
import requests
import os
import argparse
from dotenv import load_dotenv
from pathlib import Path

# Load env from parent dir
load_dotenv(Path(__file__).parent.parent / ".env")

# CONFIG
TOKEN = os.getenv("FIGMA_ACCESS_TOKEN")
TEAM_ID = os.getenv("FIGMA_TEAM_ID") 

if not TOKEN:
    print("❌ Error: FIGMA_ACCESS_TOKEN not found in .env")
    exit()

def delete_webhook(webhook_id):
    print(f"Deleting Webhook ID: {webhook_id}...")
    
    headers = {"X-Figma-Token": TOKEN}
    url = f"https://api.figma.com/v2/webhooks/{webhook_id}"
    
    response = requests.delete(url, headers=headers)
    
    if response.status_code == 204:
        print(f"Successfully deleted webhook {webhook_id}")
    else:
        print(f"Failed to delete webhook {webhook_id}: {response.status_code} - {response.text}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ids", nargs='+', help="Webhook IDs to delete")
    args = parser.parse_args()
    
    for wid in args.ids:
        delete_webhook(wid)
