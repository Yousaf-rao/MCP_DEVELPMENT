
import asyncio
import os
import sqlite3
import time
import json
from pathlib import Path
from dotenv import load_dotenv

# Load env to get File Key
load_dotenv(Path(__file__).parent.parent / ".env")

DB_PATH = Path(__file__).parent.parent / "events.db"
FILE_KEY = os.getenv("FIGMA_FILE_KEY")

if not FILE_KEY:
    print("❌ Error: FIGMA_FILE_KEY not found in .env")
    exit()

def inject_event():
    print(f"🚀 Forcing Sync for File: {FILE_KEY}")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create a fake FILE_UPDATE event
    event_id = f"force_sync_{int(time.time())}"
    payload = {
        "event_type": "FILE_UPDATE",
        "file_key": FILE_KEY,
        "file_name": "Forced Sync File",
        "node_id": "0:1",  # Specific Frame from your URL
        "passcode": "internal_force",
        "timestamp": str(time.time()),
        "webhook_id": "manual"
    }
    
    try:
        c.execute("""
            INSERT INTO events (event_id, event_type, file_key, file_name, node_id, timestamp, status, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            "FILE_UPDATE",
            FILE_KEY,
            "Forced Sync File",
            "0:1",  # Save Node ID column
            str(time.time()),
            "pending",
            json.dumps(payload)
        ))
        conn.commit()
        print("✅ Event injected into Database!")
        print("⏳ Worker should pick it up in 2 seconds...")
    except Exception as e:
        print(f"❌ Error injecting event: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inject_event()
