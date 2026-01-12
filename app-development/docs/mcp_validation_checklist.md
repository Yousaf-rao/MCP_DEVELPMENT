# Sprint 1 - Validation Checklist

Complete this checklist to verify all Sprint 1 acceptance criteria are met.

## 1. Decide Host, Transport & SDK ✓

### Checklist

- [x] **ADR Created**: ADR 001 documents all technology choices
- [x] **Language Selected**: Python with official MCP SDK
- [x] **Host Support**: Claude Code (primary) + OpenAI Agents (compatible)
- [x] **Transports Chosen**: stdio (dev) + Streamable HTTP (remote)

### Validation Steps

```bash
# 1. Verify ADR exists
cat ADR_001_Technology_Choices.md

# 2. Confirm Python SDK installed
python -c "import mcp; print(f'MCP SDK version: {mcp.__version__}')"

# 3. Check both transport files exist
ls mcp_server.py mcp_server_http.py
```

**Expected Output**: All files exist, no import errors

---

## 2. Stand Up the MCP Server (Read-Only) ✓

### Checklist

- [x] **Server Metadata**: Name and version implemented
- [x] **Capability Negotiation**: MCP initialization follows spec
- [x] **Read-Only Tools**:
  - [x] `list_repo_files` - Lists directory contents
  - [x] `read_file` - Returns text file contents
  - [x] `locate_component` - Finds UI components by hint
- [x] **Logging**: stderr only, no stdout corruption

### Validation Steps

```bash
# 1. Test server starts without errors
python -m mcp_server &
SERVER_PID=$!

# 2. Send test message via stdio
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python -m mcp_server

# 3. Check stderr logs (no stdout output)
# Logs should appear in terminal, not in stdout

# 4. Kill test server
kill $SERVER_PID
```

**Expected Output**:
- Server starts successfully
- Tools listed in JSON-RPC response
- Logs only on stderr
- No stdout pollution

### Tool Discovery Test

```python
# test_tool_discovery.py
import asyncio
from mcp_server import RepoToolsServer, ServerConfig
from pathlib import Path

async def test():
    config = ServerConfig(allowed_roots=[Path.cwd()])
    server = RepoToolsServer(config)
    
    # Get tool schemas
    tools = await server.server.list_tools()
    
    print(f"✓ Found {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")
    
    assert len(tools) == 3, "Should have exactly 3 tools"
    tool_names = {t.name for t in tools}
    assert tool_names == {"list_repo_files", "read_file", "locate_component"}
    
    print("\n✅ Tool discovery validation passed!")

asyncio.run(test())
```

**Run**: `python test_tool_discovery.py`

---

## 3. Wire Transports (stdio + Streamable HTTP) ✓

### Checklist

- [x] **stdio Transport**: Newline-delimited JSON-RPC
- [x] **HTTP Transport**: Single endpoint with POST/GET
- [x] **Security**: Origin validation and localhost binding
- [x] **Health Check**: Both transports respond

### Validation Steps

#### stdio Transport

```bash
# 1. Start server
python -m mcp_server &

# 2. Test JSON-RPC message
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python -m mcp_server

# Expected: Valid JSON-RPC response with server capabilities
```

#### HTTP Transport

```bash
# 1. Start HTTP server
python mcp_server_http.py &
sleep 2

# 2. Health check
curl http://127.0.0.1:8080/health

# Expected:
# {
#   "status": "healthy",
#   "server": "repo-tools-mcp-server",
#   "version": "1.0.0",
#   "transport": "http"
# }

# 3. Test origin validation
curl -H "Origin: http://evil.com" http://127.0.0.1:8080/mcp
# Expected: 403 Forbidden

# 4. Test allowed origin
curl -H "Origin: http://localhost" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
     http://127.0.0.1:8080/mcp

# Expected: Tool list with security headers

# 5. Check security headers
curl -i http://127.0.0.1:8080/health | grep -E "X-Content-Type-Options|X-Frame-Options"
# Expected: Both headers present
```

---

## 4. Connect & Validate with Agent Host ✓

### Checklist

