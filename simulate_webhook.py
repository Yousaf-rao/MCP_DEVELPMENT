import httpx
import asyncio
import os
import json
import time
from dotenv import load_dotenv
import hmac
import hashlib

load_dotenv()

async def simulate_update():
    print("🔄 Simulating Figma Webhook Event")
    print("=" * 50)
    
    # Configuration
    ENDPOINT = "http://localhost:8000/figma-webhook"
    PASSCODE = os.getenv("FIGMA_WEBHOOK_PASSCODE")
    # Real Key extracted from user URL (New Account)
    FILE_KEY = "s4ScQTZEDf1aTeTIi6RHvq" 
    
    if not PASSCODE:
        print("❌ Error: FIGMA_WEBHOOK_PASSCODE not found in .env")
        print("Please set FIGMA_WEBHOOK_PASSCODE in your .env file")
        return

    # Payload matching Figma's format
    payload = {
        "event_type": "FILE_UPDATE",
        "file_key": FILE_KEY,
        "file_name": "Weather App Design",
        "timestamp": str(time.time()),
        "webhook_id": f"sim_{int(time.time()*1000)}",
        "passcode": PASSCODE 
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
    
    print(f"📤 Sending webhook to: {ENDPOINT}")
    print(f"📁 File Key: {FILE_KEY}")
    print(f"📝 Event Type: FILE_UPDATE")
    print()
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(ENDPOINT, content=body, headers=headers, timeout=10.0)
            print(f"✅ Response Status: {resp.status_code}")
            print(f"📦 Response Body: {resp.json()}")
            
            if resp.status_code == 200:
                print("\n🎉 Success! The webhook server received the event.")
                print("💡 Next steps:")
                print("   1. Check webhook_server.py terminal for logs")
                print("   2. Check events.db for stored event")
                print("   3. Start automation_worker.py to process the event")
            else:
                print(f"\n⚠️  Unexpected status code: {resp.status_code}")
                
        except httpx.ConnectError as e:
            print(f"❌ Connection Error: {e}")
            print("\n💡 Make sure webhook_server.py is running:")
            print("   python webhook_server.py")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(simulate_update())
