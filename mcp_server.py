"""
MCP Server – Sprint 1 (Refined)
Wrapper around mcp_core package.
"""
import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import from new package
from mcp_core import RepoToolsServer, ServerConfig

# Configure logging here (application entry point)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)

async def main():
    # Use absolute path relative to this script file
    base_dir = Path(__file__).parent.resolve()
    
    config = ServerConfig(
        # Use "*" to allow any folder found in allowed_roots to be accessed as a repo
        allowed_repos=["*"],
        # Add Desktop as a root so any folder on Desktop can be found by name
        allowed_roots=[Path.home() / "Desktop", base_dir],
        max_file_size=1_000_000
    )
    server = RepoToolsServer(config)
    await server.run_stdio()

if __name__ == "__main__":
    asyncio.run(main())
