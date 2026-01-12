import os
import requests
import asyncio
import logging
from typing import Dict, Any, List
from ..context import ToolContext
import json
import time

logger = logging.getLogger(__name__)

def _rgb_to_hex(color: Dict[str, float]) -> str:
    r = int(color.get('r', 0) * 255)
    g = int(color.get('g', 0) * 255)
    b = int(color.get('b', 0) * 255)
    return f"#{r:02x}{g:02x}{b:02x}"

from ..theme import DesignTokenMapper

def _get_color_str(hex_code: str) -> str:
    """Return mapped token or raw arbitrary value."""
    token = DesignTokenMapper.map_color(hex_code)
    if token:
        return token
    return f"[{hex_code}]"

def _get_spacing_str(px: float) -> str:
    """Return mapped spacing token or raw arbitrary value."""
    token = DesignTokenMapper.map_spacing(px)
    if token:
        return token
    return f"[{int(px)}px]"

def _extract_tailwind_classes(node: Dict[str, Any], parent_bbox: Dict[str, float] = None) -> str:
    classes = []
    style = node.get("style", {})
    # Dimensions & Responsiveness
    layout_align = node.get("layoutAlign")
    layout_grow = node.get("layoutGrow", 0)
    
    # Width
    if layout_align == "STRETCH" or layout_grow == 1:
        classes.append("w-full")
        if "width" in style and style['width'] > 0:
             w_val = _get_spacing_str(style['width'])
             classes.append(f"max-w-{w_val}")
    elif "width" in style:
        w = int(style['width'])
        if w > 1200:
             w_val = _get_spacing_str(w)
             classes.append(f"w-full max-w-{w_val} mx-auto")
        else:
             w_val = _get_spacing_str(w)
             classes.append(f"w-{w_val}")
            
    # Height
    if layout_grow == 1:
        classes.append("h-full")
    elif "height" in style:
        h_val = _get_spacing_str(style['height'])
        classes.append(f"h-{h_val}")

    # Positioning
    if node.get("layoutPositioning") == "ABSOLUTE":
        classes.append("absolute")
        constraints = node.get("constraints", {})
        h_const = constraints.get("horizontal", "LEFT")
        v_const = constraints.get("vertical", "TOP")
        
        # Calculate relative position using Bounding Box if available
        # Default to node's own x/y which are usually parent-relative
        rel_x = node.get("x", 0)
        rel_y = node.get("y", 0)
        
        node_bbox = node.get("absoluteBoundingBox")
        if parent_bbox and node_bbox:
            # Re-calculate relative to ensure accuracy, especially for groups
            rel_x = node_bbox["x"] - parent_bbox["x"]
            rel_y = node_bbox["y"] - parent_bbox["y"]
        
        # Horizontal
        if h_const == "RIGHT":
             val = _get_spacing_str(rel_x)
             classes.append(f"left-{val}") 
        elif h_const == "CENTER":
             classes.append("left-1/2 -translate-x-1/2")
        else:
             val = _get_spacing_str(rel_x)
             classes.append(f"left-{val}")
             
        # Vertical
        if v_const == "BOTTOM":
             val = _get_spacing_str(rel_y)
             classes.append(f"top-{val}")
        elif v_const == "CENTER":
             classes.append("top-1/2 -translate-y-1/2")
        else:
             val = _get_spacing_str(rel_y)
             classes.append(f"top-{val}")

    # Auto Layout (Flexbox)
    layout_mode = node.get("layoutMode")
    if layout_mode:
        classes.append("flex")
        if layout_mode == "VERTICAL":
            classes.append("flex-col")
        else:
            classes.append("flex-row")
        
        # Formatting alignment mapping
        primary_align = node.get("primaryAxisAlignItems")
        counter_align = node.get("counterAxisAlignItems")
        
        align_map = {
            "MIN": "start", "MAX": "end", "CENTER": "center", "SPACE_BETWEEN": "between"
        }
        
        if layout_mode == "HORIZONTAL":
            if primary_align in align_map: classes.append(f"justify-{align_map[primary_align]}")
            if counter_align in align_map: classes.append(f"items-{align_map[counter_align]}")
        else:
            if primary_align in align_map: classes.append(f"justify-{align_map[primary_align]}")
            if counter_align in align_map: classes.append(f"items-{align_map[counter_align]}")

        # Gap / Padding
        gap = node.get("itemSpacing")
        if gap and gap > 0: 
            g_val = _get_spacing_str(gap)
            classes.append(f"gap-{g_val}")
        
        p_left = node.get("paddingLeft", 0)
        p_right = node.get("paddingRight", 0)
        p_top = node.get("paddingTop", 0)
        p_bottom = node.get("paddingBottom", 0)
        
        if p_left == p_right == p_top == p_bottom and p_left > 0:
            val = _get_spacing_str(p_left)
            classes.append(f"p-{val}")
        else:
            if p_left > 0: classes.append(f"pl-{_get_spacing_str(p_left)}")
            if p_right > 0: classes.append(f"pr-{_get_spacing_str(p_right)}")
            if p_top > 0: classes.append(f"pt-{_get_spacing_str(p_top)}")
            if p_bottom > 0: classes.append(f"pb-{_get_spacing_str(p_bottom)}")

    # Background Color (Fills)
    fills = node.get("fills", [])
    bg_color = style.get("backgroundColor")
    
    if fills:
        for fill in fills:
            if not fill.get("visible", True):
                continue
                
            if fill.get("type") == "SOLID":
                hex_code = _rgb_to_hex(fill["color"])
                token = _get_color_str(hex_code)
                classes.append(f"bg-{token}")
                
                opacity = fill.get("opacity", 1)
                if opacity < 1:
                        classes.append(f"opacity-[{int(opacity*100)}]")
                break # Take first visible solid
                
            elif fill.get("type") == "GRADIENT_LINEAR":
                # Simple gradient approximation
                classes.append("bg-gradient-to-br")
                stops = fill.get("gradientStops", [])
                if len(stops) >= 2:
                    start_c = _rgb_to_hex(stops[0]["color"])
                    end_c = _rgb_to_hex(stops[-1]["color"])
                    classes.append(f"from-{_get_color_str(start_c)} to-{_get_color_str(end_c)}")
                break
                
    elif bg_color:
            hex_code = _rgb_to_hex(bg_color)
            classes.append(f"bg-{_get_color_str(hex_code)}")

    # Typography
    if node.get("type") == "TEXT":
        if "fontSize" in style:
            classes.append(f"text-[{int(style['fontSize'])}px]")
        if "fontWeight" in style:
            fw = style['fontWeight']
            if fw >= 700: classes.append("font-bold")
            elif fw >= 600: classes.append("font-semibold")
            elif fw >= 500: classes.append("font-medium")
        
        text_align = style.get("textAlignHorizontal", "LEFT")
        if text_align == "CENTER": classes.append("text-center")
        elif text_align == "RIGHT": classes.append("text-right")
        elif text_align == "JUSTIFIED": classes.append("text-justify")
        
        # Text Color
        text_fills = node.get("fills", [])
        style_color = style.get("color")
        
        if text_fills:
            for fill in text_fills:
                if fill.get("type") == "SOLID" and fill.get("visible", True):
                    hex_code = _rgb_to_hex(fill["color"])
                    classes.append(f"text-{_get_color_str(hex_code)}")
                    break
        elif style_color:
                hex_code = _rgb_to_hex(style_color)
                classes.append(f"text-{_get_color_str(hex_code)}")

    # Border Radius
    corner_radius = node.get("cornerRadius")
    if corner_radius:
        # Standard radii? 2->sm, 4->DEFAULT, 6->md, 8->lg, 12->xl, 16->2xl
        # For now, keeping arbitrary unless we map radii too.
        # Let's map small ones.
        cr = int(corner_radius)
        if cr == 2: classes.append("rounded-sm")
        elif cr == 4: classes.append("rounded")
        elif cr == 6: classes.append("rounded-md")
        elif cr == 8: classes.append("rounded-lg")
        elif cr == 12: classes.append("rounded-xl")
        elif cr == 16: classes.append("rounded-2xl")
        else:
            classes.append(f"rounded-[{cr}px]")
            
    elif style.get("borderRadius"):
            classes.append(f"rounded-[{int(style['borderRadius'])}px]")

    return " ".join(classes)

