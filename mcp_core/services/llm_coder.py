import os
import json
import logging
from typing import Dict, Any
import google.generativeai as genai
from pathlib import Path

# Initialize a logger to track what this file is doing (for debugging)
logger = logging.getLogger("llm_coder")

class LLMCoder:
    """
    This class is the 'Brain' of the operation. 
    It communicates with Google Gemini (AI) to generate, route, and fix code.
    """
    def __init__(self):
        # 1. SETUP GEMINI API
        # We look for the GEMINI_API_KEY in the environment variables (.env file).
        # Without this key, we cannot talk to the Google AI.
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY is missing from .env")
        else:
            # Configure the library with the key
            genai.configure(api_key=api_key)
        
        # 2. SELECT THE AI MODEL
        # We are using 'gemini-flash-latest' because it is fast and cost-effective.
        self.model_name = "gemini-flash-latest"
        self.model = genai.GenerativeModel(self.model_name)
        
        # 3. LOAD PROJECT SETTINGS
        # We read the 'mcp_config.json' file to understand the project's style (React, Tailwind, etc.)
        self.config = self._load_project_config()

    def _load_project_config(self) -> str:
        """
        Helper function: Reads 'mcp_config.json' to get the project's technology stack.
        Returns a string summarizing the configuration (e.g., "Use React, Tailwind...").
        """
        try:
            # Check if the config file exists
            if os.path.exists("mcp_config.json"):
                with open("mcp_config.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # If the config has profiles (e.g., 'default', 'advanced'), find the active one
                    if "active_profile" in data and "profiles" in data:
                        active_key = data["active_profile"]
                        selected_profile = data["profiles"].get(active_key)
                        
                        # Format the profile settings into a readable string for the AI
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
                    
                    # If it's a simple config without profiles
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
        
        # Fallback default if config fails to load
        return "PROJECT CONFIGURATION: React (JS/TS), Tailwind CSS, Lucide Icons."

    def generate_component(self, figma_data: Dict[str, Any], context_files: str = "", rag_context: str = "", image_path: str = None) -> Dict[str, str]:
        """
        MAIN FUNCTION: Generates React code from Figma data.
        
        Args:
            figma_data: The JSON data from Figma (node name, properties, etc.)
            context_files: Content of existing files (to match style)
            rag_context: Extra context found by searching the repo
            image_path: Path to the screenshot image (if available)
            
        Returns:
            A dictionary with 'file_name' and 'code'.
        """
        node_name = figma_data.get("name", "Component")
        
        # --- SCENARIO 1: IMAGE + DATA (VISION MODE) ---
        # If we have a screenshot, we show it to the AI for better results.
        if image_path and os.path.exists(image_path):
            logger.info("   👁️ Activating Hybrid Vision + Data Mode...")
            
            # The PROMPT tells the AI exactly what to do.
            # We must be very strict ("CRITICAL RULES") to get good code.
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

{rag_context}

JSON DATA:
{json.dumps(figma_data)}

OUTPUT FORMAT: Return a single JSON object with:
- "file_name": ComponentName.jsx (use .jsx extension)
- "code": The complete JSX code

Output ONLY the JSON. No markdown.
            """
            
            contents = [prompt_text]
            
            try:
                # Prepare the image for the Gemini API
                mime_type = "image/png"
                if image_path.lower().endswith(".jpg") or image_path.lower().endswith(".jpeg"):
                    mime_type = "image/jpeg"
                
                with open(image_path, "rb") as f:
                    image_data = f.read()
                
                image_blob = {
                    "mime_type": mime_type,
                    "data": image_data
                }
                # Attach image to the prompt
                contents.append(image_blob)
            except Exception as e:
                logger.warning(f"Failed to load image for generation: {e}")

        # --- SCENARIO 2: TEXT ONLY ---
        # If no image exists, we rely purely on the JSON data.
        else:
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

{rag_context}

FIGMA NODE DATA:
{json.dumps(figma_data)}

OUTPUT FORMAT: Return a single JSON object with:
- "file_name": ComponentName.jsx (use .jsx extension)
- "code": The complete JSX code

Output ONLY the JSON. No markdown.
            """
            contents = [prompt_text]

        # Call the Gemini API
        try:
            logger.info(f"🧠 Asking Gemini to generate code for {node_name}...")
            
            # Request specific JSON response format
            response = self.model.generate_content(
                contents,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # Check if Gemini refused to answer (safety filters)
            if not response.candidates or not response.candidates[0].content.parts:
                finish_reason = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
                logger.error(f"Gemini returned empty response (finish_reason: {finish_reason})")
                raise ValueError(f"Gemini blocked or returned empty response. Finish reason: {finish_reason}")
            
            # Parse the JSON response
            result = json.loads(response.text)
            
            # Verify we got both expected fields
            if "code" not in result or "file_name" not in result:
                raise ValueError("Gemini response missing 'code' or 'file_name' keys")
                
            return result
            
        except Exception as e:
            logger.error(f"Gemini Generation Failed: {e}")
            raise e

    def find_matching_file(self, figma_name: str, figma_text_content: str, repo_file_list: list, image_path: str = None) -> str:
        """
        ROUTING FUNCTION: Decides WHERE to save the code.
        Instead of creating new files blindly, it checks if a relevant file already exists.
        
        Args:
            figma_name: Name of the layer in Figma (e.g. "Header")
            repo_file_list: List of all files currently in the project
        
        Returns:
            The path where the file should be saved (e.g., "src/components/Header.jsx")
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
        
        # Attach image if available to help identify the component
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
            # Fallback if AI fails: Just make a new file in a default folder
            logger.error(f"Router Failed: {e}")
            safe_name = figma_name.replace(" ", "")
            return f"FigmaDesign/{safe_name}.jsx"

    def fix_code(self, code: str, error_log: str) -> str:
        """
        DEBUGGING FUNCTION: Fixes code if it fails to compile.
        
        Args:
            code: The original broken code.
            error_log: The error message from the compiler.
            
        Returns:
            Corrected code.
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
            # Clean up potential markdown formatting from the response
            return response.text.replace("```tsx", "").replace("```typescript", "").replace("```", "").strip()
        except Exception as e:
            logger.error(f"Fix failed: {e}")
            return code
