import os
import json
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import mcp_core
sys.path.append(str(Path(__file__).parent))

from mcp_core import ApprovalToken

load_dotenv()

secret = os.getenv("MCP_APPROVAL_SECRET")
if not secret:
    print("Error: MCP_APPROVAL_SECRET not found in environment or .env")
    sys.exit(1)

def generate_token():
    # Defaults for testing
    operation = "save_code_file"
    repo = "myproject" # Or any valid repo name
    approver = "test-user@example.com"
    host_id = "inspector-test"
    
    print(f"Generating token for operation: {operation}")
    
    token = ApprovalToken.create(
        operation=operation,
        repo=repo,
        approver_id=approver,
        host_id=host_id,
        secret_key=secret
    )
    
    # Convert to dictionary for easy copying
    token_dict = {
        "version": token.version,
        "operation": token.operation,
        "repo": token.repo,
        "timestamp": token.timestamp,
        "nonce": token.nonce,
        "approver_id": token.approver_id,
        "aud": token.aud,
        "host_id": token.host_id,
        "signature": token.signature
    }
    
    print("\n✅ Token Generated Successfully!")
    print("\nCopy this JSON object and paste it into the 'approval_token' field in the Inspector:\n")
    print(json.dumps(token_dict, indent=2))

if __name__ == "__main__":
    generate_token()