def _render_node_to_jsx(node: Dict[str, Any], assets: List[Dict[str, Any]], imports: List[str], registry: Any = None, indent_level: int = 2, parent_bbox: Dict[str, float] = None, heading_level: int = 2) -> str:
    from ..component_registry import ComponentRegistry
    
    if registry is None:
        registry = ComponentRegistry() # Fallback
    if node.get("visible") is False:
        return ""

    indent = "  " * indent_level
    node_type = node.get("type")
    
    # Calculate BBox for current node to pass to children
    current_bbox = node.get("absoluteBoundingBox")
    
    node_name = node.get("name", "").lower()
    node_id = node.get("id", "unknown")
    class_name = _extract_tailwind_classes(node, parent_bbox)
    
    # Check for Vector/Image assets to export
    is_asset = False
    
    # 1. Explicit VECTOR node
    if node_type == "VECTOR":
        is_asset = True
        
    # 2. Frame/Rect with IMAGE fill
    fills = node.get("fills", [])
    for fill in fills:
        if fill.get("type") == "IMAGE" and fill.get("visible", True):
            is_asset = True
            break

    if is_asset:
        # Create asset entry
        safe_name = "".join(c for c in node.get("name", "asset") if c.isalnum() or c in "-_").lower()
        if not safe_name: safe_name = f"asset_{node_id.replace(':','_')}"
        
        asset_filename = f"{safe_name}.svg" # Default to SVG for consistency
        
        # Dedupe by ID
        existing = next((a for a in assets if a["id"] == node_id), None)
        if not existing:
            assets.append({
                "id": node_id,
                "name": safe_name,
                "filename": asset_filename,
                "type": node_type
            })
        else:
            asset_filename = existing["filename"]
        
        # Render as img
        # A11y: Use description for alt if available, or name
        alt_text = node.get("description", node.get("name", "Asset"))
        return f'{indent}<img src="/assets/{asset_filename}" alt="{alt_text}" aria-label="{alt_text}" className="{class_name}" />'

    # Determine Tag (Semantic HTML Inference or Smart Component)
    tag = "div"
    
    # Check Registry for Match
    match = registry.find_match(node_name)
    if match:
        tag = match["component"]
        # Assuming source path provided in registry mapping
        import_stmt = f'import {{ {tag} }} from "{match["path"]}";'
        if import_stmt not in imports:
            imports.append(import_stmt)
    

    # If no smart component matched, fallback to semantic HTML inference
    if tag == "div":
        if node_type == "TEXT":
            tag = "p"
            if "heading" in node_name: 
                tag = f"h{min(heading_level, 6)}"
            elif "title" in node_name: 
                tag = "h1"
            elif "label" in node_name: 
                tag = "span"
        elif "button" in node_name or "btn" in node_name:
            tag = "button"
        elif "input" in node_name or "field" in node_name:
            tag = "input"
        elif "header" in node_name or "nav" in node_name:
            tag = "header"
        elif "footer" in node_name:
            tag = "footer"
        elif "section" in node_name:
            tag = "section"
        elif "card" in node_name:
            tag = "article"
    
    # Content
    content = ""
    children_jsx = ""
    
    if node_type == "TEXT":
        # Escape braces for JSX
        raw_text = node.get("characters", node.get("content", ""))
        safe_text = raw_text.replace("{", "{'{'").replace("}", "{'}'}")
        content = safe_text

    elif "children" in node:
        # Determine next heading level based on context
        next_level = heading_level
        if "section" in node_name or "article" in node_name:
            next_level += 1
            
        child_nodes = node["children"]
        for child in child_nodes:
            children_jsx += "\n" + _render_node_to_jsx(child, assets, imports, registry, indent_level + 1, current_bbox, heading_level=next_level)
        if children_jsx:
            children_jsx += f"\n{indent}"

    # Props string
    props_list = []
    if class_name:
        props_list.append(f'className="{class_name}"')
        
    # Interaction Detection (Prototype)
    # Check for simple transition triggers as a proxy for "onClick"
    # Note: Real Figma structure puts interactions in 'interactions' array, or implicit via prototypeDevice
    # But usually transitionNodeID implies a navigate action on click.
    if node.get("transitionNodeID") or node.get("onClick"): # Fallback for our own mock if we injected it
        props_list.append("onClick={() => {}}")
        # Ensure cursor-pointer is added if not already
        if "cursor-pointer" not in class_name:
             # Hacky append to class prop if it exists, or logic above needs query
             # Simpler: just replace the className prop in list or append to class_name string earlier.
             # Better: modify class_name earlier. But here we are post-extraction.
             # Let's direct append to the props string for simplicity in this regex-free generation
             pass 

    # A11y: Description -> aria-label
    description = node.get("description")
    # Figma component description sometimes in different fields, trusting raw node has it or injected
    if description:
        props_list.append(f'aria-label="{description}"')

    # A11y: Interactive Roles
    is_interactive = node.get("transitionNodeID") or node.get("onClick")
    if is_interactive:
         if tag not in ["button", "a", "input"]:
             props_list.append('role="button"')
             props_list.append('tabIndex={0}')
         
         if 'className="' in props_list[0] if props_list else "":
             props = props_list[0]
             # check if we already added cursor-pointer (logic above was slightly messy in diffs)
             if "cursor-pointer" not in props:
                 props_list[0] = props[:-1] + ' cursor-pointer"'
         elif not any("className" in p for p in props_list):
             props_list.append('className="cursor-pointer"')

    # Semantic Engine: Inject ID for diffing
    # We strip colon for cleaner HTML attributes if needed, but keeping raw ID is safer for uniqueness
    props_list.append(f'data-mcp-id="{node_id}"')

    props = " ".join(props_list)
    
    if not content and not children_jsx:
        return f"{indent}<{tag} {props} />"
    
    return f"{indent}<{tag} {props}>{content}{children_jsx}</{tag}>"

