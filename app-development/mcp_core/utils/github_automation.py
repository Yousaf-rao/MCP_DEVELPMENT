import os
import re
import time
from github import Github, GithubException
from typing import Optional
from mcp_core.utils.code_merger import CodeMerger

# CONFIGURATION
# CONFIGURATION
# This is the "Long-Lived" branch where all Figma updates will accumulate
PIPELINE_BRANCH = "figma-pipeline" 

def sanitize_for_comparison(text: str) -> str:
    """
    Normalizes a name for fuzzy comparison.
    1. Removes file extension (if any).
    2. Converts to lowercase.
    3. Removes ALL non-alphanumeric characters (spaces, underscores, dashes).
    
    Example:
    "Primary Button"       -> "primarybutton"
    "PrimaryButton.tsx"    -> "primarybutton"
    "btn_primary_v2"       -> "btnprimaryv2"
    """
    # Remove extension if present (e.g., .tsx, .js)
    if "." in text:
        text = text.rsplit(".", 1)[0]
    
    # Lowercase and strip everything except a-z and 0-9
    return re.sub(r'[^a-z0-9]', '', text.lower())

def find_existing_file_path(repo, figma_name: str) -> str:
    """
    Scans the repo for a matching file, ignoring casing and formatting.
    """
    target_clean = sanitize_for_comparison(figma_name)
    
    print(f"[Smart Search] 🔍 Looking for: '{figma_name}' (Normalized: '{target_clean}')...")

    try:
        # Recursive tree fetch (fast)
        tree = repo.get_git_tree(repo.default_branch, recursive=True).tree
        
        for element in tree:
            # We only care about blobs (files), not trees (folders)
            if element.type != "blob":
                continue
                
            # Check if this file is a match
            repo_filename = os.path.basename(element.path)
            repo_clean = sanitize_for_comparison(repo_filename)
            
            # THE MATCH LOGIC
            if repo_clean == target_clean:
                print(f"[Smart Search] ✅ MATCH FOUND! Maps to: {element.path}")
                return element.path
                
    except Exception as e:
        print(f"[Smart Search] ⚠️ Search error: {e}")

    # Fallback: If not found, create a new one in components
    # We maintain the original casing from Figma but ensure it's a valid filename
    safe_name = figma_name.replace(" ", "") 
    default_path = f"src/components/{safe_name}.tsx"
    
    print(f"[Smart Search] 🆕 No match found. creating: {default_path}")
    return default_path

def get_repo_file_structure() -> list[str]:
    """
    Returns a flat list of all file paths in the repository.
    Used for the AI Semantic Router.
    """
    token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("GITHUB_REPO")
    
    if not token or not repo_name:
        return []
        
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        tree = repo.get_git_tree(repo.default_branch, recursive=True).tree
        
        # Return only blobs (files)
        return [element.path for element in tree if element.type == "blob"]
    except Exception as e:
        print(f"[GitHub Automation] Failed to fetch file structure: {e}")
        return []

