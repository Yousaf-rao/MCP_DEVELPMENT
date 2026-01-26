
import asyncio
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load env
load_dotenv(Path(__file__).parent.parent / ".env")

# Import our core services
from mcp_core.context import ToolContext
from mcp_core.tools import figma
from mcp_core.services.llm_coder import LLMCoder

async def direct_generate():
    print("\n🚀 STARTING DIRECT GENERATION (Bypassing Worker)...")
    
    file_key = os.getenv("FIGMA_FILE_KEY")
    node_id = "0:1" # The specific frame
    
    if not file_key:
        print("❌ Error: FIGMA_FILE_KEY not found")
        return

    ctx = ToolContext(config=None, security=None, audit=None, search_config=None, approval_secret="secret")
    coder = LLMCoder()
    
    # 1. Fetch Figma Data
    print(f"📡 Fetching Node {node_id} from File {file_key}...")
    try:
        data = await figma.fetch_figma_pattern(ctx, {"file_key": file_key, "node_ids": [node_id], "depth": 5})
        if not data.get("nodes"):
            print("❌ No nodes found. Check permissions or Node ID.")
            return
        
        node_data = data["nodes"][0]
        print(f"✅ Found Node: {node_data.get('name')}")
        
    except Exception as e:
        print(f"❌ Figma Error: {e}")
        return

    # 2. Generate Code
    print("🧠 Generating Code with Gemini...")
    try:
        result = coder.generate_component(
            figma_data=node_data,
            context_files="Use Material UI. Make it beautiful.",
            rag_context=""
        )
        
        code = result["code"]
        file_name = result["file_name"]
        
        print(f"✨ Code Generated: {file_name}")
        
        # 3. Save to React Folder
        target_dir = Path("Frontend/reactjs/src")
        target_dir.mkdir(parents=True, exist_ok=True)
        
        save_path = target_dir / file_name
        
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        print(f"💾 Saved to: {save_path}")
        
        # 4. Update App.jsx to show this component
        app_jsx_path = target_dir / "App.jsx"
        component_name = file_name.replace(".jsx", "").replace(".tsx", "")
        
        new_app_content = f"""
import React from 'react';
import {{ {component_name} }} from './{component_name}';

function App() {{
  return (
    <div style={{ padding: '20px', backgroundColor: '#f5f5f5', minHeight: '100vh' }}>
      <h1>Automation Demo</h1>
      <{component_name} />
    </div>
  );
}}

export default App;
"""
        with open(app_jsx_path, "w", encoding="utf-8") as f:
            f.write(new_app_content)
            
        print(f"🔄 Updated App.jsx to render {component_name}")
        print("✅ DONE! Check your browser.")

    except Exception as e:
        print(f"❌ Generation Error: {e}")

if __name__ == "__main__":
    asyncio.run(direct_generate())
