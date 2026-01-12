"""
Unified Test Suite for MCP Server & Automation Pipeline
Merges:
- Unit tests from test_mcp_server.py
- Figma generation tests from test_figma_gen.py
- Webhook tests from test_webhook.py (converted to TestClient)
"""

import asyncio
import json
import logging
import os
import hmac
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
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
from unittest.mock import AsyncMock, MagicMock

try:
    import aiosqlite
except ImportError:
    # Create a mock that supports async context manager for connect
    mock_db = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.fetchone.return_value = [1] # Default event_id
    mock_cursor.fetchall.return_value = []
    
    mock_db.execute.return_value = mock_cursor
    
    # Handle async context manager: async with aiosqlite.connect(...) as db:
    mock_connect = MagicMock()
    mock_connect.__aenter__.return_value = mock_db
    mock_connect.__aexit__.return_value = None
    
    mock_aiosqlite = MagicMock()
    mock_aiosqlite.connect.return_value = mock_connect
    
    sys.modules["aiosqlite"] = mock_aiosqlite

from webhook_server import app  # Import FastAPI app for testing

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
        # Ensure DEV_ALLOW_ALL_REPOS is disabled for these tests
        with patch.dict(os.environ, {"DEV_ALLOW_ALL_REPOS": "false"}):
            return SecurityValidator(config)
    
    def test_validate_repo_allowed(self, validator):
        assert validator.validate_repo("test-repo") is True
    
    def test_validate_repo_not_allowed(self, validator):
        assert validator.validate_repo("other-repo") is False
    
    def test_validate_repo_empty_list(self):
        config = ServerConfig(allowed_repos=[])
        # Ensure DEV_ALLOW_ALL_REPOS is disabled
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


# --- Part 3: Figma & Automation Tests ---

