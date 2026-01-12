import os
import re
import logging
from typing import Dict, Any
from ..constants import GIT_AVAILABLE
from ..context import ToolContext
from ..security import ApprovalToken
from .filesystem import resolve_repo_root

if GIT_AVAILABLE:
    from git import Repo, InvalidGitRepositoryError

logger = logging.getLogger(__name__)

def _get_git_repo(repo_path):
    if not GIT_AVAILABLE:
        raise RuntimeError("GitPython not available")
    try:
        return Repo(repo_path)
    except InvalidGitRepositoryError:
        raise ValueError(f"'{repo_path}' is not a Git repository")

async def create_branch(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    repo = args["repo"]
    branch_name = args["branch"]
    from_ref = args.get("from_ref", "HEAD")
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
        
        if not token.verify(ctx.approval_secret, ctx.used_nonces):
            raise PermissionError("Approval token verification failed")
            
        if token.operation != "create_branch":
            raise PermissionError(f"Token is for '{token.operation}', not 'create_branch'")
        if token.repo != repo:
            raise PermissionError(f"Token is for repo '{token.repo}', not '{repo}'")
            
        ctx.used_nonces.add(token.nonce)
        approver_id = token.approver_id
    else:
        approver_id = "auto-approved-dev"
    
    if not ctx.security.validate_repo(repo):
        raise PermissionError(f"Repository '{repo}' not in allow-list")
        
    repo_root = await resolve_repo_root(ctx, repo)
    git_repo = _get_git_repo(repo_root)
    
    if not re.match(r'^[a-zA-Z0-9/_-]+$', branch_name):
        raise ValueError(f"Invalid branch name: '{branch_name}'")
    
    if branch_name in [ref.name for ref in git_repo.branches]:
        raise ValueError(f"Branch '{branch_name}' already exists")
        
    try:
        new_branch = git_repo.create_head(branch_name, from_ref)
        commit_sha = str(new_branch.commit)
        logger.info(f"Created branch '{branch_name}' at {commit_sha}")
        return {
            "repo": repo,
            "branch": branch_name,
            "from_ref": from_ref,
            "commit_sha": commit_sha,
            "approver": approver_id
        }
    except Exception as e:
        raise RuntimeError(f"Failed to create branch: {e}")
