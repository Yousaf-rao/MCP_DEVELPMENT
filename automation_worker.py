import os
<<<<<<< HEAD
import sys
from dotenv import load_dotenv

# 1. LOAD ENV IMMEDIATELY
load_dotenv()

=======
>>>>>>> d06dac19010c3e2f3fff8aa92dad6ccd137cd9b7
import asyncio
import logging
import sqlite3
import json
<<<<<<< HEAD
import time
import random
import subprocess
from pathlib import Path

# Import our modular tools and utils
# Ye humare custom modules hain jo alag files mein pare hain. 
# mcp_core humari main library hai jisme tools aur services defined hain.
from mcp_core.context import ToolContext
from mcp_core.tools import figma
from mcp_core.utils import gitlab_automation as git_service
from mcp_core.services.llm_coder import LLMCoder
from mcp_core.services.repo_search import RepoSearch
from mcp_core.services.router_cache import RouterCache
from mcp_core.utils.validator import validate_code

# Config
# DB_PATH: Ye wo file hai jahan hum events save karte hain taake duplicate kaam na ho.
DB_PATH = Path(__file__).parent / "events.db"
# BASE_POLL_INTERVAL: Worker har 2 second baad check karega ke koi naya kaam hai ya nahi.
BASE_POLL_INTERVAL = 2  # Check frequently for debounce readiness
# DEBOUNCE_WINDOW: Agar Figma mein jaldi jaldi changes ho rahi hain, to hum 30 seconds wait karte hain taake saari changes ek saath process hon.
DEBOUNCE_WINDOW = 30    # Seconds

# Windows Console Fix: Force UTF-8
# Windows mein kabhi kabhi printing mein masla hota hai (encoding issues), ye code usay fix karta hai taake emojis aur special characters sahi nazar ayen.
DEMO_MODE = True
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Setup logging
# Logging set ki ja rahi hai taake hum console mein dekh sakein ke worker kya kar raha hai (INFO level).
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AutomationWorker")


def extract_text_from_figma(node):
    """
    Recursively extracts all text characters from a Figma JSON node.
    
    Is function ka maqsad:
    Figma ke design node se sara text nikalna. 
    Ye 'recursively' kaam karta hai, yani ye function apne aap ko call karta hai taake agar kisi Layer ke andar aur Layers hain (children), 
    to wo unke andar se bhi text nikal le. Ye text humein ye samajhne mein madad deta hai ke ye component kya hai (e.g., agar button pe 'Submit' likha hai).
    """
    text_content = []
    # Agar node type 'TEXT' hai aur usmein 'characters' property hai, to usay list mein daal do.
    if node.get('type') == 'TEXT' and 'characters' in node:
        text_content.append(node['characters'])
    
    # Agar node ke 'children' hain (yani ye Group ya Frame hai), to har child ke liye yehi function dubara call karo.
    if 'children' in node:
        for child in node['children']:
            text_content.extend(extract_text_from_figma(child))
            
    # Saare text pieces ko join kar ke ek string bana kar wapis bhejo.
    return " ".join(text_content)


