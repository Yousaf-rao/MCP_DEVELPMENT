import re
import os
from pathlib import Path

# Constants
SAFE_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+$")
IGNORE_DIRS = {'.git', 'node_modules', '.next', 'dist', 'build'}

# Git Availability Check
try:
    from git import Repo, InvalidGitRepositoryError
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

# Utilities
def is_relative_to(p: Path, base: Path) -> bool:
    try:
        p.relative_to(base)
        return True
    except ValueError:
        return False
