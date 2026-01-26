"""
Figma Webhook Receiver
Receives POST requests from Figma webhooks, verifies signatures, and stores events in SQLite.
Uses aiosqlite for non-blocking I/O.
"""
# OS module system ke functions use krne ke liye (jaise environments variables get krna)
import os
# Logging module errors aur info messages record krne ke liye
import logging
# HMAC cryptographic signatures banane ke liye (security ke liye)
import hmac
# Hashlib hashing algorithms (SHA256) ke liye
import hashlib
# JSON data ko parse karne aur string banane ke liye
import json
# AsyncIO asynchronous programming ke liye (taake code block na ho)
import asyncio
# AIOSQLite database ke sath asynchronously kaam krne ke liye
import aiosqlite
# Datetime module time aur dates handle krne ke liye
from datetime import datetime, timezone
# Pathlib file paths ko easily handle krne ke liye
from pathlib import Path
# Typing hints code ko more readable banane ke liye
from typing import Dict, Any

# FastAPI framework web server banane ke liye
from fastapi import FastAPI, Request, HTTPException, Header
# JSONResponse custom JSON responses return krne ke liye
from fastapi.responses import JSONResponse
# Dotenv environment variables load krne ke liye (.env file se)
from dotenv import load_dotenv

# Database file ka path set kr rha ha (current file ke parent folder me events.db)
DB_PATH = Path(__file__).parent / "events.db"
# .env file se saari settings load kr rha ha
load_dotenv(Path(__file__).parent / ".env")

# Logging configuration set kr rha ha (time, name, level, message format)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
# Logger object bana rha ha "figma-webhook" naam se
logger = logging.getLogger("figma-webhook")

# FastAPI app create kr rha ha "Figma Webhook Receiver" naam se
app = FastAPI(title="Figma Webhook Receiver")

def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify Figma webhook signature using HMAC-SHA256."""
    # Environment variable se passcode le rha ha
    passcode = os.getenv("FIGMA_WEBHOOK_PASSCODE")
    # Agar passcode nahi mila to error raise kr rha ha
    if not passcode:
        raise ValueError("FIGMA_WEBHOOK_PASSCODE not set in environment")
    
    # Expected signature calculate kr rha ha HMAC-SHA256 algorithm use krke
    expected_signature = hmac.new(
        passcode.encode(), # Passcode ko bytes me convert kr rha ha
        payload,           # Original payload data
        hashlib.sha256     # SHA256 hashing algorithm use kr rha ha
    ).hexdigest()          # Hexadecimal string return kr rha ha
    
    # Calculate kiya hua signature aur receive kiya hua signature compare kr rha ha
    return hmac.compare_digest(signature, expected_signature)

    """
    SUMMARY (Roman Urdu):
    Is function ka maqsad ye check karna ha ke jo data Figma se aya ha wo asli ha ya kisi hacker ne bheja ha.
    Ye function aapke secret passcode aur payload ko mila kar ek signature banata ha aur usay Figma ke signature se match karta ha.
    Agar match ho jaye to return True (Valid), warna False (Invalid).
    """

async def save_event(event: Dict[str, Any]) -> int:
    """Save webhook event to database asynchronously."""
    # Database connection open kr rha ha asynchronously
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            # Webhook ID nikal rha ha, agar nahi ha to "unknown" use kr rha ha
            webhook_id = event.get("webhook_id", "unknown")
            # Timestamp nikal rha ha, agar nahi ha to current time use kr rha ha
            timestamp = event.get("timestamp", datetime.now(timezone.utc).isoformat())
            # Ek unique ID bana rha ha webhook_id aur timestamp ko mila kar
            unique_event_id = f"{webhook_id}_{timestamp}"
            
            # SQL query chala rha ha data insert krne ke liye
            await db.execute("""
                INSERT INTO events (event_id, event_type, file_key, file_name, node_id, timestamp, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                unique_event_id,                     # Unique ID
                event.get("event_type", "FILE_UPDATE"), # Event type (default: FILE_UPDATE)
                event.get("file_key"),               # Figma file key
                event.get("file_name"),              # File ka naam
                event.get("node_id"),                # Node ID (agar ha to)
                timestamp,                           # Time jab event aya
                json.dumps(event)                    # Poora event JSON format me
            ))
            # Changes ko database me pakka (save) kr rha ha
            await db.commit()
            
            # Last inserted ID nikal rha ha taake return kar sake
            cursor = await db.execute("SELECT last_insert_rowid()")
            row = await cursor.fetchone() # Pehli row fetch kr rha ha
            event_id = row[0]             # ID nikal rha ha
            return event_id               # ID wapis bhej rha ha
        except aiosqlite.IntegrityError:
            # Agar event pehle se exist krta ha (duplicate) to error handle kr rha ha
            # -1 return kr raha ha ye batane ke liye ke duplicate ha
            return -1

    """
    SUMMARY (Roman Urdu):
    Ye function Figma se aane walay event ko database me save karta ha.
    Sab se pehle ye ek unique ID banata ha, phir SQL query chala kar data insert karta ha.
    Agar same event dobara aa jaye (Duplicate), to ye error nahi deta balkay -1 return kar deta ha taake pata chal jaye ke ye duplicate ha.
    """

