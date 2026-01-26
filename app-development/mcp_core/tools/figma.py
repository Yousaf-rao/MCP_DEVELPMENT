"""
figma.py - Figma API and Event Management Tools

This module provides:
- Figma API integration for fetching design data
- Image download utilities for vision-enhanced processing
- Event queue management for webhook events
"""
import os
import asyncio
import logging
import httpx
from typing import Dict, Any, List
from ..context import ToolContext

logger = logging.getLogger(__name__)


# ============================================================
# FIGMA API FUNCTIONS
# ============================================================

async def fetch_figma_pattern(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch design nodes from Figma using httpx for true async I/O."""
    file_key = args["file_key"]
    node_ids = args.get("node_ids", [])
    depth = args.get("depth", 4)
    token = os.getenv("FIGMA_ACCESS_TOKEN")
    
    if not token:
        raise ValueError("FIGMA_ACCESS_TOKEN environment variable is not set")
    
    headers = {"X-Figma-Token": token}
    max_retries = 3
    base_delay = 2
    
    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                # Use /nodes if specific IDs are provided, otherwise /files
                if node_ids:
                    ids_str = ",".join(node_ids)
                    url = f"https://api.figma.com/v1/files/{file_key}/nodes?ids={ids_str}&depth={depth}"
                else:
                    url = f"https://api.figma.com/v1/files/{file_key}?depth={depth}"
                    
                resp = await client.get(url, headers=headers, timeout=15)
                
                if resp.status_code == 429:
                    if attempt < max_retries - 1:
                        header_val = resp.headers.get('Retry-After')
                        if header_val:
                            retry_after = int(header_val)
                        else:
                            retry_after = base_delay * (2 ** attempt)
                        
                        # Cap at 60s
                        retry_after = min(retry_after, 60)
                        
                        logger.warning(f"[Figma Rate Limit] Attempt {attempt+1} failed. Sleeping {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        raise RuntimeError("Figma API rate limit exceeded.")
                
                resp.raise_for_status()
                data = resp.json()
                
                # Normalize results
                if node_ids:
                    # /nodes endpoint structure
                    nodes_data = data.get("nodes", {})
                    nodes = [v["document"] for v in nodes_data.values() if "document" in v]
                    file_name = data.get("name", "Unknown File")
                    last_modified = data.get("lastModified")
                else:
                    # /files endpoint structure
                    nodes = [data["document"]]
                    file_name = data.get("name", "Unknown File")
                    last_modified = data.get("lastModified")
                    
                tokens = {
                    "colors": {},
                    "components": data.get("components", {}),
                    "styles": data.get("styles", {})
                }
                
                return {
                    "file_key": file_key,
                    "name": file_name,
                    "last_modified": last_modified,
                    "nodes": nodes,
                    "tokens": tokens
                }
                
            except httpx.RequestError as e:
                logger.error(f"Figma API connection error: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(base_delay * (attempt + 1))
                    continue
                return {
                    "success": False,
                    "error": f"Figma API connection error: {str(e)}",
                    "status_code": 0
                }
            except httpx.HTTPStatusError as e:
                logger.error(f"Figma API status error: {e}")
                return {
                    "success": False,
                    "error": f"Figma API error: {e.response.text}",
                    "status_code": e.response.status_code
                }
            except Exception as e:
                logger.error(f"Figma processing error: {e}")
                return {
                    "success": False,
                    "error": f"Figma API processing error: {str(e)}",
                    "status_code": 500
                }
                
    return {
        "success": False,
        "error": "Failed to fetch Figma design after multiple attempts",
        "status_code": 408
    }


# ============================================================
# IMAGE DOWNLOAD FUNCTIONS (For Vision-Enhanced Processing)
# ============================================================

async def fetch_node_image_url(ctx: ToolContext, file_key: str, node_id: str) -> str:
    """
    Fetches the rendered image URL for a specific node from Figma.
    Used for Vision-Enhanced Routing.
    """
    import httpx
    
    token = os.getenv("FIGMA_ACCESS_TOKEN")
    if not token:
        return None
        
    headers = {"X-Figma-Token": token}
    url = f"https://api.figma.com/v1/images/{file_key}?ids={node_id}&format=png"
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch image URL: {resp.status_code}")
                return None
                
            data = resp.json()
            images = data.get("images", {})
            return images.get(node_id)
            
        except Exception as e:
            logger.error(f"Error fetching node image URL: {e}")
            return None


async def download_node_image_to_temp(ctx: ToolContext, file_key: str, node_id: str) -> str:
    """
    Fetches URL and downloads image to a temp file. Returns path or None.
    """
    import tempfile
    import httpx
    import aiofiles
    
    img_url = await fetch_node_image_url(ctx, file_key, node_id)
    if not img_url:
        return None
        
    try:
        # Create temp file
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tf.close()
        temp_path = tf.name
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(img_url)
            if resp.status_code == 200:
                async with aiofiles.open(temp_path, "wb") as f:
                    await f.write(resp.content)
                return temp_path
                
        return None
    except Exception as e:
        logger.error(f"Failed to download temp image: {e}")
        return None


# ============================================================
# EVENT QUEUE MANAGEMENT (Webhook Events)
# ============================================================

async def list_pending_events(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    """List pending Figma webhook events from the database."""
    import aiosqlite
    from pathlib import Path
    
    db_path = Path(__file__).parent.parent.parent / "events.db"
    if not db_path.exists():
        return {"events": [], "count": 0, "message": "No events database found"}
    
    limit = args.get("limit", 20)
    
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("""
            SELECT id, event_id, event_type, file_key, file_name, node_id, timestamp, created_at
            FROM events
            WHERE status = 'pending'
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        events = []
        rows = await cursor.fetchall()
        for row in rows:
            events.append({
                "id": row[0],
                "event_id": row[1],
                "event_type": row[2],
                "file_key": row[3],
                "file_name": row[4],
                "node_id": row[5],
                "timestamp": row[6],
                "created_at": row[7]
            })
        
        return {"events": events, "count": len(events)}


async def mark_event_processed(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    """Mark a webhook event as processed (or other status)."""
    import aiosqlite
    from pathlib import Path
    
    db_path = Path(__file__).parent.parent.parent / "events.db"
    event_id = args["event_id"]
    status = args.get("status", "processed")
    
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("""
            UPDATE events
            SET status = ?
            WHERE id = ?
        """, (status, event_id,))
        
        await conn.commit()
        rows_affected = cursor.rowcount
        
        return {
            "success": rows_affected > 0,
            "event_id": event_id,
            "message": "Event marked as processed" if rows_affected > 0 else "Event not found"
        }
