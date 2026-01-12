import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .constants import GIT_AVAILABLE
from .config import ServerConfig, SearchConfig
from .audit import AuditLogger, AuditLog
from .security import SecurityValidator
from .context import ToolContext

# Context Import
from mcp_core.tools import filesystem, git, figma

logger = logging.getLogger(__name__)

def truncate_large_output(result_obj: Dict[str, Any], max_size: int = 100000) -> Dict[str, Any]:
    """
    Truncate result object if its JSON string representation exceeds max_size (default 100KB).
    Prevents 'Context Saturation' freezes in LLMs.
    """
    try:
        final_json = json.dumps(result_obj)
        if len(final_json) <= max_size:
            return result_obj
            
        return {
            "warning": f"Output truncated (Size: {len(final_json)/1024:.1f}KB > {max_size/1024:.0f}KB limit).",
            "summary": "Result too large for context window. Please use specific filters or IDs.",
            "partial_data": str(final_json)[:1000] + "... [TRUNCATED]"
        }
    except Exception as e:
        logger.error(f"Error during output truncation check: {e}")
        return result_obj # Fallback to full object if check fails


class RepoToolsServer:
    def __init__(self, config: ServerConfig, search_config: SearchConfig = None):
        self.config = config
        self.search_config = search_config or SearchConfig()
        self.security = SecurityValidator(config)
        self.audit = AuditLogger()
        self.server = Server(config.name)
        self.approval_secret = os.getenv("MCP_APPROVAL_SECRET", "dev-secret-change-in-prod")
        
        # Initialize Context
        self.ctx = ToolContext(
            config=self.config,
            security=self.security,
            audit=self.audit,
            search_config=self.search_config,
            approval_secret=self.approval_secret
        )
        
        self._register_tools()
        logger.info(f"Initialized {config.name} v{config.version}")
        logger.info(f"Allowed roots: {[str(r) for r in config.allowed_roots]}")
        if not GIT_AVAILABLE:
            logger.warning("GitPython not available - write operations disabled")
            
        self._validate_environment()

    def _validate_environment(self):
        """Check for critical environment variables."""
        missing = []
        if not os.getenv("FIGMA_ACCESS_TOKEN"):
            missing.append("FIGMA_ACCESS_TOKEN")
        if not os.getenv("GITHUB_TOKEN"):
            missing.append("GITHUB_TOKEN")
            
        if missing:
            logger.error(f"CRITICAL: Missing configuration! Please check .env file. Missing: {', '.join(missing)}")
            # We don't raise Exception to allow partial functionality (e.g. read_file)
        else:
            logger.info("Environment configuration verified.")

    def _tool_schemas(self) -> List[Tool]:
        return [
            Tool(
                name="list_repo_files",
                description="List files and directories in a repository path",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "minLength": 1},
                        "path": {"type": "string", "default": "."}
                    },
                    "required": ["repo"]
                }
            ),
            Tool(
                name="read_file",
                description="Read contents of a text file. If repo is omitted, searches all allowed roots for the file by name.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "minLength": 1},
                        "file": {"type": "string", "minLength": 1}
                    },
                    "required": ["file"]
                }
            ),
            Tool(
                name="locate_component",
                description="Find files by name hint (any extension)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "hint": {"type": "string", "minLength": 1}
                    },
                    "required": ["hint"]
                }
            ),
            Tool(
                name="search_content",
                description="Search for multi-line code blocks or content across files. Finds exact consecutive line matches and returns file paths with line ranges where the block appears.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "minLength": 1},
                        "repo": {"type": "string", "minLength": 1},
                        "case_sensitive": {"type": "boolean", "default": False}
                    },
                    "required": ["content"]
                }
            ),
            Tool(
                name="create_branch",
                description="Create a new Git branch in a repository. Requires approval token for write operation.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "minLength": 1},
                        "branch": {"type": "string", "minLength": 1},
                        "from_ref": {"type": "string", "default": "HEAD"},
                        "approval_token": {"type": "object"}
                    },
                    "required": ["repo", "branch"]
                }
            ),
            Tool(
                name="fetch_figma_pattern",
                description="Fetch design nodes/styles/variables from a Figma file (read-only).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_key": {"type": "string", "minLength": 8},
                        "node_ids": {
                            "type": "array",
                            "items": {"type": "string", "minLength": 3},
                            "minItems": 1
                        },
                        "include_tokens": {"type": "boolean", "default": True},
                        "depth": {"type": "integer", "minimum": 1, "maximum": 10}
                    },
                    "required": ["file_key"]
                }
            ),
            Tool(
                name="generate_react_code",
                description="Generate React code (JS/TSX/TS/JS) from a normalized Figma pattern (dry-run).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "component_name": {"type": "string", "minLength": 1, "maxLength": 128},
                        "pattern": {"type": "object"},
                        "language": {"type": "string", "enum": ["js", "jsx", "ts", "tsx"], "default": "tsx"},
                        "styling": {
                            "type": "string",
                            "enum": ["css-modules", "styled-components", "emotion", "tailwind", "mui"],
                            "default": "tailwind"
                        },
                        "props_strategy": {
                            "type": "string",
                            "enum": ["minimal", "explicit", "tokens-as-props"],
                            "default": "explicit"
                        }
                    },
                    "required": ["component_name", "pattern"]
                }
            ),
            Tool(
                name="save_code_file",
                description="Persist generated React code to a local file. Requires approval token.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "output_path": {"type": "string", "minLength": 1, "maxLength": 4096},
                        "file_name": {"type": "string", "minLength": 1, "maxLength": 256, "pattern": "^[A-Za-z0-9._\\-/]+$"},
                        "code": {"type": "string", "minLength": 1, "maxLength": 200000},
                        "approval_token": {"type": "object"}
                    },
                    "required": ["output_path", "file_name", "code"]
                }
            ),
            Tool(
                name="list_pending_events",
                description="List pending Figma webhook events from the inbox. Returns recent file update events that haven't been processed.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100}
                    },
                    "required": []
                }
            ),
            Tool(
                name="mark_event_processed",
                description="Mark a webhook event as processed after handling it.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "integer", "minimum": 1}
                    },
                    "required": ["event_id"]
                }
            )
        ]

    def _register_tools(self):
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return self._tool_schemas()

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            start_time = datetime.now()
            try:
                # Dispatch to Modular Functions
                if name == "list_repo_files":
                    result_obj = await filesystem.list_repo_files(self.ctx, arguments)
                elif name == "read_file":
                    result_obj = await filesystem.read_file(self.ctx, arguments)
                elif name == "locate_component":
                    result_obj = await filesystem.locate_component(self.ctx, arguments)
                elif name == "search_content":
                    result_obj = await filesystem.search_content(self.ctx, arguments)
                elif name == "create_branch":
                    result_obj = await git.create_branch(self.ctx, arguments)
                elif name == "fetch_figma_pattern":
                    result_obj = await figma.fetch_figma_pattern(self.ctx, arguments)
                elif name == "generate_react_code":
                    result_obj = await figma.generate_react_code(self.ctx, arguments)
                elif name == "save_code_file":
                    result_obj = await filesystem.save_code_file(self.ctx, arguments)
                elif name == "list_pending_events":
                    result_obj = await figma.list_pending_events(self.ctx, arguments)
                elif name == "mark_event_processed":
                    result_obj = await figma.mark_event_processed(self.ctx, arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                duration = (datetime.now() - start_time).total_seconds() * 1000
                self.audit.log(AuditLog(
                    timestamp=datetime.now().isoformat(),
                    tool_name=name,
                    inputs=arguments,
                    outputs=None,
                    duration_ms=duration,
                    success=True,
                    target_ref=result_obj.get("target_ref") if isinstance(result_obj, dict) else None
                ))
                
                # Output Truncation Prevention (Context Saturation Fix)
                truncated_obj = truncate_large_output(result_obj)
                return [TextContent(type="text", text=json.dumps(truncated_obj))]
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                self.audit.log(AuditLog(
                    timestamp=datetime.now().isoformat(),
                    tool_name=name,
                    inputs=arguments,
                    outputs=None,
                    duration_ms=duration,
                    success=False,
                    error=str(e)
                ))
                raise

    async def run_stdio(self):
        logger.info("Starting MCP server with stdio transport")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, self.server.create_initialization_options())
