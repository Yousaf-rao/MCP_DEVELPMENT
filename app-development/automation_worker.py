import os
import asyncio
import logging
import sqlite3
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Import our modular tools and utils
from mcp_core.context import ToolContext
from mcp_core.tools import figma
from mcp_core.utils.github_automation import create_figma_update_pr, get_repo_file_structure
from mcp_core.services.llm_coder import LLMCoder
from mcp_core.services.router_cache import RouterCache
from mcp_core.services.repo_search import RepoSearch # <--- NEW
from mcp_core.utils.validator import validate_code

def get_project_context():
    """
    Reads critical context files to send to the LLM so it matches your style.
    """
    context = ""
    # Example: Read your tailwind config or a global styles file
    # We look for tailwind.config.js or tailwind.config.ts
    for config_file in ["tailwind.config.js", "tailwind.config.ts"]:
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    context += f"// {config_file}\n{f.read()}\n"
            except Exception:
                pass
    return context

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AutomationWorker")

load_dotenv()

DB_PATH = Path(__file__).parent / "events.db"
BASE_POLL_INTERVAL = 2 # Check frequently for debounce readiness
DEBOUNCE_WINDOW = 30 # Seconds

async def process_pipeline(ctx: ToolContext, event: dict, node_id: str, coder: LLMCoder, router_cache: RouterCache, search_engine: RepoSearch) -> bool:
    """Explicitly process a single 'Ready' event."""
    file_key = event["file_key"]
    file_name = event["file_name"]
    event_id = event["id"]
    
    comp_name = file_name.replace(" ", "").replace("-", "")
    logger.info(f"   🚀 Starting Pipeline for {comp_name} ({node_id})...")

    try:
        # 1. Fetch design pattern from Figma (Vision Ready)
        pattern_result = await figma.fetch_figma_pattern(ctx, {"file_key": file_key, "node_ids": [node_id] if ":" in node_id else [], "depth": 2})
        
        if not pattern_result.get("nodes"):
            logger.warning(f"   ⚠️ No nodes found for {file_key}, skipping.")
            return True # Treat as handled

        main_node = pattern_result["nodes"][0]

        # 2. Router Cache / Decision
        # OPTIMIZATION: Check for smart cache hit (Timestamp)
        file_last_mod = pattern_result.get("last_modified")
        cached_entry = router_cache.get_entry(node_id)
        
        computed_file_path = None
        
        if cached_entry and cached_entry.get("last_modified") == file_last_mod:
             logger.info(f"   ⚡ Smart Cache Hit: {node_id} hasn't changed. Skipping generation.")
             return True
             
        if cached_entry:
             # Path is known, but timestamp changed - skip routing, proceed to gen
             computed_file_path = cached_entry.get("path")
             logger.info(f"   ⚡ Route Cache Hit: {computed_file_path}")
        else:
            # Cache Miss - Ask Gemini (with VISION)
            logger.info(f"   🧠 CACHE MISS: Routing '{file_name}' via Gemini...")

            # 1. Fetch Image for Vision
            try:
                # We need to await this
                image_path = await figma.download_node_image_to_temp(ctx, file_key, main_node["id"])
                if image_path:
                    logger.info(f"   👁️ Downloaded vision test image: {image_path}")
            except Exception as e:
                logger.warning(f"   ⚠️ Failed to fetch vision image: {e}")

            # 2. Vector Search (RAG) for candidates
            # OPTIMIZATION: Reduced limit from 15 to 5 to save tokens
            logger.info(f"   🔍 Vector Search querying: '{file_name}'")
            relevant_files = search_engine.search(query=file_name, limit=5)
            logger.info(f"   🔍 Found {len(relevant_files)} candidates: {relevant_files}")
            
            # Format for LLM (just a list of paths)
            repo_file_structure = "\n".join(relevant_files)

            # 3. Ask Gemini
            # OPTIMIZATION: Use cleaned node for routing too
            cleaned_node = figma.clean_node_data(main_node)
            figma_text_content = json.dumps(cleaned_node)[:500]
            
            computed_file_path = coder.find_matching_file(
                figma_name=file_name,
                figma_text_content=figma_text_content,
                repo_file_list=repo_file_structure,
                image_path=image_path
            )
            
            # Save to Cache (Path Only initially, we update timestamp after success?)
            # Actually we save it now to remember the route
            router_cache.set(node_id, computed_file_path, last_modified=file_last_mod)

        # 4. Generate React component code (LLM POWERED)
        project_context = get_project_context()
        
        try:
            # OPTIMIZATION: Clean Data before Generation
            cleaned_node = figma.clean_node_data(main_node)
            
            llm_result = coder.generate_component(
                figma_data=cleaned_node, 
                context_files=project_context,
                image_path=image_path
            )
        except ValueError as e:
            if "GEMINI_API_KEY" in str(e):
                logger.error("   ❌ GEMINI_API_KEY missing.")
                return False
            raise e
        finally:
            # Cleanup Temp Image
            if image_path and os.path.exists(image_path):
                try: os.remove(image_path) 
                except: pass
        
        code = llm_result["code"]
        
        # 5. Validation Loop (Self-Healing)
        # Use local temp file for context
        ext = ".tsx" if "tsx" in file_name.lower() else ".jsx"
        temp_file = f"temp_gen_{comp_name}{ext}"
        validation_passed = False
        
        try:
            # Retry Loop
            for attempt in range(2): 
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(code)
                
                logger.info(f"   🛡️ Running Compiler Check (Attempt {attempt+1})...")
                is_valid, error_msg = validate_code(temp_file)
                
                if is_valid:
                    logger.info("   ✅ Compiler Check Passed.")
                    validation_passed = True
                    break
                else:
                    logger.warning(f"   ❌ Compiler Error: {error_msg[:200]}...")
                    # AI Fix
                    if attempt < 1: 
                        logger.info("   💊 Attempting AI Fix...")
                        code = coder.fix_code(code, error_msg)
                    else:
                        logger.error("   💀 Auto-fix failed twice.")

            # CLEANUP
            if os.path.exists(temp_file): os.remove(temp_file)

            # 6. ABORT IF INVALID
            if not validation_passed:
                logger.error(f"   🛑 Aborting PR. Code failed validation.")
                return False # Stop here. Do not create PR.

            # Prettier (Formatting) - Only runs if valid
            # We need to write it back temporarily for Prettier or pipe it?
            # Actually, we validated 'temp_file'. If we deleted it, we need to re-write or use a pipe.
            # But wait, create_figma_update_pr takes 'code' string.
            # So we just need to run Prettier on the code string or file.
            # Let's perform Prettier on a temp file again or pipe.
            
            # Re-write for Prettier (since we cleaned up)
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(code)
                
            import subprocess
            subprocess.run(["npx", "prettier", "--write", temp_file], capture_output=True, shell=True)
            
            # Read back final code
            if os.path.exists(temp_file):
                with open(temp_file, "r", encoding="utf-8") as f:
                    code = f.read()
                os.remove(temp_file)
                
        except Exception as e:
            logger.warning(f"   ⚠️ Validation step failed: {e}")
            if os.path.exists(temp_file): os.remove(temp_file)
            return False

        # 7. Create GitHub PR
        logger.info(f"   📦 Initiating GitHub PR update...")
        loop = asyncio.get_running_loop()
        pr_url = await loop.run_in_executor(
            None, 
            create_figma_update_pr, 
            computed_file_path, 
            code, 
            file_name, 
            file_key
        )
        
        if pr_url:
            logger.info(f"   ✅ Success! PR: {pr_url}")
            # OPTIMIZATION: Update Cache with Timestamp on Success
            router_cache.set(node_id, computed_file_path, last_modified=file_last_mod)
            return True
        else:
            logger.error(f"   ❌ Failed to create PR")
            return False

    except Exception as e:
        logger.error(f"   💥 Pipeline processing error: {e}")
        return False


