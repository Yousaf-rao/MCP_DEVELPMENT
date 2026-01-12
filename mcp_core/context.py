from dataclasses import dataclass, field
from typing import Set, Any
from .config import ServerConfig, SearchConfig
from .security import SecurityValidator
from .audit import AuditLogger

@dataclass
class ToolContext:
    config: ServerConfig
    security: SecurityValidator
    audit: AuditLogger
    search_config: SearchConfig
    approval_secret: str
    approval_secret: str
