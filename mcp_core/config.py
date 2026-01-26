from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

@dataclass
class ServerConfig:
    name: str = "repo-tools-mcp-server"
    version: str = "2.0.0"
    allowed_repos: List[str] = None
    allowed_roots: List[Path] = None
    max_file_size: int = 1_000_000
    
    def __post_init__(self):
        if self.allowed_repos is None:
            self.allowed_repos = []
        if self.allowed_roots is None:
            self.allowed_roots = [Path.cwd()]
        self.allowed_roots = [Path(r).resolve() for r in self.allowed_roots]

@dataclass
class SearchConfig:
    """Production limits for search_content tool"""
    max_files_per_root: int = 10_000
    max_matches_per_file: int = 10
    max_results: int = 100
    allowed_extensions: List[str] = None
    binary_size_threshold: int = 8192
    
    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = [
                ".js", ".ts", ".tsx", ".jsx", ".py",
                ".css", ".html", ".json", ".md", ".yaml",
                ".yml", ".xml", ".txt", ".sh", ".bat"
            ]
