import os
import json
import logging
from typing import Dict, Any
import google.generativeai as genai
from pathlib import Path

logger = logging.getLogger("llm_coder")

class LLMCoder:
    def __init__(self):
        # 1. Configure Gemini (Legacy SDK)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY is missing from .env")
        else:
            genai.configure(api_key=api_key)
        
        # 2. Select Model
        self.model_name = "gemini-flash-latest"
        self.model = genai.GenerativeModel(self.model_name)
        
        # 3. Load Project Config
        self.config = self._load_project_config()

    def _load_project_config(self) -> str:
        """Reads mcp_config.json and selects the ACTIVE profile."""
        try:
            if os.path.exists("mcp_config.json"):
                with open("mcp_config.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    if "active_profile" in data and "profiles" in data:
                        active_key = data["active_profile"]
                        selected_profile = data["profiles"].get(active_key)
                        
                        if selected_profile:
                            config_str = f"--- ACTIVE CONFIG: {active_key.upper()} ---\n"
                            for key, value in selected_profile.items():
                                if isinstance(value, list):
                                    val_str = "\n".join([f"  - {v}" for v in value])
                                    config_str += f"- {key}:\n{val_str}\n"
                                else:
                                    config_str += f"- {key}: {value}\n"
                            return config_str
                        else:
                            return "ERROR: Active profile not found in config."
                    
                    else:
                        config_str = "PROJECT CONFIGURATION:\n"
                        for key, value in data.items():
                            if isinstance(value, list):
                                val_str = "\n".join([f"  - {v}" for v in value])
                                config_str += f"- {key}:\n{val_str}\n"
                            else:
                                config_str += f"- {key}: {value}\n"
                        return config_str

        except Exception as e:
            logger.warning(f"Could not load mcp_config.json: {e}")
        
        return "PROJECT CONFIGURATION: React (JS/TS), Tailwind CSS, Lucide Icons."

    def generate_component(self, figma_data: Dict[str, Any], context_files: str = "", image_path: str = None) -> Dict[str, str]:
        """
        Sends Figma data (and optional Image) to Gemini and returns {file_name, code}.
        """
        node_name = figma_data.get("name", "Component")
        
        # Construct the Prompt
        if image_path and os.path.exists(image_path):
            logger.info("   👁️ Activating Hybrid Vision + Data Mode...")
            
            prompt_text = f"""
You are a Senior Frontend Engineer specializing in React and Material UI (MUI).
Your task is to generate production-grade React JSX code based on the Figma design provided.

### CRITICAL RULES:
1. **JSX Format:** Generate .jsx files (JavaScript, NOT TypeScript)
2. **Imports:** ALWAYS import React: `import React from 'react';`
3. **MUI Components:** Use Material UI from `@mui/material`
4. **No Hallucinations:** Only use libraries shown in the context
5. **Export:** Use `export const ComponentName` (Named Export)

### CODE PATTERN (Follow this structure):
```jsx
import React from 'react';
import {{ Box, Typography, Button }} from '@mui/material';

export const ComponentName = ({{ title, isActive = false }}) => {{
  return (
    <Box sx={{{{ p: 2, border: '1px solid #eee' }}}}>
      <Typography variant="h6">{{title}}</Typography>
      {{isActive && <Button variant="contained">Active</Button>}}
    </Box>
  );
}};
```

### YOUR TASK:
SOURCE 1: THE VISUAL REFERENCE (Image)
- Look at the attached screenshot for layout and visual hierarchy.

SOURCE 2: THE TECHNICAL SPEC (Figma JSON)
- Extract EXACT colors, spacing, and text content.

{self.config}

CONTEXT:
{context_files}

JSON DATA:
{json.dumps(figma_data)}

OUTPUT FORMAT: Return a single JSON object with:
- "file_name": ComponentName.jsx (use .jsx extension)
- "code": The complete JSX code

Output ONLY the JSON. No markdown.
            """
            
            contents = [prompt_text]
            
            try:
                # Load Image for Legacy SDK
                mime_type = "image/png"
                if image_path.lower().endswith(".jpg") or image_path.lower().endswith(".jpeg"):
                    mime_type = "image/jpeg"
                
                with open(image_path, "rb") as f:
                    image_data = f.read()
                
                image_blob = {
                    "mime_type": mime_type,
                    "data": image_data
                }
                contents.append(image_blob)
            except Exception as e:
                logger.warning(f"Failed to load image for generation: {e}")

        else:
            # Standard Text-Only Prompt
            prompt_text = f"""
You are a Senior Frontend Engineer specializing in React and Material UI (MUI).
Your task is to generate production-grade React JSX code based on the Figma design data.

### CRITICAL RULES:
1. **JSX Format:** Generate .jsx files (JavaScript, NOT TypeScript)
2. **Imports:** ALWAYS import React: `import React from 'react';`
3. **MUI Components:** Use Material UI from `@mui/material`
4. **No Hallucinations:** Only use libraries shown in the context
5. **Export:** Use `export const ComponentName` (Named Export)

### CODE PATTERN (Follow this structure):
```jsx
import React from 'react';
import {{ Box, Typography, Button }} from '@mui/material';

export const ComponentName = ({{ title, isActive = false }}) => {{
  return (
    <Box sx={{{{ p: 2, border: '1px solid #eee' }}}}>
      <Typography variant="h6">{{title}}</Typography>
      {{isActive && <Button variant="contained">Active</Button>}}
    </Box>
  );
}};
```

### YOUR TASK:
{self.config}

CONTEXT:
{context_files}

FIGMA NODE DATA:
{json.dumps(figma_data)}

OUTPUT FORMAT: Return a single JSON object with:
- "file_name": ComponentName.jsx (use .jsx extension)
- "code": The complete JSX code

Output ONLY the JSON. No markdown.
            """
            contents = [prompt_text]

        try:
            logger.info(f"🧠 Asking Gemini to generate code for {node_name}...")
            
            # Generate with JSON output
            response = self.model.generate_content(
                contents,
                generation_config={"response_mime_type": "application/json"}
            )
            
            result = json.loads(response.text)
            
            if "code" not in result or "file_name" not in result:
                raise ValueError("Gemini response missing 'code' or 'file_name' keys")
                
            return result
            
        except Exception as e:
            logger.error(f"Gemini Generation Failed: {e}")
            raise e

    def find_matching_file(self, figma_name: str, figma_text_content: str, repo_file_list: list, image_path: str = None) -> str:
        """
        Asks Gemini to match a vague Figma name to a concrete Repo file.
        """
        prompt_text = f"""
        You are a Project Architect.
        
        INCOMING DESIGN:
        Name: "{figma_name}"
        Available Text: "{figma_text_content[:200]}..."
        
        EXISTING REPO FILES:
        {json.dumps(repo_file_list)}
        
        DECISION RULES:
        1. Match incoming design to the most logical existing file.
        2. If NO match exists, create a new logical path.
        
        Return JSON: {{ "matched_path": "string", "reason": "string" }}
        """
        
        contents = [prompt_text]
        
        if image_path and os.path.exists(image_path):
            try:
                mime_type = "image/png"
                if image_path.lower().endswith(".jpg") or image_path.lower().endswith(".jpeg"):
                    mime_type = "image/jpeg"
                
                with open(image_path, "rb") as f:
                    image_data = f.read()
                
                contents.append({
                    "mime_type": mime_type,
                    "data": image_data
                })
                logger.info("   👁️ Vision Activated: Image attached to prompt.")
            except Exception as e:
                logger.warning(f"Failed to load image for vision: {e}")
        
        try:
            logger.info(f"🧠 Asking Gemini to route '{figma_name}'...")
            
            response = self.model.generate_content(
                contents,
                generation_config={"response_mime_type": "application/json"}
            )
            result = json.loads(response.text)
            
            matched_path = result.get("matched_path")
            reason = result.get("reason")
            
            logger.info(f"🎯 AI Router Decision: {matched_path} (Reason: {reason})")
            return matched_path
            
        except Exception as e:
            logger.error(f"Router Failed: {e}")
            safe_name = figma_name.replace(" ", "")
            return f"src/components/{safe_name}.jsx"  # Use .jsx for prototyping mode

    def fix_code(self, code: str, error_log: str) -> str:
        """
        Asks Gemini to fix compilation errors.
        """
        prompt = f"""
        CRITICAL ERROR: The code you generated failed to compile.
        
        THE CODE:
        ```tsx
        {code}
        ```
        
        THE COMPILER ERROR:
        {error_log}
        
        TASK:
        Fix the syntax error described above. Return ONLY the corrected code.
        Do not explain. Just fix it.
        """
        
        try:
            logger.info("   🚑 Asking Gemini to fix the code...")
            response = self.model.generate_content(prompt)
            return response.text.replace("```tsx", "").replace("```typescript", "").replace("```", "").strip()
        except Exception as e:
            logger.error(f"Fix failed: {e}")
            return code