# Webhook endpoint define kr rha ha (POST request handle karega)
@app.post("/figma-webhook")
async def receive_webhook(
    request: Request, # Incoming request object
    x_figma_signature: str = Header(None, alias="X-Figma-Signature") # Signature header se nikal rha ha
):
    """
    Receive Figma webhook events.
    Verifies signature and stores event in database.
    """
    try:
        # Request ki body (raw data) read kr rha ha signature verify krne ke liye
        body = await request.body()
        
        # Agar signature header moujood ha to verify kr rha ha
        if x_figma_signature:
            try:
                # Signature check kr rha ha verify_signature function se
                if not verify_signature(body, x_figma_signature):
                    # Agar signature galat ha, to 401 Unauthorized error bhej rha ha
                    return JSONResponse(status_code=401, content={"error": "Invalid signature"})
            except ValueError as e:
                # Agar configuration me passcode missing ha to error log kr rha ha
                logger.error(f"Configuration error: {e}")
                return JSONResponse(status_code=500, content={"error": "Server configuration error"})

        # JSON data ko parse (convert) kr rha ha Python dictionary me
        try:
            event = json.loads(body)
        except json.JSONDecodeError:
            # Agar JSON invalid ha to 400 Bad Request bhej rha ha
            return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
        
        # File key aur Event type log krne ke liye nikal rha ha
        file_key = event.get("file_key")
        event_type = event.get("event_type")
        logger.info(f"Received {event_type} for file {file_key}")

        # Check kr rha ha ke kya ye event hamari allowed file ke liye ha ya nahi
        allowed_file_key = os.getenv("FIGMA_FILE_KEY")
        # Agar allowed file key set ha aur match nahi ho rahi, to ignore kr rha ha
        if allowed_file_key and file_key and file_key != allowed_file_key:
            logger.info(f"Ignoring event for file {file_key} (not matching {allowed_file_key})")
            return JSONResponse(
                status_code=200,
                content={"status": "ignored", "message": "File not in scope"}
            )

        # ============================================================
        # HANDLE FILE_COMMENT - Targeted Sync via !sync command
        # ============================================================
        # Agar event type comment ha, to check kr rha ha ke kya user ne command di ha
        if event_type == "FILE_COMMENT":
            # Comments list nikal rha ha
            comments = event.get("comment", [])
            comment_text = ""
            # Agar comments hain to pehle comment ka text le rha ha
            if comments and len(comments) > 0:
                comment_text = comments[0].get("text", "")
            
            # Check kr rha ha ke kya comment me "!sync" ya "!generate" likha ha
            if "!sync" in comment_text.lower() or "!generate" in comment_text.lower():
                # Node ID nikal rha ha jahan comment kiya gaya ha
                # parent_id ya order_id use kr rha ha Figma version ke hisab se
                node_id = event.get("parent_id") or event.get("order_id")
                # User ka naam nikal rha ha jisne comment kiya
                trigger_user = event.get("triggered_by", {}).get("handle", "Unknown")
                
                # Log kr rha ha ke command receive ho gayi ha
                logger.info(f"🎯 COMMAND RECEIVED: '{comment_text}' on Node {node_id} by {trigger_user}")
                
                # Event data ko update kr rha ha worker ke liye
                event["node_id"] = node_id        # Node ID save kr rha ha
                event["trigger_user"] = trigger_user # User save kr rha ha
                event["event_type"] = "TARGETED_SYNC"  # Event type change kr rha ha taake worker isay pehchan le
                
                # Database me save krne ki koshish kr rha ha
                try:
                    event_id = await save_event(event) # save_event call kr rha ha
                except Exception as e:
                    # Agar save krne me error aye to log kr rha ha aur error response bhej rha ha
                    logger.error(f"Database error: {e}")
                    return JSONResponse(status_code=200, content={"status": "error", "message": str(e)})
                
                # Agar duplicate event ha (-1 return hua), to duplicate status bhej rha ha
                if event_id == -1:
                    return JSONResponse(status_code=200, content={"status": "duplicate"})
                
                # Agar sab sahi ha, to Success response bhej rha ha
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success",
                        "event_id": event_id,
                        "message": f"Sync queued for node {node_id}",
                        "command": comment_text
                    }
                )
            else:
                # Agar command nahi ha (normal comment), to ignore kr rha ha
                logger.info(f"💬 Ignoring regular comment: {comment_text[:50]}...")
                return JSONResponse(status_code=200, content={"status": "ignored", "message": "No command found"})

        if event_type == "FILE_UPDATE":
            # Save to database
            try:
                event_id = await save_event(event)
                logger.info(f"✅ FILE_UPDATE saved! ID: {event_id}")
            except Exception as e:
                logger.error(f"Database error: {e}")
                return JSONResponse(
                    status_code=200, 
                    content={"status": "error", "message": "Database write failed", "details": str(e)}
                )
            
            if event_id == -1:
                return JSONResponse(
                    status_code=200,
                    content={"status": "duplicate", "message": "Event already processed"}
                )
            
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "event_id": event_id,
                    "file_key": file_key,
                    "event_type": event_type
                }
            )
    except Exception as e:
        # Global Safety Net - agar koi bhi anjaan error aye to server crash na ho
        logger.error(f"CRITICAL: Webhook processing crash: {e}")
        # Error return kr rha ha lekin status 200 taake Figma webhook disable na kare
        return JSONResponse(
            status_code=200,
            content={
                "status": "error", 
                "error": "Internal Webhook Error", 
                "details": str(e)
            }
        )

    """
    SUMMARY (Roman Urdu):
    Ye sab se main function ha jo Figma se data receive karta ha.
    1. Pehle ye Verify karta ha ke data asli ha.
    2. Phir ye check karta ha ke kya ye wohi file ha jiska hamain intazaar tha.
    3. Agar event 'FILE_COMMENT' ha aur usme '!sync' likha ha, to ye usay process ke liye Database me save kr leta ha.
    4. Agar koi aur event ha ya simple comment ha, to ye usay ignore kr deta ha.
    Maqsad sirf '!sync' commands ko pakarna aur aagay worker ko dena ha.
    """

