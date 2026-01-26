import httpx
import asyncio
import os
import json
import time
import uuid
from dotenv import load_dotenv
import hmac
import hashlib

from pathlib import Path
load_dotenv(Path(__file__).parent.parent / ".env")

async def simulate_update():
    print("Simulating Figma Webhook Event")
    
    # Configuration
    ENDPOINT = "http://localhost:8000/figma-webhook"
    PASSCODE = os.getenv("FIGMA_WEBHOOK_PASSCODE")
    FILE_KEY = os.getenv("FIGMA_FILE_KEY", "9aQwMxaBj287xHu5bovavC") 
    
    if not PASSCODE:
        print("Error: FIGMA_WEBHOOK_PASSCODE not found in .env")
        return

    # Payload matching Figma's format
    event_id = str(uuid.uuid4())
    
    payload = {
        "event_id": event_id,
        "file_key": FILE_KEY,
        "file_name": "Automation Project",
        "node_id": "0-1", # Root Node ID
        "passcode": PASSCODE,  # Must match env var
        "timestamp": str(time.time()),   # Current time
        "webhook_id": event_id
    }
    
    body = json.dumps(payload).encode()
    
    # Generate Signature
    signature = hmac.new(
        PASSCODE.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "X-Figma-Signature": signature
    }
    
    print(f"Sending to {ENDPOINT}...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(ENDPOINT, content=body, headers=headers)
            print(f"Response: {resp.status_code}")
            print(resp.json())
            
            if resp.status_code == 200:
                print("\nSuccess! The MCP Server received the event.")
                print("Now check 'list_pending_events' in Claude or the logs.")
        except Exception as e:
            print(f"Connection Error: {e}")
            print("Is 'webhook_server.py' running via 'ngrok http 8000'?")

if __name__ == "__main__":
    asyncio.run(simulate_update())
