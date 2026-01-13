import os
import json
import logging
from typing import Dict, Any
import google.generativeai as genai

logger = logging.getLogger("llm_coder")

class LLMCoder:
    def __init__(self):
        # 1. Configure Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            # We log a warning instead of crashing init, so the worker can start
            # but will fail gracefully when trying to generate if key is still missing.
            logger.warning("GEMINI_API_KEY is missing from .env")
        else:
            genai.configure(api_key=api_key)
        
        # 2. Select Models (Optimization)
        self.flash_model = "gemini-1.5-flash"
        self.pro_model = "gemini-1.5-pro"
        self.model_name = self.flash_model # Default fallback
        
        # 3. Load Project Config
        self.config = self._load_project_config()

    def _load_project_config(self) -> str:
        """Reads mcp_config.json and selects the ACTIVE profile."""
        try:
            if os.path.exists("mcp_config.json"):
                with open("mcp_config.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # 1. Check if using the new "Profile" system
                    if "active_profile" in data and "profiles" in data:
                        active_key = data["active_profile"]
                        selected_profile = data["profiles"].get(active_key)
                        
                        if selected_profile:
                            # Found the specific profile (e.g., "web_tailwind")
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
                    
                    # 2. Fallback for simple/flat config files
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
        # Ensure configured
        if not os.getenv("GEMINI_API_KEY"):
             raise ValueError("GEMINI_API_KEY is missing from .env")
        
        node_name = figma_data.get("name", "Component")
        
        # Re-init model object to ensure config is picked up if set runtime
        # GENERATION = PRO MODEL (Smarter)
        model = genai.GenerativeModel(
            model_name=self.pro_model, 
            generation_config={"response_mime_type": "application/json"}
        )
        
        # 3. Construct the Prompt (Hybrid vs Standard)
        if image_path and os.path.exists(image_path):
            logger.info("   👁️ Activating Hybrid Vision + Data Mode...")
            
            prompt_text = f"""
            You are an expert Senior Frontend Engineer with a specialty in 'Pixel-Perfect' implementation.
            
            {self.config}
            
            I am providing you with two sources of truth for this component:

            SOURCE 1: THE VISUAL REFERENCE (Image)
            - Look at the attached screenshot to understand the "Gestalt" of the component.
            - Use this to determine:
                - The overall layout strategy (e.g., "This is a Card with a floating badge").
                - The visual hierarchy (what stands out?).
                - Complex alignments (e.g., "The icon is centered relative to the text").

            SOURCE 2: THE TECHNICAL SPEC (Figma JSON)
            - Use the JSON data below for EXACT implementation details.
            - You must extract:
                - Exact Hex Colors (Do not guess from the image).
                - Exact Padding/Margin values.
                - Exact Text Content strings.

            CONFLICT RESOLUTION RULES:
            1. If the JSON structure seems messy (too many nested frames), use the IMAGE to simplify the HTML structure.
            2. If the Image colors look different due to compression, ALWAYS trust the JSON hex codes.
            3. If the Image text is blurry, ALWAYS trust the JSON text characters.

            CRITICAL OUTPUT RULES:
            1. OUTPUT FORMAT: return a single JSON object with keys "file_name" and "code".
            2. Code must be responsive and accessible.
            
            CONTEXT (Design System / Config):
            {context_files}
            
            JSON DATA:
            {json.dumps(figma_data)}
            """
            
            try:
                import PIL.Image
                img = PIL.Image.open(image_path)
                request_content = [prompt_text, img]
            except Exception as e:
                logger.warning(f"Failed to load image for generation: {e}")
                request_content = [prompt_text] # Fallback to text usage using standard logic implies text-only prompt, but here we keep the hybrid prompt text which is fine.

        else:
            # Standard Text-Only Prompt
            prompt_text = f"""
            You are an expert Senior React Developer. 
            Your task is to convert this Figma JSON data into a production-ready React component.
            
            {self.config}
            
            CRITICAL OUTPUT RULES:
            1. OUTPUT FORMAT: You must return a single JSON object with keys "file_name" and "code".
            2. Ensure the code is responsive and accessible.
            3. Do not output markdown.
            
            CONTEXT (Design System / Config):
            {context_files}

            FIGMA NODE DATA:
            {json.dumps(figma_data)}
            
            Generate the React component now.
            """
            request_content = prompt_text

        try:
            logger.info(f"🧠 Asking Gemini to generate code for {node_name}...")
            
            # 4. Generate
            response = model.generate_content(request_content)
            
            # 5. Parse
            # Since we set response_mime_type to json, we don't need regex hacking
            result = json.loads(response.text)
            
            # Validation check
            if "code" not in result or "file_name" not in result:
                raise ValueError("Gemini response missing 'code' or 'file_name' keys")
                
            return result
            
        except Exception as e:
            logger.error(f"Gemini Generation Failed: {e}")
            raise e
    def find_matching_file(self, figma_name: str, figma_text_content: str, repo_file_list: list, image_path: str = None) -> str:
        """
        Asks Gemini to match a vague Figma name to a concrete Repo file.
        Supports multimodal input (Vision) if image_path is provided.
        """
        # Ensure configured (in case called before generate)
        if not os.getenv("GEMINI_API_KEY"):
             raise ValueError("GEMINI_API_KEY is missing from .env")
             
        # ROUTING = FLASH MODEL (Fast/Cheap)
        model = genai.GenerativeModel(
            model_name=self.flash_model, 
            generation_config={"response_mime_type": "application/json"}
        )

        prompt_text = f"""
        You are a Project Architect.
        
        INCOMING DESIGN:
        Name: "{figma_name}"
        Visible Text: "{figma_text_content[:200]}..." (Truncated)
        
        EXISTING REPO FILES:
        {json.dumps(repo_file_list)}
        
        DECISION RULES:
        1. Look at the image (if provided) and the text to understand the UI component.
        2. Match it to the most logical existing file in the repo.
        3. If NO match exists, create a new logical path.
        
        Return JSON: {{ "matched_path": "string", "reason": "string" }}
        """
        
        request_content = [prompt_text]
        
        if image_path and os.path.exists(image_path):
            try:
                import PIL.Image
                img = PIL.Image.open(image_path)
                request_content.append(img)
                logger.info("   👁️ Vision Activated: Image attached to prompt.")
            except Exception as e:
                logger.warning(f"Failed to load image for vision: {e}")
        
        try:
            logger.info(f"🧠 Asking Gemini to route '{figma_name}' to the correct file path...")
            response = model.generate_content(request_content)
            result = json.loads(response.text)
            
            matched_path = result.get("matched_path")
            reason = result.get("reason")
            
            logger.info(f"🎯 AI Router Decision: {matched_path} (Reason: {reason})")
            return matched_path
            
        except Exception as e:
            logger.error(f"Router Failed: {e}")
            # Fallback to a safe default if routing fails
            safe_name = figma_name.replace(" ", "")
            return f"src/components/{safe_name}.tsx"

    def fix_code(self, code: str, error_log: str) -> str:
        """
        Asks Gemini to fix compilation errors.
        """
        # FIXING = FLASH MODEL (Fast)
        model = genai.GenerativeModel(model_name=self.flash_model)
        
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
            response = model.generate_content(prompt)
            # Cleanup markdown if present
            fixed_code = response.text.replace("```tsx", "").replace("```typescript", "").replace("```", "").strip()
            return fixed_code
        except Exception as e:
            logger.error(f"Fix failed: {e}")
            return code # Return original if fix fails