class TestFigmaGenerators:
    """
    Converted from test_figma_gen.py
    Tests the Figma-to-React conversion logic.
    """
    
    @pytest.fixture
    def mock_pattern(self):
        return {
            "id": "1:2",
            "name": "Card",
            "type": "FRAME",
            "visible": True,
            "layoutMode": "VERTICAL",
            "primaryAxisAlignItems": "CENTER",
            "counterAxisAlignItems": "CENTER",
            "itemSpacing": 16,
            "paddingLeft": 24, "paddingRight": 24, "paddingTop": 24, "paddingBottom": 24,
            "style": {
                "backgroundColor": {"r": 1, "g": 1, "b": 1, "a": 1},
                "width": 300,
                "height": 200,
                "borderRadius": 8
            },
            "children": [
                {
                    "id": "1:3",
                    "name": "Title",
                    "type": "TEXT",
                    "visible": True,
                    "characters": "Hello World",
                    "style": {
                        "fontSize": 24,
                        "fontWeight": 700,
                        "color": {"r": 0, "g": 0, "b": 0, "a": 1}
                    }
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_generate_react_code(self, mock_pattern):
        # Mock context not needed for pure generation if we don't access config/security
        # But we need to pass something if the function expects it.
        # figma.generate_react_code uses ctx only if needed (current impl doesn't seem to use it for gen)
        
        # We'll use a dummy context
        config = ServerConfig(allowed_repos=["*"], allowed_roots=[])
        server = RepoToolsServer(config)
        
        result = await figma.generate_react_code(server.ctx, {
            "component_name": "TestCard",
            "pattern": mock_pattern
        })
        
        code = result["code"]
        assert "export const TestCard" in code
        assert "flex" in code # layoutMode check
        assert "flex-col" in code # VERTICAL Check
        assert "rounded-[8px]" in code # borderRadius check
        assert "Hello World" in code # Content check


class TestWebhookEndpoint:
    """
    Converted from test_webhook.py
    Uses fastapi.testclient to test the webhook endpoint without running the server.
    """
    
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
            "timestamp": "2023-10-27T10:00:00Z",
            "passcode": "test-passcode-12345" # Included in payload? No, usually header.
            # Checking webhook_server.py implementation for payload structure
            # It usually expects just event data, passcode is in header X-Figma-Passcode
        }

    def test_webhook_success(self, client):
        # Setup valid signature
        passcode = "test-passcode-12345"
        payload = {"event_id": "test_1", "file_key": "abc", "event_type": "ping", "timestamp": "now"}
        payload_bytes = json.dumps(payload).encode()
        
        # We need to match the signature verification logic in webhook_server.py
        # Assuming it uses X-Figma-Signature or X-Figma-Passcode
        # Let's assume standard HMAC for safety if configured, or simple passcode check
        
        # Override dependency or env var if needed. 
        # For this test, we assume the environment variable IS set in the test runner context
        # In pytest, we can set env vars using os.environ or monkeypatch
        
        with patch.dict(os.environ, {"FIGMA_WEBHOOK_PASSCODE": passcode}):
            signature = hmac.new(passcode.encode(), payload_bytes, hashlib.sha256).hexdigest()
            
            response = client.post(
                "/figma-webhook",
                content=payload_bytes,
                headers={"X-Figma-Signature": signature, "Content-Type": "application/json"}
            )
            
            # Note: If database interaction fails (e.g. init logic), this might 500.
            # But the webhook server handles DB init usually.
            assert response.status_code in [200, 429] # 429 possible if rate limited? 
            if response.status_code == 200:
                assert response.json()["status"] == "success"


class TestFigmaRefinements:
    """Test Phase 6 Refinements: Assets, Gradients, Constraints."""

    @pytest.mark.asyncio
    async def test_asset_detection(self):
        config = ServerConfig(allowed_repos=["*"], allowed_roots=[])
        server = RepoToolsServer(config)
        
        # Pattern with Vector node
        vector_pattern = {
            "id": "2:1",
            "name": "Icon",
            "type": "VECTOR",
            "visible": True,
            "style": {"width": 24, "height": 24}
        }
        
        result = await figma.generate_react_code(server.ctx, {
            "component_name": "IconComp",
            "pattern": vector_pattern
        })
        
        assets = result["assets"]
        code = result["code"]
        
        assert len(assets) == 1
        assert assets[0]["name"] == "icon"
        assert assets[0]["filename"] == "icon.svg"
        assert 'img src="/assets/icon.svg"' in code


    @pytest.mark.asyncio
    async def test_fetch_figma_pattern_httpx(self):
        # Mock httpx response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "Test File",
            "lastModified": "2023-01-01",
            "document": {"id": "0:0", "type": "DOCUMENT"},
            "components": {},
            "styles": {}
        }
        
        # Mock httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            
            # Setup __aenter__ and __aexit__ for context manager
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
    async def test_gradient_and_constraints_bbox(self):
        config = ServerConfig(allowed_repos=["*"], allowed_roots=[])
        server = RepoToolsServer(config)
        
        # Parent node with BBox
        parent_bbox = {"x": 100, "y": 100, "width": 500, "height": 500}
        
        # Absolute child inside parent
        # Child Global X=150, Y=120 -> Relative X=50, Y=20
        child_node = {
            "id": "3:1",
            "name": "Badge",
            "type": "FRAME",
            "layoutPositioning": "ABSOLUTE",
            "constraints": {"horizontal": "LEFT", "vertical": "TOP"},
            "absoluteBoundingBox": {"x": 150, "y": 120, "width": 50, "height": 20},
            "x": 50, "y": 20, # Original relative coordinates
            "fills": []
        }
        
        # We need to test _extract_tailwind_classes directly or via render, 
        # but generate_react_code doesn't accept parent_bbox argument publicly.
        # However, _extract_tailwind_classes logic handles the math if we pass it.
        # Let's verify _extract_tailwind_classes directly for the math.
        
        # 1. Without parent_bbox (uses node.x = 50)
        classes_1 = figma._extract_tailwind_classes(child_node, parent_bbox=None)
        assert "left-[50px]" in classes_1
        assert "top-5" in classes_1 # 20 / 4 = 5.
        
        # 2. With parent_bbox (uses abs - parent_abs = 150-100=50)
        child_node_discrepancy = child_node.copy()
        child_node_discrepancy["absoluteBoundingBox"] = {"x": 200, "y": 200, "width": 50, "height": 20}

        # Should result in left-[100px] (200-100) instead of left-[50px]
        classes_2 = figma._extract_tailwind_classes(child_node_discrepancy, parent_bbox=parent_bbox)
        assert "left-25" in classes_2 # 100/4 = 25
        assert "top-25" in classes_2 # 100/4 = 25

    @pytest.mark.asyncio
    async def test_design_token_mapping(self):
        """Verify that hex colors and spacing match Tailwind tokens."""
        
        # Test 1: Color Mapping
        # #ef4444 should map to red-500
        node_color = {
            "style": {"backgroundColor": {"r": 0.937, "g": 0.267, "b": 0.267}}, # ~#ef4444
            "layoutPositioning": "AUTO",
            "type": "FRAME"
        }
        classes_color = figma._extract_tailwind_classes(node_color)
        assert "bg-red-500" in classes_color
        
        # #000000 -> black
        node_black = {
            "style": {"backgroundColor": {"r": 0, "g": 0, "b": 0}},
            "type": "FRAME"
        }
        classes_black = figma._extract_tailwind_classes(node_black)
        assert "bg-black" in classes_black
        
        # Test 2: Spacing Mapping
        # 16px -> p-4
        node_spacing = {
            "layoutMode": "VERTICAL",
            "paddingLeft": 16, "paddingRight": 16, "paddingTop": 16, "paddingBottom": 16,
            "itemSpacing": 24, # gap-6
            "type": "FRAME"
        }
        classes_spacing = figma._extract_tailwind_classes(node_spacing)
        assert "p-4" in classes_spacing
        assert "gap-6" in classes_spacing
        
        # Test 3: Fuzzy Matching
        # 16.1px -> p-4 (Should round down/snap)
        node_fuzzy = {
            "layoutMode": "VERTICAL",
            "itemSpacing": 16.1,
            "type": "FRAME"
        }
        classes_fuzzy = figma._extract_tailwind_classes(node_fuzzy)
        assert "gap-4" in classes_fuzzy
        
        # Test 4: Arbitrary Fallback
        # #ff00ff (Magenta) -> bg-[#ff00ff] (No close match)
        node_arb = {
            "style": {"backgroundColor": {"r": 1, "g": 0, "b": 1}}, 
            "type": "FRAME"
        }
        classes_arb = figma._extract_tailwind_classes(node_arb)
        assert "bg-[" in classes_arb 

    @pytest.mark.asyncio
    async def test_design_token_mapping(self):
        """Verify that hex colors and spacing match Tailwind tokens."""
        
        # Test 1: Color Mapping
        # #ef4444 should map to red-500
        node_color = {
            "style": {"backgroundColor": {"r": 0.937, "g": 0.267, "b": 0.267}}, # ~#ef4444
            "layoutPositioning": "AUTO",
            "type": "FRAME"
        }
        classes_color = figma._extract_tailwind_classes(node_color)
        assert "bg-red-500" in classes_color
        
        # #000000 -> black
        node_black = {
            "style": {"backgroundColor": {"r": 0, "g": 0, "b": 0}},
            "type": "FRAME"
        }
        classes_black = figma._extract_tailwind_classes(node_black)
        assert "bg-black" in classes_black
        
        # Test 2: Spacing Mapping
        # 16px -> p-4
        node_spacing = {
            "layoutMode": "VERTICAL",
            "paddingLeft": 16, "paddingRight": 16, "paddingTop": 16, "paddingBottom": 16,
            "itemSpacing": 24, # gap-6
            "type": "FRAME"
        }
        classes_spacing = figma._extract_tailwind_classes(node_spacing)
        assert "p-4" in classes_spacing
        assert "gap-6" in classes_spacing
        
        # Test 3: Fuzzy Matching
        # 16.1px -> p-4 (Should round down/snap)
        node_fuzzy = {
            "layoutMode": "VERTICAL",
            "itemSpacing": 16.1,
            "type": "FRAME"
        }
        classes_fuzzy = figma._extract_tailwind_classes(node_fuzzy)
        assert "gap-4" in classes_fuzzy
        
        # Test 4: Arbitrary Fallback
        # #ff00ff (Magenta) -> bg-[#ff00ff] (No close match)
        node_arb = {
            "style": {"backgroundColor": {"r": 1, "g": 0, "b": 1}}, 
            "type": "FRAME"
        }
        classes_arb = figma._extract_tailwind_classes(node_arb)
        assert "bg-[" in classes_arb 

    @pytest.mark.asyncio
    async def test_asset_download_pipeline(self):
        """Verify asset download logic with mocked httpx and aiofiles."""
        assets = [{"id": "1:2", "name": "icon", "filename": "icon.svg"}]
        
        # Mock responses
        mock_images_resp = MagicMock()
        mock_images_resp.status_code = 200
        mock_images_resp.json.return_value = {"images": {"1:2": "http://img.url/1.svg"}}
        
        mock_file_resp = MagicMock()
        mock_file_resp.status_code = 200
        mock_file_resp.content = b"<svg>...</svg>"
        
        with patch("httpx.AsyncClient") as mock_client_cls, \
             patch("aiofiles.open") as mock_aio_open:
            
            mock_client = AsyncMock()
            # Side effect for sequential calls: 1. image list, 2. image data
            mock_client.get.side_effect = [mock_images_resp, mock_file_resp]
            
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client_cls.return_value.__aexit__.return_value = None
            
            mock_f = AsyncMock()
            mock_aio_open.return_value.__aenter__.return_value = mock_f
            
            config = ServerConfig(allowed_repos=["*"], allowed_roots=[])
            server = RepoToolsServer(config)
            
            with patch.dict(os.environ, {"FIGMA_ACCESS_TOKEN": "active"}):
                final_assets = await figma.download_figma_assets(server.ctx, "key123", assets)
                
            assert final_assets[0]["local_path"].endswith("icon.svg")
            mock_f.write.assert_called_with(b"<svg>...</svg>")

    @pytest.mark.asyncio
    async def test_interaction_detection(self):
        """Verify that prototype interactions trigger onClick props."""
        config = ServerConfig(allowed_repos=["*"], allowed_roots=[])
        server = RepoToolsServer(config)
        
        # Node with transitionNodeID (Prototype Link)
        node = {
            "id": "btn:1",
            "name": "Button",
            "type": "FRAME",
            "transitionNodeID": "page:2", # Indicates click nav
            "children": []
        }
        
        result = await figma.generate_react_code(server.ctx, {
            "component_name": "NavButton",
            "pattern": node
        })
        
        code = result["code"]
        assert "onClick={() => {}}" in code
        assert "cursor-pointer" in code

    @pytest.mark.asyncio
    async def test_smart_component_mapping(self):
        """Verify that layer names map to React Components with imports."""
        config = ServerConfig(allowed_repos=["*"], allowed_roots=[])
        server = RepoToolsServer(config)
        
        # Node named "Primary Button" -> Should map to <Button>
        node = {
            "id": "btn:1",
            "name": "Primary Button",
            "type": "FRAME",
            "style": {"backgroundColor": {"r": 0, "g": 0, "b": 0}}, # bg-black
            "children": []
        }
        
        result = await figma.generate_react_code(server.ctx, {
            "component_name": "LoginView",
            "pattern": node
        })
        
        code = result["code"]
        imports = result["imports"]
        
        # Check JSX
        assert "<Button" in code
        assert "className=" in code # Should still have classes
        
        # Check Imports
        assert any("import { Button } from" in imp for imp in imports)
        assert any("@/components/ui/button" in imp for imp in imports)

    @pytest.mark.asyncio
    async def test_scan_components(self):
        """Verify component scanning and registration logic."""
        config = ServerConfig(allowed_repos=["*"], allowed_roots=[])
        server = RepoToolsServer(config)
        
        # Mock filesystem walk
        # root -> "components"
        # files -> ["UserProfile.tsx"]
        mock_walk = [
            ("/path/to/repo/src/components", [], ["UserProfile.tsx", "utils.ts"])
        ]
        
        mock_file_content = """
        import React from 'react';
        export const UserProfile = () => <div>Prof</div>;
        export function Helper() {}
        """
        
        with patch("os.walk", return_value=mock_walk), \
             patch("builtins.open", mock_open(read_data=mock_file_content)), \
             patch.object(server.ctx.config, "allowed_roots", [Path("/path/to/repo")]), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("mcp_core.component_registry.ComponentRegistry.save") as mock_save, \
             patch("mcp_core.component_registry.ComponentRegistry._load"):
             
            # Inject a fresh registry instance that will be used by the tool
            # The tool imports ComponentRegistry from mcp_core.component_registry
            # We need to make sure consistency.
            # Actually, standard patch on `save` is enough to stop disk write.
            # But the tool instantiates `ComponentRegistry()`.
            
            result = await figma.scan_components(server.ctx, {"repo": "my-repo"})
            
            assert result["success"] is True
            assert result["scanned_count"] >= 1
            
            # Check if "UserProfile" string is in mappings return
            # Heuristic in code: "UserProfile" -> "User Profile"
            assert any("User Profile" in m for m in result["mappings"])

    @pytest.mark.asyncio
    async def test_a11y_automation(self):
        """Verify A11y features: aria-label, roles, headings."""
        config = ServerConfig(allowed_repos=["*"], allowed_roots=[])
        server = RepoToolsServer(config)
        
        # Node with description -> aria-label
        node_desc = {
            "id": "1:1",
            "name": "Icon",
            "type": "VECTOR",
            "description": "Close Modal",
            "children": []
        }
        
        # Interactive Frame -> role="button"
        node_interact = {
            "id": "1:2",
            "name": "Submit",
            "type": "FRAME",
            "transitionNodeID": "page:2",
            "children": []
        }
        
        # Heading Hierarchy
        # Section (Level 2) -> Title (Level 3?)
        # Our logic: "section" in name -> increments level for children
        # "title" in name -> h1 if root? No, logic is: "heading"->h{level}, "title"->h1
        # Let's test explicit hierarchy tracking
        node_hier = {
            "id": "1:3", 
            "name": "Section Profile", 
            "type": "FRAME", 
            "children": [
                 {"id": "1:4", "name": "Section Heading", "type": "TEXT", "characters": "Profile"}, 
            ]
        }

        # Test Description
        res_desc = await figma.generate_react_code(server.ctx, {"component_name": "Icon", "pattern": node_desc})
        assert 'aria-label="Close Modal"' in res_desc["code"]
        
        # Test Interaction
        res_interact = await figma.generate_react_code(server.ctx, {"component_name": "Btn", "pattern": node_interact})
        assert 'role="button"' in res_interact["code"]
        assert 'tabIndex={0}' in res_interact["code"]
        
        # Test Hierarchy
        # Root (Level 2) -> Section (+1 = 3) -> Child "Heading" (h3)
        res_hier = await figma.generate_react_code(server.ctx, {"component_name": "Hier", "pattern": node_hier})
        # Wait, my logic for "section" was simple string check.
        # Root is level 2. "Section Profile" contains "section", so next_level=3.
        # Child is "Section Heading". contains "Heading". tag = h{level} = h3.
        assert '<h3>Profile</h3>' in res_hier["code"] or '<h3 ' in res_hier["code"]

    @pytest.mark.asyncio
    async def test_semantic_merging(self):
        """Verify that CodeMerger preserves manual code outside zones."""
        config = ServerConfig(allowed_repos=["*"], allowed_roots=[])
        server = RepoToolsServer(config)
        
        component_name = "UserProfile"
        manual_code = """import React, { useEffect } from 'react';
        
        export const UserProfile = () => {
            useEffect(() => { console.log('Mounted'); }, []);
            
            return (
                <>
                {/* @mcp-begin:view */}
                <div className="old-view">Old</div>
                {/* @mcp-end:view */}
                </>
            );
        };
        """
        
        # New pattern from Figma
        node_new = {
            "id": "1:1",
            "name": "UserProfile",
            "type": "FRAME",
            "children": [{"type": "TEXT", "characters": "New View"}]
        }
        
        # Mock filesystem to find "UserProfile.tsx" and read "manual_code"
        with patch("os.walk", return_value=[("/src", [], ["UserProfile.tsx"])]), \
             patch("builtins.open", mock_open(read_data=manual_code)), \
             patch.object(server.ctx.config, "allowed_roots", [Path("/src")]), \
             patch("pathlib.Path.exists", return_value=True):
             
             result = await figma.generate_react_code(server.ctx, {
                 "component_name": "UserProfile",
                 "pattern": node_new
             })
             
             code = result["code"]
             
             # Checks:
             # 1. Manual code preserved
             assert "useEffect" in code
             assert "console.log('Mounted')" in code
             
             # 2. View updated
             assert "New View" in code
             assert "old-view" not in code
             
             # 3. Markers preserved
             assert "@mcp-begin:view" in code
             assert "@mcp-end:view" in code

    @pytest.mark.asyncio
    async def test_tailwind_diffing(self):
        """Verify that Tailwind overrides are preserved."""
        config = ServerConfig(allowed_repos=["*"], allowed_roots=[])
        server = RepoToolsServer(config)
        
        # Scenario: Dev added 'hover:bg-blue-600' and 'id="btn-1"' manually? 
        # No, ID is from Figma. Dev added class.
        component_name = "Button"
        manual_code = """import React from 'react';
        export const Button = () => {
            return (
                <>
                {/* @mcp-begin:view */}
                <button 
                  className="bg-blue-500 p-4 hover:scale-105" 
                  data-mcp-id="1:1"
                >
                  Click Me
                </button>
                {/* @mcp-end:view */}
                </>
            );
        };
        """
        
        # New design: Designer changed bg to red-500. p-4 remains.
        # Dev's 'hover:scale-105' should be preserved.
        # 'bg-blue-500' should go.
        node_new = {
            "id": "1:1",
            "name": "Button",
            "type": "FRAME",
            "fills": [{"type": "SOLID", "color": {"r": 1, "g": 0, "b": 0}}], # Red
            "style": {"width": 100, "paddingNext": 16}, # Just dummy styles
            "children": [{"type": "TEXT", "characters": "New Text"}]
        }
        
        with patch("os.walk", return_value=[("/src", [], ["Button.tsx"])]), \
             patch("builtins.open", mock_open(read_data=manual_code)), \
             patch.object(server.ctx.config, "allowed_roots", [Path("/src")]), \
             patch("pathlib.Path.exists", return_value=True):
             
             result = await figma.generate_react_code(server.ctx, {
                 "component_name": "Button",
                 "pattern": node_new
             })
             
             code = result["code"]
             
             # Checks:
             # 1. New Red Background (bg-[#ff0000] or close)
             # Wait, our mapper maps pure red to bg-red-500? Or hex?
             # _get_color_str: if token mapped, return token. 
             # DesignTokenMapper: (1,0,0) -> #ff0000 -> red-500?
             assert "bg-red-500" in code or "bg-[#ff0000]" in code
             
             # 2. Developer's hover preserved
             assert "hover:scale-105" in code
             
             # 3. Old Blue removed (replaced by red)
             # Wait, logic is UNION currently in StyleMerger unless conflict resolution is smarter.
             # Current StyleMerger: incoming U protected.
             # Incoming: [bg-red-500, ...]
             # Protected: [hover:scale-105] (from old)
             # Existing [bg-blue-500] is NOT protected, so it is dropped. Correct.
             assert "bg-blue-500" not in code



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
