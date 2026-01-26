"""
Database initialization for Figma webhook events.
Creates the SQLite database and tables if they don't exist.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "events.db"

def init_db():
    """Initialize the events database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE,
            event_type TEXT NOT NULL,
            file_key TEXT NOT NULL,
            file_name TEXT,
            node_id TEXT,
            timestamp TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            payload TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nonces (
            nonce TEXT PRIMARY KEY,
            timestamp INTEGER NOT NULL,
            expiry INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create index for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_status 
        ON events(status, created_at DESC)
    """)
    
    # Enable Write-Ahead Logging for concurrency (Production Hardening)
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    conn.commit()
    conn.close()
    print(f"[OK] Database initialized with WAL mode at {DB_PATH}")

if __name__ == "__main__":
    init_db()