def find_target_file(figma_node, repo_root, search_tool):
    """
    Determines the file to update using a 3-Layer Strategy.
    
Iska kaam hai ye decide karna ke Figma ke design ko kis file mein convert karna hai.    Ye function bohat critical hai. 
    Hum 3 tareeqon (strats) se file dhoondte hain:
    
    1. Layer 1 (Name Match): 
       Hum check karte hain ke kya Figma layer ka naam (e.g. "User Profile") humare project ki kisi file se milta hai (e.g. "UserProfile.jsx").
       
    2. Layer 2 (Visual/RAG Search): 
       Agar naam se file nahi mili, to hum design ke andar ka text parhte hain aur Project mein search karte hain ke kya koi aisi file hai jisme ye text ho.
       
    3. Layer 3 (Create New): 
       Agar upar dono fail ho jayen, to hum samajhte hain ke ye naya design hai aur ek nayi file create karte hain "FigmaDesign" folder mein.
    """
    raw_name = figma_node['name']
    # Sanitize: Naam mein se spaces aur special characters hataye ja rahe hain taake file name clean ho. "User Profile" -> "UserProfile"
    safe_name = raw_name.replace(" ", "").replace("-", "").replace("_", "")
    
    # 1. GET SEARCH ZONE FROM ENV
    # Hum environment variable se dekhte hain ke humein kis folder mein search karna hai. Default "Frontend/reactjs" hai.
    relative_search_dir = os.getenv("SEARCH_ROOT", "Frontend/reactjs")
    
    # Construct absolute paths
    # Full paths banaye ja rahe hain taake OS unhe samajh sake.
    search_base = os.path.join(repo_root, relative_search_dir)
    default_creation_dir = os.path.join(search_base, "FigmaDesign")
    
    # Ensure directories exist
    # Agar folders nahi hain to unhe bana diya jata hai.
    if not os.path.exists(search_base):
        logger.warning(f"⚠️ Search root '{search_base}' missing. Creating it.")
        os.makedirs(search_base, exist_ok=True)
    if not os.path.exists(default_creation_dir):
        os.makedirs(default_creation_dir, exist_ok=True)

    logger.info(f"📍 SEARCH CONFIG: Looking for '{safe_name}' inside '{relative_search_dir}'")

    # --- LAYER 1: EXACT & SANITIZED NAME MATCH ---
    # Hum expected file names ki list banate hain.
    target_files = {
        f"{safe_name}.jsx", f"{safe_name}.js", f"{safe_name}.tsx",
        f"{raw_name}.jsx"  # Asli naam bhi check karte hain (kabhi kabhi spaces nahi hoten)
    }
    
    # os.walk se hum folder ke andar folder check karte hain.
    for root, dirs, files in os.walk(search_base):
        if "node_modules" in dirs: dirs.remove("node_modules") # node_modules ko ignore karo, wahan humare code nahi hota.
        
        for file in files:
            # A. Strict Match: Bilkul same spelling check.
            if file in target_files:
                found_full_path = os.path.join(root, file)
                rel_path = os.path.relpath(found_full_path, repo_root)
                logger.info(f"✅ FOUND MATCH: {rel_path}")
                return rel_path
            
            # B. Case-Insensitive Match: Choti barri ABC ka farq ignore karo (Windows ke liye acha hai).
            if file.lower() == f"{safe_name.lower()}.jsx":
                found_full_path = os.path.join(root, file)
                rel_path = os.path.relpath(found_full_path, repo_root)
                logger.info(f"✅ FOUND CASE MATCH: {rel_path}")
                return rel_path

    # --- LAYER 2: VISUAL FINGERPRINT (RAG) ---
    # Agar naam se file nahi mili, to ab hum content check karenge.
    figma_text = extract_text_from_figma(figma_node)
    
    # Agar design mein thora sa bhi text hai (min 15 chars), to search tool use karo.
    if len(figma_text) > 15:
        logger.info(f"🕵️‍♂️ Name failed. Running Visual Search on: '{figma_text[:30]}...'")
        results = search_tool.search(query=figma_text, limit=1) # Search engine se pucho ke ye text kahan match hota hai.
        
        if results:
            best_match = results[0]
            # Search result format handle karna (dictionary ya string ho sakta hai).
            if isinstance(best_match, dict):
                matched_path = best_match.get('path') or best_match.get('metadata', {}).get('path')
            else:
                matched_path = best_match
            
            # Verify existence and safety
            if matched_path and isinstance(matched_path, str):
                # Ensure hum handle relative/absolute path logic correctly.
                full_match_path = matched_path if os.path.isabs(matched_path) else os.path.join(repo_root, matched_path)
                
                if os.path.exists(full_match_path):
                    # SECURITY CHECK: Make sure ke file humare search folder ke andar hi hai (Security risk avoid karne ke liye).
                    if os.path.abspath(full_match_path).startswith(os.path.abspath(search_base)):
                        rel_path = os.path.relpath(full_match_path, repo_root)
                        logger.info(f"🧬 VISUAL MATCH FOUND: {rel_path}")
                        return rel_path

    # --- LAYER 3: CREATE NEW (Fallback) ---
    # Agar upar kuch nahi mila, to nayi file banao.
    final_rel_path = os.path.join(relative_search_dir, "FigmaDesign", f"{safe_name}.jsx")
    logger.info(f"✨ Match failed. Creating NEW file: {final_rel_path}")
    return final_rel_path


def get_project_context():
    """
    Reads context files (Tailwind/Styles) to guide the LLM.
    
    Is function ka maqsad hai ke hum AI ko bata sakein ke humara project kaisa dikhta hai.
    Hum 'tailwind.config.js' aur 'index.css' file parh ke AI ko bhejte hain taake wo jo code generate kare,
    wo humare project ki styling ke mutabiq ho (e.g. sahi Colors aur Fonts use kare).
    """
    context = ""
    # Add files you want the LLM to see here
    config_files = ["tailwind.config.js", "tailwind.config.ts", "src/index.css"]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    context += f"// {config_file}\n{f.read()}\n"
            except Exception:
                pass
    return context