async def fetch_figma_pattern(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch design nodes from Figma using httpx for true async I/O."""
    import httpx
    
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

async def download_figma_assets(ctx: ToolContext, file_key: str, assets: List[Dict[str, Any]], output_dir: str = "public/assets") -> List[Dict[str, Any]]:
    """
    Download image assets from Figma API and save to local disk.
    Returns updated assets list with local paths.
    """
    import httpx
    import aiofiles
    from pathlib import Path
    
    if not assets:
        return assets
        
    token = os.getenv("FIGMA_ACCESS_TOKEN")
    if not token:
        logger.warning("No Figma token found, skipping asset download.")
        return assets

    headers = {"X-Figma-Token": token}
    asset_ids = [a["id"] for a in assets]
    ids_str = ",".join(asset_ids)
    
    # 1. Get Image URLs
    # We default to SVG for vector assets, PNG for others could be an option but SVG is safest for exact rendering
    url = f"https://api.figma.com/v1/images/{file_key}?ids={ids_str}&format=svg"
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            image_map = data.get("images", {})
        except Exception as e:
            logger.error(f"Failed to fetch image URLs: {e}")
            return assets
            
        # 2. Download and Save
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        updated_assets = []
        for asset in assets:
            node_id = asset["id"]
            img_url = image_map.get(node_id)
            
            if not img_url:
                logger.warning(f"No URL found for asset {node_id}")
                updated_assets.append(asset)
                continue
                
            try:
                img_resp = await client.get(img_url)
                img_resp.raise_for_status()
                
                filename = asset["filename"]
                file_path = f"{output_dir}/{filename}"
                
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(img_resp.content)
                    
                asset["local_path"] = file_path
                updated_assets.append(asset)
                
            except Exception as e:
                logger.error(f"Failed to download asset {node_id}: {e}")
                updated_assets.append(asset)
                
        return updated_assets

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

async def generate_react_code(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    from ..component_registry import ComponentRegistry
    
    component_name = args["component_name"]
    pattern = args["pattern"]
    language = args.get("language", "tsx")
    
    registry = ComponentRegistry()
    assets = []
    found_imports = [] 
    # Start recursion. Top level node usually has no parent_bbox context unless we fetch parent frame too.
    # We assume pattern root is our component container.
    # Start recursion. Top level node usually has no parent_bbox context unless we fetch parent frame too.
    # We assume pattern root is our component container.
    jsx_body = _render_node_to_jsx(pattern, assets, found_imports, registry, indent_level=2, parent_bbox=None, heading_level=2)
    
    # If file_key is provided (found via args or context?), invoke download.
    # Currently generate_react_code args doesn't strictly require file_key, but fetch_figma_pattern does.
    # We'll rely on args passing it if available, or skip.
    file_key = args.get("file_key")
    if assets and file_key:
        # Download assets (non-blocking if we awaited parallel, here we await the process)
        # Note: In a real server, might want to background this? But for generation we usually want result.
        assets = await download_figma_assets(ctx, file_key, assets)
    
    # Wrap body in markers and Fragment for merging
    marked_body = f"""<>
    {{/* @mcp-begin:view */}}
{jsx_body}
    {{/* @mcp-end:view */}}
    </>"""

    code = f"""import React from 'react';

export const {component_name} = () => {{
  return (
{marked_body}
  );
}};
"""

    # Check for existing file to merge (unless skipped)
    # We try to find the file in the workspace to preserve imports/hooks
    from ..tools.filesystem import list_repo_files, read_file
    from ..utils.code_merger import CodeMerger
    import os
    
    # Check if merge is explicitly disabled
    skip_merge = args.get("skip_merge", False)
    
    # Simple search: Try to find {component_name}.tsx in allowed roots
    # In a real app we might cache this or use the registry if it was registered.
    existing_content = None
    found_path = None
    
    # Only try to find logic if we intend to merge
    if not skip_merge and ctx.config.allowed_roots:
        root = ctx.config.allowed_roots[0] # Assume primary root
        for r, d, f in os.walk(root):
            if f"{component_name}.tsx" in f:
                found_path = os.path.join(r, f"{component_name}.tsx")
                break
    
    if found_path:
        try:
            with open(found_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
            
            # Merge
            code = CodeMerger.merge(existing_content, code)
            logger.info(f"Merged code for {component_name} with existing file at {found_path}")
        except Exception as e:
            logger.warning(f"Failed to merge with existing file {found_path}: {e}")

    return {
        "file_name": f"{component_name}.{language}",
        "code": code,
        "imports": ["react"] + found_imports,
        "assets": assets
    }

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

async def scan_components(ctx: ToolContext, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scan the repository for React components and populate the registry.
    """
    from ..component_registry import ComponentRegistry
    from ..tools.filesystem import list_repo_files, read_file
    import re
    
    repo = args.get("repo")
    if not repo:
        # Try to infer or default? For now require it or assume 1st allowed
        repo = ctx.config.allowed_repos[0] if ctx.config.allowed_repos else None
        
    if not repo:
        return {"success": False, "message": "No repository specified"}
        
    registry = ComponentRegistry()
    
    # 1. List all TSX files in common component directories
    # In a real app we'd recurse or have smarter config. 
    # For now, let's look in a hypothetical 'components' or 'src/components' root.
    # based on filesystem tool, we can walk? 
    # The filesystem tool implementation list_repo_files is shallow or uses native walk if local. 
    # Let's assume we can find them. For this MVP, let's scan a fixed set of confirmed paths if possible
    # or just assume a flat structure for the demo if 'recursive' isn't exposed easily via existing tools without overhead.
    # Wait, list_repo_files DOES support recursive listing if we implemented it right? 
    # Actually list_repo_files in `filesystem.py` usually just does os.scandir.
    # Let's try to grab a few known UI kit paths or just the root 'components' dir.
    
    target_dirs = ["components", "src/components", "components/ui"]
    found_files = []
    
    # Hack: We can't easy-walk via 'list_repo_files' without recursion loop here.
    # But since we are INSIDE the server code, we can use direct OS access if allowed by security.
    # SecurityValidator validates PATHS. 
    # Let's use os.walk on the repo root provided config allows it.
    
    repo_root = None
    for root in ctx.config.allowed_roots:
        possible = root / repo
        if possible.exists():
            repo_root = possible
            break
            
    if not repo_root:
         # Fallback for single-root config where repo name might be virtual or mapped
         if len(ctx.config.allowed_roots) == 1:
             repo_root = ctx.config.allowed_roots[0]
    
    if not repo_root or not repo_root.exists():
        return {"success": False, "message": f"Repository root not found for {repo}"}
        
    count = 0
    scanned = []
    
    for r, d, f in os.walk(repo_root):
        for file in f:
            if file.endswith(".tsx") or file.endswith(".jsx"):
                full_path = os.path.join(r, file)
                # Parse for "export const X" or "export function X"
                try:
                    with open(full_path, 'r', encoding='utf-8') as f_obj:
                        content = f_obj.read()
                        
                        # Regex for exports
                        matches = re.findall(r'export\s+(?:const|function)\s+([A-Z][a-zA-Z0-9_]*)', content)
                        for comp_name in matches:
                             # Heuristic: Figma Name = Component Name with spaces? 
                             # e.g. "PrimaryButton" -> "Primary Button"
                             # e.g. "UserProfile" -> "User Profile"
                             case_split = re.sub(r"([a-z])([A-Z])", r"\1 \2", comp_name)
                             
                             rel_path = os.path.relpath(full_path, repo_root).replace("\\", "/")
                             # convert to import path (remove .tsx, add @/)
                             # This is highly project specific. Let's assume alias @/
                             import_path = f"@/{rel_path.rsplit('.', 1)[0]}"
                             
                             registry.register_component(case_split, comp_name, import_path)
                             
                             scanned.append(f"{case_split} -> {comp_name}")
                             count += 1
                except Exception as e:
                    logger.warning(f"Error scanning {full_path}: {e}")
                    
    return {
        "success": True,
        "scanned_count": count,
        "mappings": scanned,
        "registry_path": registry.registry_path
    }

async def coalesce_events(ctx: ToolContext, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Groups events by 'file_key' + 'file_name', keeps only the latest one per group.
    Old events in the batch are marked as 'skipped_redundant' in the DB.
    Writes a summary to 'pending_batch.json'.
    """
    import aiosqlite
    from pathlib import Path

    if not events:
        return []

    # 1. Group by unique key
    grouped = {}
    for ev in events:
        # Create a unique key for the resource being modified
        key = f"{ev['file_key']}::{ev['file_name']}"
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(ev)

    unique_events = []
    redundant_ids = []

    # 2. Filter keeping only latest
    for key, group in grouped.items():
        # Sort by timestamp descending (newest first)
        # Assuming 'timestamp' is a float or comparable. 
        # If timestamp is missing, fall back to 'created_at' or 0
        group.sort(key=lambda x: x.get("timestamp") or 0, reverse=True)
        
        # Keep the winner
        winner = group[0]
        unique_events.append(winner)
        
        # Collect losers
        for loser in group[1:]:
            redundant_ids.append(loser["id"])

    # 3. Update DB for redundant events
    if redundant_ids:
        db_path = Path(__file__).parent.parent.parent / "events.db"
        logger.info(f"🧹 Coalescing: Check {len(events)} events -> {len(unique_events)} unique. Skipping {len(redundant_ids)} redundant.")
        
        try:
            async with aiosqlite.connect(db_path) as conn:
                # Batch update
                # 'events' table, 'id' column.
                placeholders = ",".join("?" * len(redundant_ids))
                query = f"UPDATE events SET status = 'skipped_redundant' WHERE id IN ({placeholders})"
                
                await conn.execute(query, redundant_ids)
                await conn.commit()
        except Exception as e:
            logger.error(f"Failed to mark redundant events: {e}")

    # 4. Report
    report = {
        "timestamp": time.time(),
        "total_incoming": len(events),
        "unique_count": len(unique_events),
        "redundant_count": len(redundant_ids),
        "processed_groups": list(grouped.keys())
    }
    
    try:
        with open("pending_batch.json", "w") as f:
            json.dump(report, f, indent=2)
    except Exception:
        pass

    return unique_events

