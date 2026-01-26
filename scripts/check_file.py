
import requests
import os
from dotenv import load_dotenv
from pathlib import Path

# Load env from parent dir
load_dotenv(Path(__file__).parent.parent / ".env")

TOKEN = os.getenv("FIGMA_ACCESS_TOKEN")
FILE_KEY = "9aQwMxaBj287xHu5bovavC" # Extracted from user URL

if not TOKEN:
    print("Error: FIGMA_ACCESS_TOKEN missing")
    exit()

print(f"Checking access for File: {FILE_KEY}...")
headers = {"X-Figma-Token": TOKEN}
url = f"https://api.figma.com/v1/files/{FILE_KEY}?depth=1"

resp = requests.get(url, headers=headers)

if resp.status_code == 200:
    data = resp.json()
    print(f"SUCCESS: Found file '{data.get('name')}'")
    print(f"Last Modified: {data.get('lastModified')}")
    print(f"Editor Type: {data.get('editorType')}")
else:
    print(f"FAILED: {resp.status_code} - {resp.text}")
