import json
import logging
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional

# Setup Logging
logger = logging.getLogger(__name__)

@dataclass
class AuditLog:
    timestamp: str
    tool_name: str
    inputs: Dict[str, Any]
    outputs: Optional[Any]
    duration_ms: float
    success: bool
    error: Optional[str] = None
    # Sprint 2 enhancements
    approver: Optional[str] = None
    correlation_id: Optional[str] = None
    side_effects: bool = False
    target_ref: Optional[str] = None

class AuditLogger:
    def __init__(self, log_file: Path = Path("mcp_audit.jsonl")):
        self.log_file = log_file

    def log(self, entry: AuditLog):
        log_data = asdict(entry)
        inputs_str = json.dumps(log_data.get('inputs', {})).lower()
        if 'password' in inputs_str:
            log_data['inputs'] = {'<redacted>': True}
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data) + '\n')
        except IOError as e:
            logger.error(f"Failed to write audit log: {e}")
        status = "SUCCESS" if entry.success else "FAILED"
        logger.info(f"[AUDIT] {status} - {entry.tool_name} - duration: {entry.duration_ms:.2f}ms")
