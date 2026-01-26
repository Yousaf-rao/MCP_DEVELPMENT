
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def check_health():
    print("🏥 Starting System Health Check...\n")
    
    # Check 1: Environment Variables
    load_dotenv(Path(__file__).parent.parent / ".env")
    required_vars = ["FIGMA_ACCESS_TOKEN", "GEMINI_API_KEY", "FIGMA_FILE_KEY"]
    
    all_ok = True
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ ENV: {var} is set.")
        else:
            print(f"❌ ENV: {var} is MISSING!")
            all_ok = False
            
    # Check 2: Database
    db_path = Path(__file__).parent.parent / "events.db"
    if db_path.exists():
        print(f"✅ DB: Database found at {db_path.name}")
    else:
        print(f"⚠️  DB: Database missing (Will be created on first run)")
        
    # Check 3: Directories
    dirs = ["Frontend/reactjs/src", "mcp_core"]
    for d in dirs:
        path = Path(__file__).parent.parent / d
        if path.exists():
             print(f"✅ DIR: {d} exists.")
        else:
             print(f"❌ DIR: {d} not found!")
             all_ok = False

    print("\n" + "="*30)
    if all_ok:
        print("🚀 SYSTEM HEALTHY - READY TO RUN")
        return 0
    else:
        print("🛑 SYSTEM HAS ISSUES")
        return 1

if __name__ == "__main__":
    sys.exit(check_health())