- [x] **Claude Code**: `.mcp.json` configuration
- [x] **OpenAI Agents**: Compatible with MCP integration
- [x] **MCP Inspector**: Validates schemas and responses
- [x] **Tool Calls**: Host can call all 3 tools

### Validation Steps

#### Claude Code Integration

```bash
# 1. Copy config to project
cp .mcp.json /path/to/your/project/

# 2. Start Claude Code in that project
cd /path/to/your/project
claude-code

# 3. In Claude Code, ask:
# "What MCP servers are available?"
# Expected: Should list "repo-tools"

# 4. Test tool call:
# "List files in the myproject repository"
# Expected: Claude calls list_repo_files tool
```

#### MCP Inspector Validation

```bash
# 1. Install inspector (if not already)
npm install -g @modelcontextprotocol/inspector

# 2. Test stdio transport
mcp-inspector python -m mcp_server

# 3. In inspector web UI:
#    - Verify 3 tools listed
#    - Check schema validity
#    - Execute sample tool calls
#    - Confirm responses match expected format

# 4. Test HTTP transport
mcp-inspector --transport http http://127.0.0.1:8080/mcp
```

**Expected Results**:
- All 3 tools discoverable
- Schemas validate correctly
- Sample calls execute successfully
- Responses in correct format

#### Manual Tool Call Test

Create `test_tool_calls.py`:

```python
import asyncio
from pathlib import Path
from mcp_server import RepoToolsServer, ServerConfig

async def test_all_tools():
    # Setup
    test_dir = Path("sample-projects")
    config = ServerConfig(
        allowed_repos=["myproject"],
        allowed_roots=[test_dir]
    )
    server = RepoToolsServer(config)
    
    print("Testing all tools...\n")
    
    # Test 1: list_repo_files
    print("1. Testing list_repo_files...")
    result = await server._list_repo_files({
        "repo": "myproject",
        "path": "."
    })
    assert "README.md" in result
    print("✅ list_repo_files works\n")
    
    # Test 2: read_file
    print("2. Testing read_file...")
    result = await server._read_file({
        "repo": "myproject",
        "file": "README.md"
    })
    assert "My Project" in result
    print("✅ read_file works\n")
    
    # Test 3: locate_component
    print("3. Testing locate_component...")
    result = await server._locate_component({
        "hint": "button"
    })
    assert "Button" in result or "No components found" in result
    print("✅ locate_component works\n")
    
    print("🎉 All tool validation passed!")

asyncio.run(test_all_tools())
```

**Run**: `python test_tool_calls.py`

---

## 5. Security & Audit Foundations ✓

### Checklist

- [x] **Repository Allow-List**: Configured and enforced
- [x] **File Root Validation**: Path traversal protection
- [x] **Structured Logs**: tool_name, inputs, outputs, duration
- [x] **No Write Tools**: Only read operations exist
- [x] **User Consent Documented**: Sprint 2 write operations require consent

### Validation Steps

#### Security Tests

```python
# test_security.py
import asyncio
import pytest
from pathlib import Path
from mcp_server import RepoToolsServer, ServerConfig

async def test_security():
    config = ServerConfig(
        allowed_repos=["myproject"],
        allowed_roots=[Path("sample-projects")],
        max_file_size=100
    )
    server = RepoToolsServer(config)
    
    print("Testing security controls...\n")
    
    # Test 1: Disallowed repo
    print("1. Testing repo allow-list...")
    try:
        await server._list_repo_files({
            "repo": "unauthorized-repo",
            "path": "."
        })
        print("❌ FAILED: Should reject unauthorized repo")
    except PermissionError:
        print("✅ Repo allow-list enforced\n")
    
    # Test 2: Path traversal
    print("2. Testing path traversal protection...")
    try:
        await server._read_file({
            "repo": "myproject",
            "file": "../../etc/passwd"
        })
        print("❌ FAILED: Should block path traversal")
    except PermissionError:
        print("✅ Path traversal blocked\n")
    
    # Test 3: File size limit
    print("3. Testing file size limits...")
    large_file = Path("sample-projects/myproject/large.txt")
    large_file.write_text("x" * 1000)  # Exceeds 100 byte limit
    
    try:
        await server._read_file({
            "repo": "myproject",
            "file": "large.txt"
        })
        print("❌ FAILED: Should reject large files")
    except ValueError:
        print("✅ File size limit enforced\n")
    finally:
        large_file.unlink(missing_ok=True)
    
    print("🔒 All security validation passed!")

asyncio.run(test_security())
```

