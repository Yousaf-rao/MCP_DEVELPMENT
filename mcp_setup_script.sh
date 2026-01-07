#!/bin/bash
# MCP Server Quick Setup Script
# Sprint 1 - Complete Installation and Validation

set -e

echo "🚀 MCP Repository Tools Server - Setup"
echo "======================================"
echo ""

# Check Python version
echo "📋 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.9"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3,9) else 1)"; then
    echo "❌ Error: Python 3.9+ required (found: $PYTHON_VERSION)"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "⚠️  Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate
echo "✅ Activated"
echo ""

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Create sample project structure
echo "📁 Creating sample project structure..."
mkdir -p sample-projects/myproject/src/components
mkdir -p sample-projects/demo/lib

cat > sample-projects/myproject/README.md << 'EOF'
# My Project

This is a sample project for testing the MCP server.

## Features

- Component browsing
- File reading
- Component location
EOF

cat > sample-projects/myproject/src/components/Button.tsx << 'EOF'
import React from 'react';

export const Button = ({ children, onClick }) => {
  return <button onClick={onClick}>{children}</button>;
};
EOF

cat > sample-projects/myproject/src/components/Input.tsx << 'EOF'
import React from 'react';

export const Input = ({ value, onChange }) => {
  return <input value={value} onChange={onChange} />;
};
EOF

echo "✅ Sample project structure created"
echo ""

# Configure server
echo "⚙️  Configuring server..."
cat > config.py << EOF
from pathlib import Path
from mcp_server import ServerConfig

# Server configuration
config = ServerConfig(
    name="repo-tools-mcp-server",
    version="1.0.0",
    allowed_repos=["myproject", "demo"],
    allowed_roots=[Path.cwd() / "sample-projects"],
    max_file_size=1_000_000  # 1MB
)
EOF

echo "✅ Configuration created (config.py)"
echo ""

# Create Claude Code config
echo "🔧 Creating Claude Code configuration..."
CURRENT_DIR=$(pwd)
cat > .mcp.json << EOF
{
  "mcpServers": {
    "repo-tools": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "$CURRENT_DIR",
      "env": {
        "PYTHONPATH": "$CURRENT_DIR"
      }
    }
  }
}
EOF

echo "✅ Claude Code config created (.mcp.json)"
echo ""

# Run basic validation
echo "🧪 Running validation tests..."

# Test 1: Import check
echo "  Testing imports..."
python3 -c "from mcp_server import RepoToolsServer, ServerConfig; print('✅ Imports successful')"

# Test 2: Server instantiation
echo "  Testing server instantiation..."
python3 -c "
from pathlib import Path
from mcp_server import RepoToolsServer, ServerConfig
config = ServerConfig(allowed_roots=[Path.cwd()])
server = RepoToolsServer(config)
print('✅ Server instantiation successful')
"

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "Next Steps:"
echo "==========="
echo ""
echo "1. Test with stdio transport:"
echo "   python -m mcp_server"
echo ""
echo "2. Test with HTTP transport:"
echo "   python mcp_server_http.py"
echo "   # Then visit: http://127.0.0.1:8080/health"
echo ""
echo "3. Connect to Claude Code:"
echo "   # Copy .mcp.json to your project directory"
echo "   cp .mcp.json /path/to/your/project/"
echo ""
echo "4. Test with MCP Inspector:"
echo "   npm install -g @modelcontextprotocol/inspector"
echo "   mcp-inspector python -m mcp_server"
echo ""
echo "5. Run tests:"
echo "   pytest test_mcp_server.py -v"
echo ""
echo "📚 Documentation: See README.md for detailed usage"
echo "🔒 Security: Review config.py for allowed repos and paths"
echo "📊 Audit logs: Check mcp_audit.jsonl for activity"
echo ""