def create_figma_update_pr(
    file_path: str,
    content: str,
    file_name: str,
    figma_file_key: str,
    max_retries: int = 3
) -> Optional[str]:
    """
    Push updates to a single persistent 'pipeline' branch.
    Developer manually merges this branch into main when ready.
    """
    token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("GITHUB_REPO") 
    
    if not token or not repo_name:
        print("[GitHub Automation] Missing GITHUB_TOKEN or GITHUB_REPO")
        return None

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)

        # --- SMART PATH RESOLUTION ---
        # Don't trust the hardcoded path. Ask the repo where the file lives.
        # We use file_path's basename as the target filename to search for.
        target_filename = os.path.basename(file_path)
        final_file_path = find_existing_file_path(repo, target_filename)
        
        # Override file_path with the found (or new default) path
        file_path = final_file_path
        
        # 1. GET OR CREATE THE PIPELINE BRANCH
        # We try to get the persistent branch. If missing, create it from default.
        try:
            repo.get_branch(PIPELINE_BRANCH)
            print(f"[GitHub Automation] Found existing pipeline branch: {PIPELINE_BRANCH}")
        except GithubException:
            # Pipeline branch needs creation. Get default branch first.
            try:
                main_branch = repo.get_branch(repo.default_branch)
                print(f"[GitHub Automation] Creating new pipeline branch: {PIPELINE_BRANCH}")
                repo.create_git_ref(ref=f"refs/heads/{PIPELINE_BRANCH}", sha=main_branch.commit.sha)
            except GithubException:
                 print("[GitHub Automation] Default branch not found (Empty Repo?). Proceeding to Create File directly.")
                 pass
        
        # 2. SMART UPDATE LOOP (Optimistic Locking)
        # We fetch from PIPELINE_BRANCH, merge, and push back to PIPELINE_BRANCH.
        
        commit_message = f"feat(design): Update {file_name} from Figma"
        
        for attempt in range(max_retries):
            try:
                # A. Fetch Current Content from the PIPELINE BRANCH
                # This ensures we don't overwrite previous automation updates that haven't been merged to main yet.
                try:
                    contents = repo.get_contents(file_path, ref=PIPELINE_BRANCH)
                    remote_code = contents.decoded_content.decode("utf-8")
                    current_sha = contents.sha
                    
                    # B. Merge (Phase 12 Soft Fallback)
                    # Merges new Figma code with any manual edits on the pipeline branch
                    final_code = CodeMerger.merge(existing_code=remote_code, new_code=content)
                    
                    # C. Check for changes
                    if final_code == remote_code:
                        print(f"[GitHub Automation] No changes needed for {file_name}")
                        break # Skip push, but still ensure PR exists below
                        
                except GithubException as e:
                    if e.status == 404:
                        # File doesn't exist on pipeline branch yet? Create it.
                        remote_code = ""
                        current_sha = None
                        final_code = content # No existing code to merge
                    else:
                        raise e

                # D. Push to Pipeline Branch
                if current_sha:
                    repo.update_file(
                        path=file_path,
                        message=commit_message,
                        content=final_code,
                        sha=current_sha, # Safety Lock
                        branch=PIPELINE_BRANCH
                    )
                else:
                    repo.create_file(
                        path=file_path,
                        message=commit_message,
                        content=final_code,
                        branch=PIPELINE_BRANCH
                    )
                
                print(f"[GitHub Automation] Pushed update to {PIPELINE_BRANCH}")
                break # Success
                
            except GithubException as e:
                if e.status == 409:
                    print(f"[GitHub Automation] Conflict on attempt {attempt+1}. Retrying...")
                    time.sleep(1)
                    continue
                else:
                    raise e
        
        # 3. ENSURE PULL REQUEST EXISTS
        # We don't create a new PR every time. We check if one exists for this branch.
        existing_prs = repo.get_pulls(state='open', head=f"{repo.owner.login}:{PIPELINE_BRANCH}")
        
        if existing_prs.totalCount > 0:
            pr = existing_prs[0]
            print(f"[GitHub Automation] PR already active: {pr.html_url}")
            return pr.html_url
        else:
            # Create the Single PR
            pr_body = f"""
### 🎨 Figma Sync Pipeline
**Branch:** `{PIPELINE_BRANCH}`
**Status:** 🟡 Auto-Updating

This PR accumulates all design updates from Figma.
- The pipeline will **keep pushing commits** to this branch as designs change.
- **Manual Review:** When you are satisfied with the state of the UI, merge this PR into `{repo.default_branch}`.
- After merge, the pipeline will recreate this branch for future updates.

_Generated by MCP Automation Worker_
            """
            
            pr = repo.create_pull(
                title=f"🎨 Figma Pipeline: Continuous Sync",
                body=pr_body,
                head=PIPELINE_BRANCH,
                base=repo.default_branch,
                draft=False 
            )
            print(f"[GitHub Automation] Created new pipeline PR: {pr.html_url}")
            return pr.html_url

    except Exception as e:
        print(f"[GitHub Automation] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
