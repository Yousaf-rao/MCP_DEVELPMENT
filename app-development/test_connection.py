import os
import json
import asyncio
from dotenv import load_dotenv
from mcp_core.services.llm_coder import LLMCoder

# 1. Load Environment Variables
load_dotenv()

def run_test():
    print("🚀 Starting Connectivity Test...")
    
    # Check API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY is missing from .env file.")
        return

    print("✅ API Key found.")

    # 2. Initialize the Coder
    try:
        coder = LLMCoder()
        print("✅ LLMCoder service initialized.")
    except Exception as e:
        print(f"❌ Failed to initialize LLMCoder: {e}")
        return

    # 3. Simulate Figma Input (A Simple Button)
    print("\n📝 Simulating Figma Input (A Blue Primary Button)...")
    fake_figma_node = {
        "id": "123:456",
        "name": "Primary Button",
        "type": "FRAME",
        "layoutMode": "HORIZONTAL",
        "primaryAxisAlignItems": "CENTER",
        "counterAxisAlignItems": "CENTER",
        "fills": [{"type": "SOLID", "color": {"r": 0, "g": 0.5, "b": 1}}], # Blue
        "children": [
            {
                "type": "TEXT",
                "name": "Label",
                "characters": "Click Me",
                "fills": [{"type": "SOLID", "color": {"r": 1, "g": 1, "b": 1}}] # White
            }
        ]
    }

    # 4. Generate Code
    print("⏳ Asking Gemini to generate React code... (This may take a few seconds)")
    try:
        result = coder.generate_component(figma_data=fake_figma_node)
        
        print("\n✨ GENERATION SUCCESS! ✨")
        print(f"File Name: {result.get('file_name')}")
        print("-" * 40)
        print(result.get('code'))
        print("-" * 40)
        print("\n✅ Test Completed Successfully.")
        
    except Exception as e:
        print(f"\n❌ Generation Failed: {e}")
        print("Tip: Check your internet connection and API Key validity.")

if __name__ == "__main__":
    run_test()