async def process_tick(ctx: ToolContext, pending_jobs: dict, search_engine: RepoSearch) -> bool:
    """
    One tick of the worker loop.
    1. Fetch new events -> Queue (Supersede)
    2. Check Queue -> Ready?
    3. Process Ready
    """
    if not DB_PATH.exists():
        return True

    # --- STEP 1: FILL THE QUEUE ---
    try:
        # Fetch pending events from DB
        events_result = await figma.list_pending_events(ctx, {"limit": 50})
        raw_events = events_result.get("events", [])
        
        # Smart Debouncing: Filter redundant events before queuing
        new_events = await figma.coalesce_events(ctx, raw_events)
        
        for event in new_events:
            # Prefer Node ID for granularity, fallback to File Key (safe superseded)
            node_id = event.get("node_id") or event["file_key"]
            file_name = event["file_name"]
            
            # SUPERSEDE LOGIC:
            # If we already have a pending job for this Node ID, we overwrite it.
            # This resets the timer and updates the data payload to the freshest version.
            if node_id in pending_jobs:
                 logger.info(f"♻️  Superseding previous event for {file_name} ({node_id})")
            else:
                 logger.info(f"📥 Queuing new event for {file_name} ({node_id})")

            pending_jobs[node_id] = {
                "data": event,
                "timestamp": time.time() # Start/Reset Timer
            }
            
            # Mark as 'processing' so we don't fetch it again
            await figma.mark_event_processed(ctx, {"event_id": event["id"], "status": "processing"})
            
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        return False

    # --- STEP 2: CHECK THE CLOCK ---
    current_time = time.time()
    ready_to_process = []
    
    # Check debouncers
    for node_id, job in pending_jobs.items():
        elapsed = current_time - job["timestamp"]
        if elapsed > DEBOUNCE_WINDOW:
            ready_to_process.append(node_id)

    # --- STEP 3: EXECUTE PIPELINE ---
    if ready_to_process:
        # Initialize reusable services
        coder = LLMCoder()
        router_cache = RouterCache()

        for node_id in ready_to_process:
            job = pending_jobs.pop(node_id)
            event = job["data"]
            file_name = event["file_name"]
            
            logger.info(f"⏰ Debounce settled ({DEBOUNCE_WINDOW}s). Processing {file_name}...")
            
            success = await process_pipeline(ctx, event, node_id, coder, router_cache, search_engine)
            
            if success:
                # Mark as fully processed (completed)
                await figma.mark_event_processed(ctx, {"event_id": event["id"], "status": "processed"})
            else:
                # Failed. Logic?
                # For now, mark as 'failed' or leave as processing? 
                # Let's mark as processed (failed) to avoid blockage, or add error status.
                # User's logic didn't specify error handling detail, defaulting to 'processed' to clear queue.
                logger.warning(f"Marking failed event {event['id']} as processed to clear queue.")
                await figma.mark_event_processed(ctx, {"event_id": event["id"], "status": "processed"})

    return True

