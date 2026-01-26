import subprocess
import os
import logging

logger = logging.getLogger(__name__)

def validate_code(file_path: str, cwd: str = None) -> tuple[bool, str]:
    """
    Runs a syntax check on the generated file.
    For .jsx files: Skip TypeScript validation (prototyping mode)
    For .tsx files: Use TypeScript Compiler (tsc)
    Returns: (is_valid, error_message)
    """
    # Skip validation for JSX files (prototyping mode)
    if file_path.endswith('.jsx') or file_path.endswith('.js'):
        logger.info("   ✅ JSX file detected - skipping TypeScript validation (prototyping mode)")
        return True, "✅ JSX validation skipped (prototyping mode)"
    
    try:
        # TypeScript validation for .tsx files
        cmd = [
            "npx", "tsc", file_path,
            "--noEmit",
            "--skipLibCheck", 
            "--jsx", "react-jsx", 
            "--target", "esnext",
            "--moduleResolution", "node",
            "--esModuleInterop" 
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=False,
            cwd=cwd,
            shell=True if os.name == 'nt' else False
        )
        
        if result.returncode == 0:
            return True, "✅ Code compiled successfully."
        else:
            output = result.stdout + "\n" + result.stderr
            return False, output.strip()

    except Exception as e:
        return False, f"Validation System Error: {str(e)}"
