
import asyncio
import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Ensure mcp_core is importable
sys.path.append(str(Path(__file__).parent.parent))

from mcp_core.server import RepoToolsServer
from mcp_core.config import ServerConfig

# Configure logging to capture output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_truncation():
    print("\n--- Testing Output Truncation ---")
    from mcp_core.server import truncate_large_output
    
    # Create a massive dummy result
    massive_data = {"data": "x" * 150000} # 150KB > 100KB limit
    
    # Test function directly
    result = truncate_large_output(massive_data)
    
    if "warning" in result and "Output truncated" in result["warning"]:
        print("Truncation Successful!")
        print(f"Warning: {result['warning']}")
    else:
        print("Truncation Failed.")
        print(f"Result keys: {result.keys()}")

async def test_figma_404_handling():
    print("\n--- Testing Figma 404 Handling ---")
    
    # We need to test fetch_figma_pattern
    from mcp_core.tools import figma
    from mcp_core.context import ToolContext
    
    ctx = MagicMock(spec=ToolContext)
    
    # Mock httpx to raise HTTPStatusError(404)
    with patch("httpx.AsyncClient") as mock_client, \
         patch("os.getenv", return_value="dummy_token"):
        
        mock_get = AsyncMock()
        mock_client.return_value.__aenter__.return_value.get = mock_get
        
        # Create a mock 404 response
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not Found"
        
        # To trigger clean exception handling, we need raise_for_status to raise
        import httpx
        def raise_404():
            raise httpx.HTTPStatusError("404 Not Found", request=None, response=mock_resp)
        
        mock_resp.raise_for_status.side_effect = raise_404
        mock_get.return_value = mock_resp
        
        # Run tool
        result = await figma.fetch_figma_pattern(ctx, {"file_key": "INVALID_KEY"})
        
        if result["success"] is False and result["status_code"] == 404:
            print("404 Handling Successful!")
            print(result)
        else:
            print("404 Handling Failed.")
            print(result)

if __name__ == "__main__":
    asyncio.run(test_truncation())
    asyncio.run(test_figma_404_handling())
