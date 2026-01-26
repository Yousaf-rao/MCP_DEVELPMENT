import hmac
import hashlib
import json
import logging
import time
import os
import secrets
import aiosqlite
from pathlib import Path
from dataclasses import dataclass
from typing import Set

from .constants import SAFE_REPO_RE, is_relative_to
from .config import ServerConfig

logger = logging.getLogger(__name__)

@dataclass
class ApprovalToken:
    """Represents an approval token for write operations (v2)"""
    version: int
    operation: str
    repo: str
    timestamp: int
    nonce: str
    approver_id: str
    aud: str
    host_id: str
    signature: str
    
    @staticmethod
    def create(operation: str, repo: str, approver_id: str, host_id: str, secret_key: str) -> 'ApprovalToken':
        timestamp = int(time.time())
        nonce = secrets.token_hex(32)
        
        payload = {
            "version": 1,
            "operation": operation,
            "repo": repo,
            "timestamp": timestamp,
            "nonce": nonce,
            "approver_id": approver_id,
            "aud": "mcp-server",
            "host_id": host_id
        }
        
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            secret_key.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return ApprovalToken(
            version=1,
            operation=operation,
            repo=repo,
            timestamp=timestamp,
            nonce=nonce,
            approver_id=approver_id,
            aud="mcp-server",
            host_id=host_id,
            signature=signature
        )
    
    def verify(self, secret_key: str, used_nonces: Set[str], ttl_seconds: int = 300, clock_skew: int = 30) -> bool:
        if self.version != 1:
            logger.warning(f"Unknown token version: {self.version}")
            return False
        if self.aud != "mcp-server":
            logger.warning(f"Invalid audience: {self.aud}")
            return False
            
        age = time.time() - self.timestamp
        if age > (ttl_seconds + clock_skew):
            logger.warning(f"Token expired (age: {age}s)")
            return False
        if age < -clock_skew:
            logger.warning(f"Token from future")
            return False
            
        if self.nonce in used_nonces:
            logger.warning(f"Token nonce already used")
            return False
            
        payload = {
            "version": self.version,
            "operation": self.operation,
            "repo": self.repo,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "approver_id": self.approver_id,
            "aud": self.aud,
            "host_id": self.host_id
        }
        payload_str = json.dumps(payload, sort_keys=True)
        expected_signature = hmac.new(
            secret_key.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(self.signature, expected_signature):
            logger.warning("Token signature verification failed")
            return False
            
        return True

class SecurityValidator:
    def __init__(self, config: ServerConfig):
        self.config = config
        self.allow_all = os.getenv("DEV_ALLOW_ALL_REPOS", "false").lower() == "true"
        
    def sanitize_repo_id(self, repo: str) -> str:
        if not SAFE_REPO_RE.match(repo):
            raise ValueError(f"Invalid repo identifier: {repo}")
        return repo
        
    def validate_repo(self, repo: str) -> bool:
        repo = self.sanitize_repo_id(repo)
        if self.allow_all or "*" in self.config.allowed_repos:
            return True
        if not self.config.allowed_repos:
            return False
        return repo in self.config.allowed_repos
        
    def validate_path(self, file_path: Path) -> bool:
        try:
            resolved = file_path.resolve()
            return any(is_relative_to(resolved, root) for root in self.config.allowed_roots)
        except (ValueError, OSError):
            return False
            
    def validate_file_size(self, file_path: Path) -> bool:
        try:
            return file_path.stat().st_size <= self.config.max_file_size
        except OSError:
            return False
    async def verify_and_consume_nonce(self, token: ApprovalToken, secret_key: str) -> bool:
        """
        Verifies the token signature AND ensures the nonce hasn't been used.
        Uses SQLite for persistence.
        """
        # 1. basic stateless checks
        if not token.verify(secret_key, set()): # Pass empty set, we check nonce manually
             return False
             
        # 2. Check nonce in DB
        db_path = Path(__file__).parent.parent / "events.db"
        
        async with aiosqlite.connect(db_path) as db:
            # Check if exists
            async with db.execute("SELECT 1 FROM nonces WHERE nonce = ?", (token.nonce,)) as cursor:
                if await cursor.fetchone():
                    logger.warning(f"Replay attack detected: Nonce {token.nonce} already used")
                    return False
            
            # Consume nonce
            try:
                # Cleanup old nonces first (optional optimization)
                # await db.execute("DELETE FROM nonces WHERE expiry < ?", (int(time.time()),))
                
                expiry = token.timestamp + 300 + 30 # TTL + Skew
                await db.execute(
                    "INSERT INTO nonces (nonce, timestamp, expiry) VALUES (?, ?, ?)",
                    (token.nonce, token.timestamp, expiry)
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                logger.warning(f"Replay attack detected (race condition): Nonce {token.nonce} used")
                return False
