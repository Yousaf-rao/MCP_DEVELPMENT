
import sqlite3
import time
from pathlib import Path
import os
import sys

# Windows console fix
if sys.platform == "win32":
    os.system('cls')
    
DB_PATH = Path(__file__).parent.parent / "events.db"

def monitor():
    print("👀 Watching database for new Figma Events...")
    print(f"Database: {DB_PATH}")
    print("-" * 50)
    
    last_id = 0
    
    while True:
        try:
            if not DB_PATH.exists():
                time.sleep(1)
                continue
                
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Get latest events
            c.execute("SELECT id, event_type, status, created_at FROM events WHERE id > ? ORDER BY id ASC", (last_id,))
            rows = c.fetchall()
            
            for row in rows:
                eid, etype, status, created = row
                last_id = eid
                print(f"[{created}] New Event Received!")
                print(f"   Type:   {etype}")
                print(f"   Status: {status}")
                print("-" * 50)
                
            conn.close()
            time.sleep(2)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    monitor()
