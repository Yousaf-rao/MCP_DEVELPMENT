import os
import asyncio
import logging
import sqlite3
import json
from pathlib import Path
from dotenv import load_dotenv

# Import our modular tools and utils
from mcp_core.context import ToolContext
from mcp_core.tools import figma
from mcp_core.utils.github_automation import create_figma_update_pr

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AutomationWorker")

load_dotenv()

DB_PATH = Path(__file__).parent / "events.db"
POLL_INTERVAL = 30 # seconds

async def process_pending_events(ctx: ToolContext):
    """
    Checks the inbox for pending Figma events and creates GitHub PRs.
    """
    if not DB_PATH.exists():
        return

    # 1. Fetch pending events
    events_result = await figma.list_pending_events(ctx, {"limit": 10})
    events = events_result.get("events", [])
    
    if not events:
        return

    logger.info(f"Found {len(events)} pending events to process...")

    for event in events:
        event_id = event["id"]
        file_key = event["file_key"]
        file_name = event["file_name"]
        
        try:
            logger.info(f"Processing event {event_id} for file: {file_name}")
            
            # 2. Fetch design pattern from Figma
            pattern_result = await figma.fetch_figma_pattern(ctx, {"file_key": file_key, "depth": 4})
            
            # 3. Generate React component code
            # Note: In a real scenario, we might want to target specific frames.
            # Here we'll generate code for the first node as a default.
            if not pattern_result.get("nodes"):
                logger.warning(f"No nodes found for file {file_key}, skipping.")
                await figma.mark_event_processed(ctx, {"event_id": event_id})
                continue
                
            main_node = pattern_result["nodes"][0]
            comp_name = file_name.replace(" ", "").replace("-", "")
            
            gen_result = await figma.generate_react_code(ctx, {
                "component_name": comp_name,
                "pattern": main_node
            })
            
            code = gen_result["code"]
            
            # Use configurable output path
            output_dir = os.getenv("CODE_GEN_OUTPUT_PATH", "src/components/generated")
            file_path = f"{output_dir}/{gen_result['file_name']}"
            
            # 4. Create GitHub PR
            # 4. Create GitHub PR (Run in executor to avoid blocking event loop)
            logger.info(f"Creating GitHub PR for {comp_name}...")
            loop = asyncio.get_running_loop()
            pr_url = await loop.run_in_executor(
                None, 
                create_figma_update_pr, 
                file_path, 
                code, 
                file_name, 
                file_key
            )
            
            if pr_url:
                logger.info(f"✅ Created PR: {pr_url}")
                # 5. Mark as processed
                await figma.mark_event_processed(ctx, {"event_id": event_id})
            else:
                logger.error(f"❌ Failed to create PR for event {event_id}")

        except Exception as e:
            logger.error(f"Error processing event {event_id}: {str(e)}")

async def main():
    logger.info("Figma-to-GitHub Automation Worker Started")
    
    # Initialize a mock context for our tools
    ctx = ToolContext(
        config=None, security=None, audit=None, 
        search_config=None, approval_secret="automation-secret"
    )

    while True:
        await process_pending_events(ctx)
        await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
