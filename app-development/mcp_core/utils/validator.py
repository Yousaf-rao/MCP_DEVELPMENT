import subprocess
import os
import logging

logger = logging.getLogger(__name__)

def validate_code(file_path: str) -> tuple[bool, str]:
    """
    Runs a syntax/type check on the generated file using TypeScript Compiler (tsc).
    Returns: (is_valid, error_message)
    """
    try:
        # We use 'tsc' (TypeScript Compiler) with --noEmit to just check for errors
        # --skipLibCheck ignores errors in node_modules (speeds it up)
        # --jsx preserve handles React syntax
        # We assume npx is available.
        # We ensure --esModuleInterop to avoid common import errors with some packages
        cmd = [
            "npx", "tsc", file_path,
            "--noEmit",
            "--skipLibCheck", 
            "--jsx", "react-jsx", 
            "--target", "esnext",
            "--moduleResolution", "node",
            "--esModuleInterop" 
        ]
        
        # Run the command
        # shell=True might be needed on Windows for npx
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=False,
            shell=True if os.name == 'nt' else False
        )
        
        if result.returncode == 0:
            return True, "✅ Code compiled successfully."
        else:
            # We captured the specific error (e.g., "Missing '}' on line 40")
            # Combine stdout and stderr
            output = result.stdout + "\n" + result.stderr
            return False, output.strip()

    except Exception as e:
        return False, f"Validation System Error: {str(e)}"
