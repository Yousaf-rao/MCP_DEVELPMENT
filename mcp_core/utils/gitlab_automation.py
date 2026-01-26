
import os
import re
import time
import logging
import gitlab
from typing import Optional, List

logger = logging.getLogger(__name__)

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
    if "." in text:
        text = text.rsplit(".", 1)[0]
    return re.sub(r'[^a-z0-9]', '', text.lower())

def find_existing_file_path(project, figma_name: str) -> str:
    """
    Scans the repository for a matching file, ignoring casing and formatting.
    """
    target_clean = sanitize_for_comparison(figma_name)
    logger.info(f"[Smart Search] Looking for: '{figma_name}' (Normalized: '{target_clean}')...")

    try:
        # Fetch file tree (recursive=True means full tree)
        items = project.repository_tree(recursive=True, all=True)
        
        for element in items:
            if element['type'] != 'blob':
                continue
                
            repo_filename = os.path.basename(element['path'])
            repo_clean = sanitize_for_comparison(repo_filename)
            
            if repo_clean == target_clean:
                logger.info(f"[Smart Search] MATCH FOUND! Maps to: {element['path']}")
                return element['path']
                
    except Exception as e:
        logger.error(f"[Smart Search] Search error: {e}")

    # Strip extension if already present, then clean up the name
    base_name = figma_name.rsplit('.', 1)[0] if '.' in figma_name else figma_name
    safe_name = base_name.replace(" ", "").replace("-", "").replace("_", "")
    default_path = f"FigmaDesign/{safe_name}.jsx"  # Use FigmaDesign folder for new files
    
    logger.info(f"[Smart Search] No match found. Creating: {default_path}")
    return default_path

def get_repo_file_structure() -> List[str]:
    """
    Returns a flat list of all file paths in the repository.
    """
    token = os.getenv("GITLAB_TOKEN")
    project_id = os.getenv("GITLAB_PROJECT_ID")
    url = os.getenv("GITLAB_URL", "https://gitlab.com")
    
    if not token or not project_id:
        return []
        
    try:
        gl = gitlab.Gitlab(url, private_token=token)
        project = gl.projects.get(project_id)
        items = project.repository_tree(recursive=True, all=True)
        return [item['path'] for item in items if item['type'] == 'blob']
    except Exception as e:
        logger.error(f"[GitLab Automation] Failed to fetch file structure: {e}")
        return []

def create_merge_request(
    file_path: str,
    content: str,
    file_name: str,
    figma_file_key: str,
    max_retries: int = 3,
    repo_path: str = None
) -> Optional[str]:
    """
    Push updates to a branch and create/update a Merge Request.
    """
    token = os.getenv("GITLAB_TOKEN")
    project_id = os.getenv("GITLAB_PROJECT_ID") 
    url = os.getenv("GITLAB_URL", "https://gitlab.com")

    if not token or not project_id:
        logger.error("[GitLab Automation] Missing GITLAB_TOKEN or GITLAB_PROJECT_ID")
        return None

    try:
        gl = gitlab.Gitlab(url, private_token=token)
        project = gl.projects.get(project_id)

        # Smart Path Resolution
        target_filename = os.path.basename(file_path)
        final_file_path = find_existing_file_path(project, target_filename)
        file_path = final_file_path
        
        # 1. Pipeline Branch Logic
        default_branch_name = project.default_branch
        source_branch = os.getenv("GITLAB_BRANCH", default_branch_name)  # Use configured branch (testsubject)
        
        try:
            project.branches.get(PIPELINE_BRANCH)
            logger.info(f"[GitLab Automation] Found existing pipeline branch: {PIPELINE_BRANCH}")
        except gitlab.exceptions.GitlabGetError:
            logger.info(f"[GitLab Automation] Creating new pipeline branch: {PIPELINE_BRANCH} from {source_branch}")
            project.branches.create({'branch': PIPELINE_BRANCH, 'ref': source_branch})

        # 2. Smart Update Loop
        commit_message = f"feat(design): Update {file_name} from Figma"
        
        for attempt in range(max_retries):
            try:
                # Fetch Current Content
                try:
                    f = project.files.get(file_path=file_path, ref=PIPELINE_BRANCH)
                    remote_code = f.decode().decode("utf-8")
                    
                    # LLM generates complete replacement code
                    # No merging needed - LLM sees existing code via RAG context
                    final_code = content
                    
                    if final_code == remote_code:
                        logger.info(f"[GitLab Automation] No changes needed for {file_name}")
                        break
                    
                    # Update File
                    f.content = final_code
                    f.save(branch=PIPELINE_BRANCH, commit_message=commit_message)
                    
                except gitlab.exceptions.GitlabGetError:
                    # File doesn't exist, Create it
                    project.files.create({
                        'file_path': file_path,
                        'branch': PIPELINE_BRANCH,
                        'content': content,
                        'commit_message': commit_message
                    })
                
                logger.info(f"[GitLab Automation] Pushed update to {PIPELINE_BRANCH}")
                break
                
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                raise e

        # 3. Ensure Merge Request Exists (target the configured branch, not default)
        target_branch = source_branch  # Use testsubject (from GITLAB_BRANCH)
        existing_mrs = project.mergerequests.list(state='opened', source_branch=PIPELINE_BRANCH, target_branch=target_branch)
        
        if existing_mrs:
            mr = existing_mrs[0]
            logger.info(f"[GitLab Automation] MR already active: {mr.web_url}")
            return mr.web_url
        else:
            mr_title = "🎨 Figma Pipeline: Continuous Sync"
            mr_description = f"""
### 🎨 Figma Sync Pipeline
**Branch:** `{PIPELINE_BRANCH}`
**Status:** 🟡 Auto-Updating

This MR accumulates all design updates from Figma.
- The pipeline will **keep pushing commits** to this branch as designs change.
- **Manual Review:** When you are satisfied with the state of the UI, merge this MR into `{target_branch}`.

_Generated by MCP Automation Worker_
            """
            
            mr = project.mergerequests.create({
                'source_branch': PIPELINE_BRANCH,
                'target_branch': target_branch,
                'title': mr_title,
                'description': mr_description,
                'remove_source_branch': True
            })
            
            logger.info(f"[GitLab Automation] Created new pipeline MR: {mr.web_url}")
            return mr.web_url

    except Exception as e:
        logger.error(f"[GitLab Automation] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
