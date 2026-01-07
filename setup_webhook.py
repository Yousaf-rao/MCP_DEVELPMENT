
import os
import sys
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_webhook(file_key=None, ngrok_url=None, team_id=None):
    print("--- Figma Webhook Setup ---")
    
    # 1. Get Secrets from .env
    token = os.getenv("FIGMA_ACCESS_TOKEN")
    passcode = os.getenv("FIGMA_WEBHOOK_PASSCODE")
    
    if not token or not passcode:
        print("Error: FIGMA_ACCESS_TOKEN or FIGMA_WEBHOOK_PASSCODE missing in .env")
        return

    # 2. Get Dynamic Inputs
    if not file_key:
        file_key = input("Enter Figma File Key (from URL, e.g. 'AbC123XyZ'): ").strip()
    
    if not ngrok_url:
        ngrok_url = input("Enter your ngrok URL (e.g. https://xxxx.ngrok-free.app): ").strip()

    if not team_id:
        team_id = input("Enter Figma Team ID (optional, press Enter to skip): ").strip()
    
    # Clean URL
    if ngrok_url.endswith("/"):
        ngrok_url = ngrok_url[:-1]
        
    endpoint = f"{ngrok_url}/figma-webhook"
    
    # 3. Send Request
    url = "https://api.figma.com/v2/webhooks"
    headers = {
        "X-Figma-Token": token,
        "Content-Type": "application/json"
    }
    
    payload = {
        "event_type": "FILE_UPDATE",
        "file_key": file_key,
        "endpoint": endpoint,
        "passcode": passcode,
        "description": "MCP Local Dev Webhook",
        "status": "ACTIVE"
    }
    
    if team_id:
        payload["team_id"] = team_id
    
    print(f"\nRegistering webhook for file {file_key}...")
    print(f"Endpoint: {endpoint}")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Webhook Created Successfully!")
            print(f"Webhook ID: {data.get('id')}")
            print(f"File Key: {data.get('file_key')}")
        else:
            print(f"\n❌ Failed to create webhook (Status: {response.status_code})")
            print("Response:", response.text)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    # Support command line args: python setup_webhook.py [FILE_KEY] [NGROK_URL] [TEAM_ID]
    f_key = sys.argv[1] if len(sys.argv) > 1 else None
    n_url = sys.argv[2] if len(sys.argv) > 2 else None
    t_id = sys.argv[3] if len(sys.argv) > 3 else None
    create_webhook(f_key, n_url, t_id)
