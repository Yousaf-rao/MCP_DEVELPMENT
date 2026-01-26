import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "events.db"

def migrate():
    print(f"Migrating database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Rename 'webhooks' -> 'events' if it exists and 'events' does not
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='webhooks'")
    has_webhooks = cursor.fetchone() is not None
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
    has_events = cursor.fetchone() is not None
    
    if has_webhooks and not has_events:
        print("Renaming table 'webhooks' -> 'events'")
        cursor.execute("ALTER TABLE webhooks RENAME TO events")
    elif not has_events and not has_webhooks:
        print("Creating table 'events' (Fresh Setup)")
        cursor.execute("""
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE, 
                event_type TEXT, 
                file_key TEXT, 
                file_name TEXT, 
                timestamp TEXT, 
                payload TEXT, 
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        print("Table 'events' already exists.")
        
    # 2. Add Missing Columns
    # check columns
    cursor.execute("PRAGMA table_info(events)")
    columns = [row[1] for row in cursor.fetchall()]
    
    missing_cols = {
        "started_at": "TEXT",
        "completed_at": "TEXT",
        "pr_url": "TEXT",
        "error_log": "TEXT",
        "node_id": "TEXT"
    }
    
    for col, dtype in missing_cols.items():
        if col not in columns:
            print(f"Adding column '{col}'...")
            cursor.execute(f"ALTER TABLE events ADD COLUMN {col} {dtype}")
            
    conn.commit()
    conn.close()
    print("Migration Complete.")

if __name__ == "__main__":
    migrate()
