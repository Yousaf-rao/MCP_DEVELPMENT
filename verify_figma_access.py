import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("FIGMA_ACCESS_TOKEN")
FILE_KEY = "s4ScQTZEDf1aTeTIi6RHvq"

print(f"🔍 Checking Figma Configuration...")
print(f"📝 Token: {TOKEN[:4]}...{TOKEN[-4:] if TOKEN else 'None'}")
print(f"📁 File Key: {FILE_KEY}")

if not TOKEN:
    print("❌ No token found in environment!")
    exit(1)

headers = {"X-Figma-Token": TOKEN}

# 1. Test Auth (Me)
print("\n👤 Testing Token Validity (GET v1/me)...")
try:
    auth_resp = requests.get("https://api.figma.com/v1/me", headers=headers)
    print(f"Status: {auth_resp.status_code}")
    if auth_resp.status_code == 200:
        user = auth_resp.json()
        print(f"✅ Token Verified! Logged in as: {user.get('handle')} ({user.get('email')})")
    else:
        print(f"❌ Token Failed: {auth_resp.text}")
except Exception as e:
    print(f"❌ Connection Error: {e}")

# 2. Test File Access
print(f"\n📂 Testing File Access (GET v1/files/{FILE_KEY})...")
try:
    file_resp = requests.get(f"https://api.figma.com/v1/files/{FILE_KEY}?depth=1", headers=headers)
    print(f"Status: {file_resp.status_code}")
    if file_resp.status_code == 200:
        data = file_resp.json()
        print(f"✅ File Found! Name: {data.get('name')}")
    elif file_resp.status_code == 404:
        print("❌ File Not Found (404). Check the File Key.")
    elif file_resp.status_code == 403:
        print("❌ Access Denied (403). Token doesn't have permission for this file.")
    else:
        print(f"❌ Error: {file_resp.text}")
except Exception as e:
    print(f"❌ Connection Error: {e}")
