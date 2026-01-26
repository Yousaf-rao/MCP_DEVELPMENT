import sqlite3
import json
import uuid
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

# --- CONFIGURATION ---
DB_PATH = "events.db"

# Read from .env (with fallback)
REAL_FILE_KEY = os.getenv("FIGMA_FILE_KEY", "9aQwMxaBj287xHu5bovavC")
COMPONENT_NAME = "AutomationTestButton"

def inject_test_event():
    print(f"Injecting test event for: {COMPONENT_NAME}...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Mock Payload mimicking what webhook_server.py would write
    payload = {
        "event_type": "FILE_UPDATE",
        "file_key": REAL_FILE_KEY,
        "file_name": "Test Design System",
        "timestamp": datetime.utcnow().isoformat(),
        "webhook_id": str(uuid.uuid4())
    }
    
    try:
        cursor.execute("""
            INSERT INTO events (
                event_id, event_type, file_key, file_name, 
                timestamp, payload, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (
            payload['webhook_id'], 
            payload['event_type'], 
            payload['file_key'], 
            COMPONENT_NAME, 
            payload['timestamp'], 
            json.dumps(payload)
        ))
        
        conn.commit()
        print(f"Event injected! ID: {payload['webhook_id']}")
        print("The Worker should pick this up in < 30 seconds.")
        
    except Exception as e:
        print(f"Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inject_test_event()
