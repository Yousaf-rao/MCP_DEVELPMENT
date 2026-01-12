"""
Figma Webhook Receiver
Receives POST requests from Figma webhooks, verifies signatures, and stores events in SQLite.
Uses aiosqlite for non-blocking I/O.
"""
import os
import hmac
import hashlib
import json
import asyncio
import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

DB_PATH = Path(__file__).parent / "events.db"
load_dotenv()

app = FastAPI(title="Figma Webhook Receiver")

def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify Figma webhook signature using HMAC-SHA256."""
    passcode = os.getenv("FIGMA_WEBHOOK_PASSCODE")
    if not passcode:
        raise ValueError("FIGMA_WEBHOOK_PASSCODE not set in environment")
    
    expected_signature = hmac.new(
        passcode.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

async def save_event(event: Dict[str, Any]) -> int:
    """Save webhook event to database asynchronously."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("""
                INSERT INTO webhooks (event_id, event_type, file_key, file_name, timestamp, payload)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event.get("webhook_id", f"evt_{datetime.utcnow().timestamp()}"),
                event.get("event_type", "FILE_UPDATE"),
                event.get("file_key"),
                event.get("file_name"),
                event.get("timestamp", datetime.utcnow().isoformat()),
                json.dumps(event)
            ))
            await db.commit()
            
            # Retrieve last inserted ID
            cursor = await db.execute("SELECT last_insert_rowid()")
            row = await cursor.fetchone()
            event_id = row[0]
            return event_id
        except aiosqlite.IntegrityError:
            # Event already exists (duplicate webhook)
            return -1

@app.post("/figma-webhook")
async def receive_webhook(
    request: Request,
    x_figma_signature: str = Header(None, alias="X-Figma-Signature")
):
    """
    Receive Figma webhook events.
    Verifies signature and stores event in database.
    """
    # Read raw body for signature verification
    body = await request.body()
    
    # Verify signature if provided
    if x_figma_signature:
        if not verify_signature(body, x_figma_signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse JSON payload
    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Save to database
    event_id = await save_event(event)
    
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
            "file_key": event.get("file_key"),
            "event_type": event.get("event_type")
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "figma-webhook-receiver", "mode": "async"}

@app.get("/events")
async def list_events(status: str = "pending", limit: int = 10):
    """List recent webhook events (for debugging)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT id, event_type, file_key, file_name, timestamp, status, created_at
            FROM webhooks
            WHERE status = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (status, limit))
        
        rows = await cursor.fetchall()
        events = []
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
        
        return {"events": events, "count": len(events)}

if __name__ == "__main__":
    import uvicorn
    print(">> Starting Figma Async Webhook Receiver on http://localhost:8000")
    print(">> Endpoints:")
    print("   POST /figma-webhook - Receive Figma webhooks")
    print("   GET  /events        - List stored events")
    print("   GET  /health        - Health check")
    uvicorn.run(app, host="0.0.0.0", port=8000)
