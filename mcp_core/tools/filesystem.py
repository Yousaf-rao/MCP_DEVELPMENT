import os
import logging
import re
from pathlib import Path
from typing import Dict, Any, List
from ..constants import IGNORE_DIRS
from ..context import ToolContext
from ..security import ApprovalToken

logger = logging.getLogger(__name__)

async def resolve_repo_root(ctx: ToolContext, repo: str) -> Path:
    ctx.security.sanitize_repo_id(repo)
    for allowed_root in ctx.config.allowed_roots:
        potential_repo = allowed_root / repo
        if potential_repo.exists():
            return potential_repo.resolve()
    raise FileNotFoundError(f"Repository '{repo}' not found")

async def list_repo_files(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    repo = args["repo"]
    rel_path = args.get("path", ".")
    if not ctx.security.validate_repo(repo):
        raise PermissionError(f"Repository '{repo}' not in allow-list")
    repo_root = await resolve_repo_root(ctx, repo)
    target_path = Path(os.path.expanduser(str(repo_root / rel_path))).resolve()
    if not ctx.security.validate_path(target_path):
        raise PermissionError(f"Path outside allowed roots: {target_path}")
    if not target_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {rel_path}")
    dirs, files = [], []
    for item in sorted(target_path.iterdir()):
        rel = str(item.relative_to(repo_root))
        if item.is_dir():
            dirs.append(rel + "/")
        else:
            files.append({"path": rel, "size": item.stat().st_size})
    return {"repo": repo, "path": rel_path, "directories": dirs, "files": files}

async def read_file(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    repo = args.get("repo")
    file_path = args["file"]
    if repo:
        if not ctx.security.validate_repo(repo):
            raise PermissionError(f"Repository '{repo}' not in allow-list")
        repo_root = await resolve_repo_root(ctx, repo)
        target_file = (repo_root / file_path).resolve()
    else:
        target_file = None
        for root in ctx.config.allowed_roots:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
                if file_path in filenames or Path(file_path).name in filenames:
                    candidate = Path(dirpath) / Path(file_path).name
                    if candidate.is_file():
                        target_file = candidate.resolve()
                        break
            if target_file:
                break
        if not target_file:
            raise FileNotFoundError(f"File '{file_path}' not found in any allowed root")
    
    if not ctx.security.validate_path(target_file):
        raise PermissionError(f"File outside allowed roots: {file_path}")
    if not target_file.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    if not ctx.security.validate_file_size(target_file):
        raise ValueError(f"File exceeds size limit: {file_path}")
    try:
        content = target_file.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        raise ValueError(f"File is not a text file: {file_path}")
    return {"repo": repo or "auto-discovered", "file": str(target_file), "content": content}

async def locate_component(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    hint = args["hint"].lower()
    matches = []
    for root in ctx.config.allowed_roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
            base = Path(dirpath)
            for fname in filenames:
                p = base / fname
                if hint in p.name.lower():
                    try:
                        rel_path = str(p.relative_to(root))
                        matches.append(rel_path)
                    except ValueError:
                        continue
    return {"hint": hint, "count": len(matches), "matches": sorted(matches)[:200]}

async def search_content(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    content = args["content"]
    repo = args.get("repo")
    case_sensitive = args.get("case_sensitive", False)
    
    if repo:
        if not ctx.security.validate_repo(repo):
            raise PermissionError(f"Repository '{repo}' not in allow-list")
        search_roots = [await resolve_repo_root(ctx, repo)]
    else:
        search_roots = ctx.config.allowed_roots
    
    search_lines = content.splitlines()
    if not search_lines:
        return {"query": content, "total_matches": 0, "files": []}
    
    if not case_sensitive:
        search_lines = [line.lower() for line in search_lines]
    
    results = []
    total_matches = 0
    files_scanned = 0
    
    for root in search_roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
            base = Path(dirpath)
            
            for fname in filenames:
                if files_scanned >= ctx.search_config.max_files_per_root:
                    break
                
                file_path = base / fname
                if ctx.search_config.allowed_extensions:
                    if file_path.suffix.lower() not in ctx.search_config.allowed_extensions:
                        continue
                
                if not ctx.security.validate_path(file_path):
                    continue
                if not ctx.security.validate_file_size(file_path):
                    continue
                
                files_scanned += 1
                
                # Streaming Search Implementation
                # Uses a sliding window (deque) to avoid loading the entire file into memory (O(N) -> O(M))
                from collections import deque
                
                # Pre-calculate search context
                num_search_lines = len(search_lines)
                window = deque(maxlen=num_search_lines)
                
                file_matches = []
                # Current 1-based line number in file
                line_idx = 0 
                
                found_match = False
                
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            # Reset for this encoding attempt
                            line_idx = 0
                            window.clear()
                            
                            for line in f:
                                line_idx += 1
                                # Normalize line
                                if case_sensitive:
                                    normalized_line = line.rstrip()
                                else:
                                    normalized_line = line.rstrip().lower()
                                
                                window.append(normalized_line)
                                
                                # Check buffer only when full
                                if len(window) == num_search_lines:
                                    # Optimistic check: Check exact matches first
                                    # The requirement is that search_lines[j] is IN window[j]
                                    is_match = True
                                    for j in range(num_search_lines):
                                        if search_lines[j] not in window[j]:
                                            is_match = False
                                            break
                                    
                                    if is_match:
                                        start_line = line_idx - num_search_lines + 1
                                        end_line = line_idx
                                        # Note: We reconstruct the original content from the buffer
                                        # This might lose original casing if case_insensitve=True
                                        # But for search results, showing the matched text is acceptable.
                                        # Ideally we'd store a tuple (raw, normalized), but that doubles memory.
                                        # Given this is "search", showing the normalized or found line is usually fine.
                                        matched_content = list(window)
                                        
                                        file_matches.append({
                                            "start_line": start_line,
                                            "end_line": end_line,
                                            "matched_lines": matched_content
                                        })
                                        total_matches += 1
                                        
                        # If we successfully read the file without encoding error, break the retry loop
                        break
                    except UnicodeDecodeError:
                        continue
                    except Exception:
                        break
                
                if file_matches:
                    try:
                        rel_path = str(file_path.relative_to(root))
                    except ValueError:
                        rel_path = str(file_path)
                    results.append({
                        "file": rel_path,
                        "match_count": len(file_matches),
                        "matches": file_matches[:ctx.search_config.max_matches_per_file]
                    })
                
                if len(results) >= ctx.search_config.max_results:
                    break
            
            if files_scanned >= ctx.search_config.max_files_per_root:
                break
                
    return {
        "query": content,
        "case_sensitive": case_sensitive,
        "total_matches": total_matches,
        "files_matched": len(results),
        "files_scanned": files_scanned,
        "files": results[:ctx.search_config.max_results]
    }

async def save_code_file(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    output_path_str = args["output_path"]
    file_name = args["file_name"]
    code = args["code"]
    # Auto-Approval Logic
    auto_approve = os.getenv("MCP_AUTO_APPROVE", "false").lower() == "true"
    token_data = args.get("approval_token")
    
    if not auto_approve:
        if not token_data:
            raise PermissionError("Approval token required (auto-approval disabled)")
        try:
            token = ApprovalToken(**token_data)
        except TypeError as e:
                raise PermissionError(f"Invalid approval token format: {e}")

        # Verify using persistent storage
        if not await ctx.security.verify_and_consume_nonce(token, ctx.approval_secret):
             raise PermissionError("Invalid token or replay attack detected")
    else:
        logger.info("Auto-Approving save_code_file (MCP_AUTO_APPROVE=true)")
        
    expanded_path = os.path.expanduser(output_path_str)
    output_path = Path(expanded_path).resolve()
    if not ctx.security.validate_path(output_path):
            raise PermissionError(f"Target directory outside allowed roots: {output_path}")
            
    if not re.match(r"^[A-Za-z0-9._\-/]+$", file_name):
        raise ValueError("Invalid file name")
        
    if len(code) > 200_000:
        raise ValueError("Code content exceeds 200KB limit")
        
    full_path = output_path / file_name
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(code, encoding="utf-8")
    
    return {
        "saved": True,
        "path": str(full_path),
        "bytes": len(code.encode("utf-8")),
        "target_ref": str(full_path),
        "tool_name": "save_code_file"
    }