def extract_top_level_frames(document_node: dict) -> list:
    """
    Extract all FRAME nodes from the top level of a Figma document.
    Figma structure: Document -> Page(s) -> Frame(s)
    
    Ye function Figma ke complex structure ko simplify karta hai.
    Figma mein structure hota hai: Document > Pages > Frames.
    Hum sirf 'FRAMES' (jo ke screens ya components hote hain) extract karte hain.
    Ye function handle karta hai ke agar humein pura document mila hai, ya sirf page, ya direct frame,
    har case mein humein Frames ki list wapis mile.
    """
    frames = []
    
    # Case 1: Agar humein pura Document mila hai
    if document_node.get("type") == "DOCUMENT":
        for page in document_node.get("children", []):
            if page.get("type") == "CANVAS":  # Pages ko 'CANVAS' kehte hain
                for child in page.get("children", []):
                    if child.get("type") == "FRAME":
                        frames.append(child)
    # Case 2: Agar humein Page/Canvas mila hai
    elif document_node.get("type") == "CANVAS":
        for child in document_node.get("children", []):
            if child.get("type") == "FRAME":
                frames.append(child)
    # Case 3: Agar humein pehle hi ek Frame mila hai
    elif document_node.get("type") == "FRAME":
        frames.append(document_node)
    
    logger.info(f"📋 Found {len(frames)} top-level frames: {[f.get('name') for f in frames]}")
    return frames

async def process_pipeline(ctx: ToolContext, event: dict, node_id: str, coder: LLMCoder, router_cache: RouterCache, search_engine: RepoSearch, project_root: str) -> bool:
    """
    Explicitly process a single 'Ready' event. Handles multi-frame files.
    
    Ye main controller function hai jo har event ko process karta hai.
    1. Ye Figma se data fetch karta hai.
    2. Ye check karta hai ke kya multiple frames process karne hain ya single.
    3. Phir ye `process_single_frame` ko call karta hai asal kaam karne ke liye.
    """
    file_key = event["file_key"]
    file_name = event["file_name"]
    
    logger.info(f"🚀 Starting Pipeline for {file_name} ({node_id})...")

    try:
        # 1. Fetch design pattern from Figma
        # Figma API se design ka data mangwao.
        has_specific_node = ":" in node_id
        pattern_result = await figma.fetch_figma_pattern(ctx, {"file_key": file_key, "node_ids": [node_id] if has_specific_node else [], "depth": 5})
        
        if not pattern_result.get("nodes"):
            logger.warning(f"⚠️ No nodes found for {file_key}, skipping.")
            return True 
        
        root_node = pattern_result["nodes"][0]
        
        # 2. MULTI-FRAME HANDLING: If we got the Document root, extract all frames
        # Agar humein koi specific node nahi di gayi, to hum samajhte hain ke shayed puri file process karni hai.
        # Is soorat mein hum saare Frames nikalte hain.
        if not has_specific_node and root_node.get("type") in ["DOCUMENT", "CANVAS"]:
            frames = extract_top_level_frames(root_node)
            if not frames:
                logger.warning(f"⚠️ No FRAME nodes found in {file_name}, skipping.")
                return True
            
            # Process each frame
            # Har frame ke liye alag process chalao.
            all_success = True
            for frame in frames:
                frame_name = frame.get("name", "Unknown")
                logger.info(f"🎯 Processing frame: {frame_name}")
                success = await process_single_frame(ctx, event, frame, coder, router_cache, search_engine, project_root)
                if not success:
                    all_success = False
            return all_success
        else:
            # Single frame mode (specific node_id provided)
            # Agar specific node ID thi, to bas usi ek ko process karo.
            return await process_single_frame(ctx, event, root_node, coder, router_cache, search_engine, project_root)
            
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return True  # Mark as processed to avoid requeue (taake worker stuck na ho)


