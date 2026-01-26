
import os
import secrets
import httpx
import asyncio
from dotenv import load_dotenv

# Load environment variables
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / ".env")

async def register_webhook():
    print("Figma Webhook Registration Utility")
    
    # 1. Get/Set Passcode
    passcode = os.getenv("FIGMA_WEBHOOK_PASSCODE")
    if not passcode:
        passcode = secrets.token_hex(32)
        print(f"FIGMA_WEBHOOK_PASSCODE not found in .env")
        print(f"Generated new passcode: {passcode}")
        print("ACTION REQUIRED: Add this to your .env file!")
    else:
        print(f"Using passcode from .env")

    # 2. Get Token
    token = os.getenv("FIGMA_ACCESS_TOKEN")
    if not token:
        print("Error: FIGMA_ACCESS_TOKEN is missing in .env")
        return

    # 3. Get Ngrok URL and Event Type
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="Ngrok Public URL")
    parser.add_argument("--event", help="Event type: FILE_UPDATE or FILE_COMMENT", default="FILE_UPDATE")
    args, _ = parser.parse_known_args()

    if args.url:
        base_url = args.url
    else:
        print("\nEnter your ngrok HTTPS URL (e.g., https://xyz.ngrok-free.app):")
        base_url = input("> ").strip()
    
    if not base_url.startswith("https://"):
        print("Error: URL must start with https://")
        return
        
    endpoint = f"{base_url}/figma-webhook"
    event_type = args.event.upper()
    
    # Validate event type
    valid_events = ["FILE_UPDATE", "FILE_COMMENT", "FILE_VERSION_UPDATE", "FILE_DELETE"]
    if event_type not in valid_events:
        print(f"Error: Invalid event type '{event_type}'. Must be one of: {valid_events}")
        return
    
    # 4. Register
    url = "https://api.figma.com/v2/webhooks"
    headers = {
        "X-Figma-Token": token,
        "Content-Type": "application/json"
    }
    payload = {
        "event_type": event_type,
        "team_id": os.getenv("FIGMA_TEAM_ID", "YOUR_TEAM_ID"),
        "endpoint": endpoint,
        "passcode": passcode,
        "status": "ACTIVE"
    }
    
    # Note: Figma API requires team_id for team webhooks
    if "YOUR_TEAM_ID" in payload["team_id"] or not payload["team_id"]:
        print("\nEnter your Figma Team ID (from team URL):")
        payload["team_id"] = input("> ").strip()

    print(f"Registering webhook for team {payload['team_id']} -> {endpoint}...")
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                print("Webhook Registered Successfully!")
                print(resp.json())
            else:
                print(f"Registration Failed: {resp.status_code}")
                print(resp.text)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(register_webhook())
