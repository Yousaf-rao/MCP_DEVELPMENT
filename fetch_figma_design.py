import asyncio
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load env vars
load_dotenv()

from mcp_core import ServerConfig, SearchConfig
from mcp_core.context import ToolContext
from mcp_core.security import SecurityValidator
from mcp_core.audit import AuditLogger
from mcp_core.tools.figma import fetch_figma_pattern

# Configure logging
logging.basicConfig(level=logging.INFO)

async def main():
    file_key = "wj7cqOLxDZ29U5ZcVxIjXU"
    
    # Check token
    token = os.getenv("FIGMA_ACCESS_TOKEN")
    if not token or "your_token" in token:
        print("Error: FIGMA_ACCESS_TOKEN not set or is a placeholder in .env")
        return

    # Mock Context
    config = ServerConfig()
    security = SecurityValidator(config)
    audit = AuditLogger()
    search_config = SearchConfig()
    
    ctx = ToolContext(
        config=config,
        security=security,
        audit=audit,
        search_config=search_config,
        approval_secret="test-secret"
    )
    
    print(f"Fetching Figma design for key: {file_key}...")
    try:
        result = await fetch_figma_pattern(ctx, {"file_key": file_key, "depth": 2})
        
        # Save to file
        output_file = "figma_design.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
            
        print(f"Successfully fetched design! Saved to {output_file}")
        print(f"Name: {result.get('name')}")
        print(f"Last Modified: {result.get('last_modified')}")
        print(f"Node Count: {len(result.get('nodes', []))}")
        
    except Exception as e:
        print(f"Error fetching design: {e}")

if __name__ == "__main__":
    asyncio.run(main())
