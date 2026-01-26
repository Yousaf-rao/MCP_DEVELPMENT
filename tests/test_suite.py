"""
Unified Test Suite for MCP Server & Automation Pipeline
Tests:
- Security validation
- File operations
- Webhook handling
- Figma API integration
"""

import asyncio
import json
import logging
import os
import hmac
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, AsyncMock
import pytest
from fastapi.testclient import TestClient

# Core Imports
from mcp_core import (
    ServerConfig,
    SecurityValidator,
    AuditLogger,
    AuditLog,
    RepoToolsServer
)
from mcp_core.tools import filesystem, figma

# Mock aiosqlite if not installed, to allow tests to run
import sys

try:
    import aiosqlite
except ImportError:
    mock_db = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = [1]
    mock_cursor.fetchall.return_value = []
    
    mock_db.execute.return_value = mock_cursor
    
    mock_connect = MagicMock()
    mock_connect.__aenter__.return_value = mock_db
    mock_connect.__aexit__.return_value = None
    
    mock_aiosqlite = MagicMock()
    mock_aiosqlite.connect.return_value = mock_connect
    
    sys.modules["aiosqlite"] = mock_aiosqlite

from webhook_server import app


# --- Part 1: Security & Core Infrastructure ---

class TestSecurityValidator:
    """Test security validation logic."""
    
    @pytest.fixture
    def config(self, tmp_path):
        return ServerConfig(
            allowed_repos=["test-repo"],
            allowed_roots=[tmp_path],
            max_file_size=100
        )
    
    @pytest.fixture
    def validator(self, config):
        with patch.dict(os.environ, {"DEV_ALLOW_ALL_REPOS": "false"}):
            return SecurityValidator(config)
    
    def test_validate_repo_allowed(self, validator):
        assert validator.validate_repo("test-repo") is True
    
    def test_validate_repo_not_allowed(self, validator):
        assert validator.validate_repo("other-repo") is False
    
    def test_validate_repo_empty_list(self):
        config = ServerConfig(allowed_repos=[])
        with patch.dict(os.environ, {"DEV_ALLOW_ALL_REPOS": "false"}):
            validator = SecurityValidator(config)
            assert validator.validate_repo("any-repo") is False
    
    def test_validate_path_within_root(self, validator, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.touch()
        assert validator.validate_path(test_file) is True
    
    def test_validate_path_outside_root(self, validator):
        outside_path = Path("/etc/passwd")
        assert validator.validate_path(outside_path) is False
    
    def test_validate_path_traversal_attempt(self, validator, tmp_path):
        malicious_path = tmp_path / ".." / ".." / "etc" / "passwd"
        assert validator.validate_path(malicious_path) is False
    
    def test_validate_file_size_within_limit(self, validator, tmp_path):
        test_file = tmp_path / "small.txt"
        test_file.write_text("x" * 50)
        assert validator.validate_file_size(test_file) is True
    
    def test_validate_file_size_exceeds_limit(self, validator, tmp_path):
        test_file = tmp_path / "large.txt"
        test_file.write_text("x" * 200)
        assert validator.validate_file_size(test_file) is False


class TestAuditLogger:
    """Test audit logging functionality."""
    
    @pytest.fixture
    def audit_logger(self, tmp_path):
        log_file = tmp_path / "audit.jsonl"
        return AuditLogger(log_file), log_file
    
    def test_log_success(self, audit_logger):
        logger, log_file = audit_logger
        entry = AuditLog(
            timestamp="2025-12-17T10:00:00",
            tool_name="test_tool",
            inputs={"key": "value"},
            outputs="result",
            duration_ms=10.5,
            success=True
        )
        logger.log(entry)
        
        assert log_file.exists()
        with open(log_file) as f:
            logged = json.loads(f.read())
        assert logged["tool_name"] == "test_tool"
        assert logged["success"] is True

    def test_log_failure(self, audit_logger):
        logger, log_file = audit_logger
        entry = AuditLog(
            timestamp="2025-12-17T10:00:00",
            tool_name="test_tool",
            inputs={"key": "value"},
            outputs=None,
            duration_ms=5.0,
            success=False,
            error="Something went wrong"
        )
        logger.log(entry)
        
        with open(log_file) as f:
            logged = json.loads(f.read())
        assert logged["success"] is False

    def test_log_redacts_sensitive_data(self, audit_logger):
        logger, log_file = audit_logger
        entry = AuditLog(
            timestamp="2025-12-17T10:00:00",
            tool_name="test_tool",
            inputs={"password": "secret123"},
            outputs="result",
            duration_ms=10.0,
            success=True
        )
        logger.log(entry)
        
        with open(log_file) as f:
            logged = json.loads(f.read())
        assert logged["inputs"] == {"<redacted>": True}


# --- Part 2: Tool Implementation Tests ---

class TestRepoToolsServer:
    """Test MCP server tool implementations."""
    
    @pytest.fixture
    async def server(self, tmp_path):
        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()
        
        (repo_path / "file1.txt").write_text("Content 1")
        (repo_path / "file2.py").write_text("print('hello')")
        
        subdir = repo_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("Nested content")
        
        config = ServerConfig(
            allowed_repos=["test-repo"],
            allowed_roots=[tmp_path],
            max_file_size=1000
        )
        return RepoToolsServer(config), tmp_path
    
    @pytest.mark.asyncio
    async def test_list_repo_files_root(self, server):
        mcp_server, tmp_path = server
        result = await filesystem.list_repo_files(mcp_server.ctx, {
            "repo": "test-repo",
            "path": "."
        })
        file_paths = [f['path'] for f in result['files']]
        assert "file1.txt" in file_paths
        assert "subdir/" in result['directories']

    @pytest.mark.asyncio
    async def test_read_file_success(self, server):
        mcp_server, tmp_path = server
        result = await filesystem.read_file(mcp_server.ctx, {
            "repo": "test-repo",
            "file": "file1.txt"
        })
        assert "Content 1" in result["content"]

    @pytest.mark.asyncio
    async def test_locate_component_found(self, server):
        mcp_server, tmp_path = server
        components_dir = tmp_path / "test-repo" / "components"
        components_dir.mkdir()
        (components_dir / "UserProfile.tsx").write_text("code")
        
        result = await filesystem.locate_component(mcp_server.ctx, {"hint": "user"})
        assert any(m.endswith("UserProfile.tsx") for m in result["matches"])


# --- Part 3: Webhook Tests ---

class TestWebhookEndpoint:
    """Test webhook endpoint without running the server."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
        
    @pytest.fixture
    def valid_payload(self):
        return {
            "event_id": "evt_123",
            "event_type": "FILE_UPDATE",
            "file_key": "kjsdhf7823",
            "file_name": "Test Design",
            "timestamp": "2023-10-27T10:00:00Z"
        }

    def test_webhook_success(self, client):
        passcode = "test-passcode-12345"
        payload = {"event_id": "test_1", "file_key": "abc", "event_type": "ping", "timestamp": "now"}
        payload_bytes = json.dumps(payload).encode()
        
        with patch.dict(os.environ, {"FIGMA_WEBHOOK_PASSCODE": passcode}):
            signature = hmac.new(passcode.encode(), payload_bytes, hashlib.sha256).hexdigest()
            
            response = client.post(
                "/figma-webhook",
                content=payload_bytes,
                headers={"X-Figma-Signature": signature, "Content-Type": "application/json"}
            )
            
            assert response.status_code in [200, 429]
            if response.status_code == 200:
                assert response.json()["status"] == "success"


# --- Part 4: Figma API Tests ---

class TestFigmaAPI:
    """Test Figma API integration functions."""

    @pytest.mark.asyncio
    async def test_fetch_figma_pattern_httpx(self):
        """Verify fetch_figma_pattern fetches and parses Figma data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "Test File",
            "lastModified": "2023-01-01",
            "document": {"id": "0:0", "type": "DOCUMENT"},
            "components": {},
            "styles": {}
        }
        
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client_cls.return_value.__aexit__.return_value = None
            
            config = ServerConfig(allowed_repos=["*"], allowed_roots=[])
            server = RepoToolsServer(config)
            
            with patch.dict(os.environ, {"FIGMA_ACCESS_TOKEN": "fake-token"}):
                result = await figma.fetch_figma_pattern(server.ctx, {"file_key": "key123"})
                
            assert result["file_key"] == "key123"
            assert result["name"] == "Test File"
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_figma_pattern_no_token(self):
        """Verify error when FIGMA_ACCESS_TOKEN is missing."""
        config = ServerConfig(allowed_repos=["*"], allowed_roots=[])
        server = RepoToolsServer(config)
        
        with patch.dict(os.environ, {"FIGMA_ACCESS_TOKEN": ""}):
            with pytest.raises(ValueError, match="FIGMA_ACCESS_TOKEN"):
                await figma.fetch_figma_pattern(server.ctx, {"file_key": "key123"})

    @pytest.mark.asyncio
    async def test_list_pending_events(self):
        """Verify list_pending_events queries the database."""
        config = ServerConfig(allowed_repos=["*"], allowed_roots=[])
        server = RepoToolsServer(config)
        
        # The mock aiosqlite returns empty list by default
        result = await figma.list_pending_events(server.ctx, {"limit": 10})
        
        # Just check structure - actual DB content depends on mock
        assert "events" in result
        assert "count" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
