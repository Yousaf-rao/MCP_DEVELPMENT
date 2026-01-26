
import requests
import os
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

if not TEAM_ID:
    print("❌ Error: FIGMA_TEAM_ID not found in .env")
    exit()

print(f"Asking Figma for active webhooks for Team ID: {TEAM_ID}...")

headers = {"X-Figma-Token": TOKEN}

# 1. Try fetching Team Webhooks (Standard for File Updates)
url = f"https://api.figma.com/v2/teams/{TEAM_ID}/webhooks"
response = requests.get(url, headers=headers)

if response.status_code == 200:
    hooks = response.json().get("webhooks", [])
    if not hooks:
        print("No webhooks found for this Team.")
    for hook in hooks:
        print(f"FOUND WEBHOOK:")
        print(f"   - ID: {hook['id']}")
        print(f"   - Event: {hook['event_type']}")
        print(f"   - Endpoint: {hook['endpoint']}")
        print(f"   - Status: {hook['status']}")
        print("--------------------------------")
else:
    print(f"Failed to list webhooks: {response.status_code} - {response.text}")