async def process_single_frame(ctx: ToolContext, event: dict, frame_node: dict, coder: LLMCoder, router_cache: RouterCache, search_engine: RepoSearch, project_root: str) -> bool:
    """
    Process a single frame node.
    
    Ye sab se important function hai. Iska workflow ye hai:
    1.  Target File Dhoondo: `find_target_file` se pata karo code kahan likhna hai.
    2.  Vision Image Lo: Figma se image download karo taake AI dekh sake design kaisa hai.
    3.  RAG Context: Project mein milti julti files dhoondo taake AI unka style copy kar sake.
    4.  Generate Code: LLM ko data bhejo aur Code generate karwao.
    5.  Validate & Fix: Code ko check karo (syntax check), agar ghalati ho to AI se fix karwao.
    6.  Prettier: Code ko format karo taake sunda dikhe.
    7.  Create MR: GitLab par Merge Request banao.
    """
    file_key = event["file_key"]
    file_name = event["file_name"]  # Needed for MR creation
    comp_name = frame_node.get("name", "Component").replace(" ", "").replace("-", "")
    
    try:
        # 2. RESOLVE FILE PATH (Hunter Logic)
        # file kahan banani/update karni hai?
        computed_file_path = find_target_file(frame_node, project_root, search_engine)

        # 3. Vision Context
        # Design ki image mangwa rahe hain.
        image_path = None
        try:
            image_path = await figma.download_node_image_to_temp(ctx, file_key, frame_node["id"])
            if image_path:
                logger.info(f"👁️ Vision image captured: {image_path}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch vision image: {e}")

        # 4. Generate Code
        # Project ka context (tailwind config, etc) load karo.
        project_context = get_project_context()

        # --- RAG: Fetch Similar Examples ---
        # RAG ka matlab hai 'Retrieval Augmented Generation'. Hum AI ko purana code dikhate hain.
        rag_context = ""
        try:
            design_text = extract_text_from_figma(frame_node)
            if len(design_text) > 20: # Agar design mein kafi text hai tabhi search karo.
                logger.info(f"🔍 RAG: Searching for components similar to '{comp_name}'...")
                similar_files = search_engine.search(query=design_text, limit=3)
                
                if similar_files:
                    logger.info(f"    Found {len(similar_files)} matches: {similar_files}")
                    rag_context = "\n### SIMILAR CODEBASE EXAMPLES (REFERENCE ONLY):\n"
                    
                    for rel_path in similar_files:
                        full_path = os.path.join(project_root, rel_path)
                        if os.path.exists(full_path):
                            try:
                                with open(full_path, "r", encoding="utf-8") as f:
                                    content = f.read()
                                    # Sirf shuru ke 2000 characters bhejte hain taake context limit cross na ho.
                                    rag_context += f"\n--- START EXAMPLE: {rel_path} ---\n{content[:2000]}\n--- END EXAMPLE ---\n"
                            except Exception:
                                pass
                    logger.info(f"📖 RAG: Injected {len(rag_context)} chars of context.")

        except Exception as e:
            logger.warning(f"⚠️ RAG Search failed (non-critical): {e}")

        try:
            # AI ko sab kuch bhej ke code generate karwao.
            llm_result = coder.generate_component(
                figma_data=frame_node, 
                context_files=project_context,
                rag_context=rag_context,
                image_path=image_path
            )
        except ValueError as e:
            if "GEMINI_API_KEY" in str(e):
                logger.error("❌ GEMINI_API_KEY missing.")
                return False
            raise e
        finally:
            # Image ab delete kardo, kaam khatam.
            if image_path and os.path.exists(image_path):
                try: os.remove(image_path) 
                except: pass
        
        code = llm_result["code"]
        
        # 5. Validation & Self-Healing Loop
        # Ab hum code ko check karenge.
        ext = ".jsx" 
        temp_filename = f"temp_gen_{comp_name}{ext}"
        temp_file = os.path.join(project_root, temp_filename)
        
        validation_passed = False
        
        try:
            # Hum 2 attempts (koshish) karte hain. Agar pehli baar error aya, to hum AI ko bolte hain fix kare.
            for attempt in range(2): 
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(code)
                
                logger.info(f"🛡️ Running Compiler Check (Attempt {attempt+1})...")
                # Ye function check karta hai ke syntax error to nahi.
                is_valid, error_msg = validate_code(temp_file, cwd=project_root)
                
                if is_valid:
                    logger.info("✅ Compiler Check Passed.")
                    validation_passed = True
                    break
                else:
                    logger.warning(f"❌ Compiler Error: {error_msg[:200]}...")
                    if attempt < 1: 
                        logger.info("💊 Attempting AI Fix...")
                        # Coder se kaho ke error fix kare.
                        code = coder.fix_code(code, error_msg)
                    else:
                        logger.error("💀 Auto-fix failed twice.")

            # Cleanup temp file
            if os.path.exists(temp_file): os.remove(temp_file)

            # Agar fix nahi hua to process rok do.
            if not validation_passed:
                logger.error(f"🛑 Aborting PR. Code failed validation.")
                return False

            # 6. Prettier Formatting
            # Code ko standardize karo (indentation, spacing etc).
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(code)
                
            try:
                logger.info("🎨 Running Prettier formatting...")
                result = subprocess.run(
                    ["npx", "prettier", "--write", temp_file], 
                    capture_output=True, 
                    shell=True, 
                    cwd=project_root,
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info("✅ Prettier formatting complete")
            except Exception as e:
                logger.warning(f"⚠️ Prettier skipped: {e}")
            
            # Read back formatted code
            if os.path.exists(temp_file):
                with open(temp_file, "r", encoding="utf-8") as f:
                    code = f.read()
                os.remove(temp_file)
                
        except Exception as e:
            logger.warning(f"⚠️ Validation step failed: {e}")
        # 7. Create/Update GitLab Merge Request OR Direct Write (Demo)
        if DEMO_MODE:
            logger.info(f"🔥 DEMO MODE: Writing file directly to {computed_file_path}")
            final_path = os.path.join(project_root, computed_file_path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            
            # Write final code
            with open(final_path, "w", encoding="utf-8") as f:
                f.write(code)
                
            logger.info(f"✅ Success! File updated locally.")
            return True
            
        else:
            # Sab theek hai to GitLab pe bhej do.
            logger.info(f"📦 Creating MR for: {computed_file_path}")
            
            mr_url = git_service.create_merge_request(
                file_path=computed_file_path,
                content=code,
                file_name=file_name,
                figma_file_key=file_key,
                repo_path=project_root
            )
            
            if mr_url:
                logger.info(f"✅ Success! MR: {mr_url}")
                return True
            else:
                logger.error("❌ Failed to create Merge Request.")
                return False

    except Exception as e:
        logger.error(f"💥 Pipeline processing error: {e}")
        return False


async def process_tick(ctx: ToolContext, pending_jobs: dict, search_engine: RepoSearch, project_root: str) -> bool:
    """
    Worker Tick: Fetches events, manages queue, triggers pipeline.
    
    Ye loop ka ek chakkar (tick) hai. Har baar jab ye chalta hai, ye ye karta hai:
    1. Pending Events Check: Figma plugin se puchta hai "koi updates hain?".
    2. Queue Update: Naye events ko list mein dalta hai.
    3. Debounce Check: Dekhta hai ke kya "DEBOUNCE_WINDOW" (30 sec) guzar gaye?
       (Taake agar designer abhi kaam kar raha ho to hum foran code generate na karein, thora wait karein).
    4. Execute: Agar time pura ho gaya hai, to `process_pipeline` chalao.
    """
    if not DB_PATH.exists():
        return True

    # --- STEP 1: FILL THE QUEUE ---
    try:
        events_result = await figma.list_pending_events(ctx, {"limit": 50})
        new_events = events_result.get("events", [])
        
        for event in new_events:
            node_id = event.get("node_id") or event["file_key"]
            file_name = event["file_name"]
            
            # Agar event pehle hi queue mein hai, to usay update (supersede) kardo.
            if node_id in pending_jobs:
                 logger.info(f"♻️  Superseding previous event for {file_name} ({node_id})")
            else:
                 logger.info(f"📥 Queuing new event for {file_name} ({node_id})")

            pending_jobs[node_id] = {
                "data": event,
                "timestamp": time.time()
            }
            # Figma ko bata do ke humne ye note kar liya hai (status: processing).
            await figma.mark_event_processed(ctx, {"event_id": event["id"], "status": "processing"})
            
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        return False

    # --- STEP 2: CHECK DEBOUNCE TIMERS ---
    # Check karo kon se jobs ready hain.
    current_time = time.time()
    ready_to_process = []
    
    for node_id, job in pending_jobs.items():
        elapsed = current_time - job["timestamp"]
        # Agar 30 seconds (DEBOUNCE_WINDOW) se zada waqt guzar gaya, to process karo.
        # if elapsed > DEBOUNCE_WINDOW:
        ready_to_process.append(node_id)

    # --- STEP 3: EXECUTE PIPELINE ---
    if ready_to_process:
        coder = LLMCoder()
        router_cache = RouterCache()

        for node_id in ready_to_process:
            job = pending_jobs.pop(node_id)
            event = job["data"]
            file_name = event["file_name"]
            
            logger.info(f"⏰ Debounce settled. Processing {file_name}...")
            
            # Asal pipeline chalao.
            success = await process_pipeline(ctx, event, node_id, coder, router_cache, search_engine, project_root)
            
            # Mark processed (chahye fail ho ya pass, humne try kar liya).
            await figma.mark_event_processed(ctx, {"event_id": event["id"], "status": "processed"})

    return True


async def main():
    logger.info("🤖 Figma-to-GitLab Automation Worker Started (Daemon Mode)")

    # Tools initialize karo (Security, Search, etc)
    ctx = ToolContext(config=None, security=None, audit=None, search_config=None, approval_secret="automation-secret")
    search_engine = RepoSearch()
    
    # --- DEMO MODE: DIRECT LOCAL WRITE ---
    # Hum GitLab ki bajaye seedha code yahan save karenge taake user foran result dekh sake.
    DEMO_MODE = True
    
    if DEMO_MODE:
        logger.info("🔥 DEMO MODE ENABLED: Writing directly to local filesystem")
        # Use the actual Frontend folder, not a temp workspace
        project_root = str(Path(__file__).parent) 
        # Skip Git Sync
        logger.info(f"📂 Project Root set to: {project_root}")
    else:
        # Standard Production Mode
        if not repo_url:
            logger.critical("❌ GITLAB_REPO_URL is missing in .env! Exiting.")
            return

        # Workspace Setup
        project_root = "./temp_workspace"
        if sub_dir:
            project_root = os.path.join(project_root, sub_dir)

        logger.info(f"🌍 Connecting to Remote: {repo_url}")
        try:
            search_engine.sync_from_remote(repo_url, repo_branch)
            search_engine.index_repo(sub_dir=sub_dir)
        except Exception as e:
            logger.critical(f"❌ Failed to initialize repo: {e}")
            return
            
    logger.info("📚 Repo Search Engine Online.")

    pending_jobs = {}
    backoff = 2
    
    # Main Loop (Infinite Loop)
    logger.info("⚡ Polling Mode Activated: Checking Figma every 10 seconds...")
    last_version = None
    
    while True:
        try:
            # 1. Process Pending Jobs from Webhook
            success = await process_tick(ctx, pending_jobs, search_engine, project_root)
            
            # 2. AUTO-POLL: Check if Figma file version changed
            if DEMO_MODE:
                try:
                    current_file_key = os.getenv("FIGMA_FILE_KEY")
                    if current_file_key:
                        # Get File Version
                        file_meta = await figma.get_file_meta(ctx, current_file_key)
                        current_version = file_meta.get("version") or file_meta.get("lastModified")
                        
                        logger.info(f"🔍 Checking Figma... [Current: {current_version} | Last: {last_version}]")
                        
                        # Trigger if changed OR if this is the first check (so we get the design immediately)
                        if last_version is None or current_version != last_version:
                            if last_version is None:
                                logger.info(f"🚀 Initial Sync: Fetching latest design (v{current_version})...")
                            else:
                                logger.info(f"🔄 Detected Change in Figma! (v{current_version})")
                            
                            # Inject artificial event
                            fake_event = {
                                "id": f"poll_{int(time.time())}_{random.randint(1000, 9999)}",
                                "event_type": "FILE_UPDATE",
                                "file_key": current_file_key,
                                "file_name": file_meta.get("name", "PolledFile"),
                                "node_id": "0:1", # Default to first frame
                                "timestamp": str(time.time())
                            }
                            pending_jobs[fake_event["id"]] = {"data": fake_event, "timestamp": time.time()}
                            
                        last_version = current_version
                except Exception as e:
                    logger.warning(f"Poll failed: {e}")

            # Sleep logic
            await asyncio.sleep(5) # 5 seconds wait (Faster Poll)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.critical(f"Critical Worker Loop Error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
=======
from pathlib import Path
from dotenv import load_dotenv

# Import our modular tools and utils
# Import our modular tools and utils
from mcp_core.context import ToolContext
from mcp_core.config import ServerConfig
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
    
    # Initialize proper configuration
    base_dir = Path(__file__).parent.resolve()
    config = ServerConfig(
        allowed_repos=["*"],
        allowed_roots=[
            Path.home() / "Desktop", 
            base_dir,
            base_dir.parent
        ],
        max_file_size=1_000_000
    )
    
    # Initialize a mock context for our tools
    ctx = ToolContext(
        config=config, security=None, audit=None, 
        search_config=None, approval_secret="automation-secret"
    )

    while True:
        await process_pending_events(ctx)
        await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
>>>>>>> d06dac19010c3e2f3fff8aa92dad6ccd137cd9b7