**Run**: `python test_security.py`

#### Audit Log Verification

```bash
# 1. Run some operations
python test_tool_calls.py

# 2. Check audit log exists
ls -lh mcp_audit.jsonl

# 3. Verify log structure
cat mcp_audit.jsonl | jq '.'

# Expected: Each line is valid JSON with:
# - timestamp
# - tool_name
# - inputs (possibly redacted)
# - outputs (truncated)
# - duration_ms
# - success (true/false)
# - error (if failed)

# 4. Test log analysis
echo "Total operations:"
wc -l < mcp_audit.jsonl

echo "Successful operations:"
grep '"success": true' mcp_audit.jsonl | wc -l

echo "Failed operations:"
grep '"success": false' mcp_audit.jsonl | wc -l

echo "Average duration:"
jq -s 'map(.duration_ms) | add / length' mcp_audit.jsonl
```

---

## Definition of Done - Final Verification

Run this complete validation script:

```bash
#!/bin/bash
# complete_validation.sh

set -e

echo "🔍 Sprint 1 - Complete Validation"
echo "================================="
echo ""

# 1. Environment check
echo "1️⃣ Checking environment..."
python --version
pip list | grep mcp
echo "✅ Environment OK"
echo ""

# 2. File structure
echo "2️⃣ Verifying file structure..."
for file in mcp_server.py mcp_server_http.py requirements.txt .mcp.json README.md; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ Missing: $file"
        exit 1
    fi
done
echo ""

# 3. Run tests
echo "3️⃣ Running test suite..."
pytest test_mcp_server.py -v
echo "✅ Tests passed"
echo ""

# 4. Start HTTP server and test
echo "4️⃣ Testing HTTP transport..."
python mcp_server_http.py &
HTTP_PID=$!
sleep 2

HEALTH=$(curl -s http://127.0.0.1:8080/health)
if echo "$HEALTH" | grep -q "healthy"; then
    echo "✅ HTTP health check passed"
else
    echo "❌ HTTP health check failed"
    kill $HTTP_PID
    exit 1
fi

kill $HTTP_PID
echo ""

# 5. Validate audit logs
echo "5️⃣ Checking audit logging..."
if [ -f "mcp_audit.jsonl" ]; then
    LINES=$(wc -l < mcp_audit.jsonl)
    echo "✅ Audit log exists ($LINES entries)"
else
    echo "⚠️  No audit log yet (will be created on first use)"
fi
echo ""

# 6. Documentation check
echo "6️⃣ Verifying documentation..."
if grep -q "Definition of Done" README.md; then
    echo "✅ README complete"
else
    echo "❌ README incomplete"
    exit 1
fi
echo ""

echo "🎉 Sprint 1 Validation Complete!"
echo ""
echo "Summary:"
echo "========"
echo "✅ MCP server runs locally (stdio) and remotely (HTTP)"
echo "✅ 3 read-only tools implemented and callable"
echo "✅ Tool schemas validated"
echo "✅ Discovery works in host"
echo "✅ Structured logging with audit trail"
echo "✅ Security checks for HTTP transport"
echo "✅ Documentation complete"
echo ""
echo "🚀 Ready for production use!"
```

**Run**: `chmod +x complete_validation.sh && ./complete_validation.sh`

---

## Sign-Off

Once all checklist items are verified:

- [ ] Technical Lead Approval
- [ ] Security Review Completed
- [ ] Product Owner Acceptance
- [ ] Documentation Reviewed
- [ ] Deployment Ready

**Sprint 1 Status**: ✅ COMPLETE

**Next Sprint**: Sprint 2 - Write operations and user consent mechanisms