# Health check endpoint define kr rha ha (GET request)
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Simple JSON return kr rha ha ye batane ke liye ke server zinda ha
    return {"status": "healthy", "service": "figma-webhook-receiver", "mode": "async"}

    """
    SUMMARY (Roman Urdu):
    Ye bs ek simple check ha taake aap dekh saken ke server chal raha ha ya nahi.
    Agar aap browser me '/health' open karein aur ye response mile, to iska matlab server OK ha.
    """

# Events list dekhne ke liye endpoint allow kr rha ha
@app.get("/events")
async def list_events(status: str = "pending", limit: int = 10):
    """List recent webhook events (for debugging)."""
    # Database connect kr rha ha
    async with aiosqlite.connect(DB_PATH) as db:
        # SQL query chala rha ha events fetch krne ke liye (status aur limit ke hisab se)
        cursor = await db.execute("""
            SELECT id, event_type, file_key, file_name, timestamp, status, created_at
            FROM events
            WHERE status = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (status, limit))
        
        # Saari rows fetch kr rha ha
        rows = await cursor.fetchall()
        events = []
        # Har row ko dictionary (JSON object) me convert kr rha ha
        for row in rows:
            events.append({
                "id": row[0],
                "event_type": row[1],
                "file_key": row[2],
                "file_name": row[3],
                "timestamp": row[4],
                "status": row[5],
                "created_at": row[6]
            })
        
        # Events ki list return kr rha ha
        return {"events": events, "count": len(events)}

    """
    SUMMARY (Roman Urdu):
    Ye function debugging ke liye ha. Aap isay use krke dekh sakte hain ke Database me kon se events 'pending' hain.
    Matlab: Aap check kar sakte hain ke Figma se data aya aur save hua ya nahi.
    """

# Main entry point - agar ye file direct chalayi jaye
if __name__ == "__main__":
    # Uvicorn server import kr rha ha
    import uvicorn
    # Console me messages print kr rha ha user ko batane ke liye ke server start ho gaya
    print(">> Starting Figma Async Webhook Receiver on http://localhost:8000")
    print(">> Endpoints:")
    print("   POST /figma-webhook - Receive Figma webhooks")
    print("   GET  /events        - List stored events")
    print("   GET  /health        - Health check")
    # Server start kr rha ha port 8000 par
    uvicorn.run(app, host="0.0.0.0", port=8000)

    """
    SUMMARY (Roman Urdu):
    Ye file ka start button ha. Jab aap `python webhook_server.py` likhte hain, to ye code chalta ha.
    Ye Uvicorn web server chalata ha jo poori application ko handle karta ha.
    """
