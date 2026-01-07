# MCP Repository Tools Server 🚀

A production-grade **Model Context Protocol (MCP)** server enabling AI agents to securely interact with local codebases and automate design-to-code workflows.

## ✨ Features

### 🛠️ Core Capabilities
*   **Deep File Search**: Multi-line code search with regex support.
*   **Git Integration**: Safely create branches and manage version control.
*   **Secure Operations**: "Read-only by default" with approval token system for writes.
*   **Audit Logging**: SOC2-ready logging of all operations to `mcp_audit.jsonl`.

### 🎨 Figma Automation Suite
*   **Event Inbox Pattern**: Captures Figma webhooks in real-time (`webhook_server.py`) and stores them in a local SQLite database (`events.db`).
*   **Smart Fetching**: Optimizes Figma API calls (using `depth=2`) to handle large files without rate-limiting.
*   **Auto-PR Worker**: A background daemon (`automation_worker.py`) that:
    1.  Detects design changes.
    2.  Generates React + Tailwind code.
    3.  **Automatically opens a GitHub Draft PR**.

---

## 🚀 Getting Started

### 1. Installation
Clone the repo and install dependencies:
```bash
git clone https://git.khired.pk/logicpatch/frontend/app.git
cd app
pip install -r requirements.txt
```

### 2. Configuration (`.env`)
Create a `.env` file in the root with the following keys:

```ini
# --- Core Security ---
MCP_APPROVAL_SECRET=your-dev-secret-key-123
MCP_AUTO_APPROVE=true         # Set 'false' for stricter security

# --- Figma Integration ---
FIGMA_ACCESS_TOKEN=figd_your_token_here
FIGMA_WEBHOOK_PASSCODE=your_webhook_secret

# --- GitHub Automation ---
GITHUB_TOKEN=your_personal_access_token
GITHUB_REPO=username/repo_name

# --- Access Control ---
ALLOWED_ORIGINS=*
```

### 3. Running the Pipeline

**A. Start the Core MCP Server (for Claude)**
```bash
# Recommended for testing with Inspector
npx -y @modelcontextprotocol/inspector python -m mcp_server

# Or for production usage with Claude Desktop
python -m mcp_server
```

**B. Start the Webhook Listener (The "Ears")**
```bash
python webhook_server.py
# Listens on http://0.0.0.0:8000/figma-webhook
```

**C. Start the Automation Worker (The "Brain")**
```bash
python automation_worker.py
# Polls for events and creates PRs
```

---

## 📚 Tools Reference

### MCP Tools (Exposed to Claude)
| Tool | Description |
| :--- | :--- |
| `list_repo_files` | Explore directory structure. |
| `read_file` | Read content of files. |
| `list_pending_events` | Check the inbox for new Figma updates. |
| `fetch_figma_pattern` | Download design nodes from Figma (optimized). |
| `generate_react_code` | Convert design nodes to React/Tailwind. |
| `save_code_file` | Save generated code to disk (Write protected). |
| `create_branch` | Create a Git branch (Write protected). |

---

## 🏗️ Architecture

The system is composed of three independent parts:

1.  **Core MCP Server** (`mcp_server.py`): The interface for the AI agent.
2.  **Webhook Receiver** (`webhook_server.py`): A standalone FastAPI app that ingests webhooks.
3.  **Automation Worker** (`automation_worker.py`): An async daemon that processes the inbox queue.

**Data Flow:**
`Figma Webhook` -> `Webhook Server` -> `SQLite DB` -> `Automation Worker` -> `GitHub PR`

---

## 📝 License
Proprietary / Internal Use Only.