async def main():
    logger.info("🤖 Figma-to-GitHub Automation Worker Started (Daemon Mode)")
    logger.info(f"   Debounce Window: {DEBOUNCE_WINDOW}s")
    
    # Initialize Context
    ctx = ToolContext(
        config=None, security=None, audit=None, 
        search_config=None, approval_secret="automation-secret"
    )
    
    # Initialize Search Engine
    search_engine = RepoSearch()
    # Index the repo (Non-blocking ideally, but blocking is safer for startup)
    search_engine.index_repo(root_dir=".") # Index root dir for this demo bundle context
    
    logger.info("📚 Repo Search Engine Online.")

    # THE WAITING ROOM (Debounce Queue)
    # Format: { "node_id": { "data": dict, "timestamp": float } }
    pending_jobs = {}
    
    backoff = 2
    
    while True:
        try:
            success = await process_tick(ctx, pending_jobs, search_engine)
            
            if success:
                backoff = 2
                # If queue is empty, sleep standard poll
                if not pending_jobs:
                    await asyncio.sleep(BASE_POLL_INTERVAL)
                else:
                    # If jobs in queue, sleep short to check timers
                    await asyncio.sleep(1)
            else:
                logger.warning(f"Tick error. Backing off {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.critical(f"Critical Worker Loop Error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
