# MCP Repository Tools Server 🚀 (Phase 8 Hardened)

A production-grade **Model Context Protocol (MCP)** server enabling AI agents to securely interact with local codebases and automate design-to-code workflows.

**Current Status:** Deployment Ready (Hardened & Verified) ✅

## ✨ Key Features

### 🛡️ Production Hardening (Phase 8)
*   **Anti-Crash System**: Robust error handling for Figma API failures (404/429/500).
*   **Anti-Freeze Protection**: Output truncation (~100KB) prevents LLM context saturation from large Figma payloads.
*   **Secrets Validation**: Startup checks for missing environment variables.

### 🎨 Figma Automation "Inbox"
*   **Zero-Touch Pipeline**: Webhook -> SQLite Inbox (`events.db`) -> Auto-PR.
*   **Simulation Mode**: Includes `simulate_webhook.py` to test the full pipeline without a paid Figma plan.
*   **Smart Fetching**: Recursive fetching with depth control to handle complex designs.

### 🛠️ Core Capabilities
*   **Deep File Search**: Multi-line code search with regex support and sliding window buffers.
*   **Secure Operations**: "Read-only by default" with approval token system for writes.
*   **Audit Logging**: SOC2-ready logging to `mcp_audit.jsonl`.

---

## 🚀 Getting Started

### 1. Installation
```bash
# Clone the repo
git clone https://git.khired.pk/logicpatch/frontend/app.git
cd app

# Setup Virtual Environment (Recommended)
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt
```

### 2. Configuration (`.env`)
Rename `.env.example` to `.env` and fill in your keys:

```ini
# Figma Integration
FIGMA_ACCESS_TOKEN=figd_your_token
FIGMA_WEBHOOK_PASSCODE=your_webhook_secret

# GitHub Automation
GITHUB_TOKEN=ghp_your_token
GITHUB_REPO=username/repo_name

# Security
MCP_APPROVAL_SECRET=dev-secret
```

### 3. Running the System

**A. Start the Core MCP Server** (For Claude/Inspector)
```bash
python -m mcp_server
```

**B. Start the Webhook Listener**
```bash
python webhook_server.py
# Listens on http://0.0.0.0:8000/figma-webhook
```

### 4. Testing the Pipeline

**Option A: Live Webhook (Requires Figma Pro)**
1.  Start ngrok: `npx ngrok http 8000`
2.  Register: `python register_webhook.py`

**Option B: Simulation (Free Plan Compatible)**   <-- **RECOMMENDED**
1.  Run the simulator to fire a fake event:
    ```bash
    python simulate_webhook.py
    ```
2.  The server will process it, update `events.db`, and trigger the workflow.

---

## 📚 Documentation
Detailed guides have been moved to the `docs/` folder:

*   [`docs/DEMO_GUIDE.md`](docs/DEMO_GUIDE.md) - Step-by-step script for demonstrating the system.
*   [`docs/DEPLOYMENT_REPORT.md`](docs/DEPLOYMENT_REPORT.md) - Full hardening and verification report.
*   [`docs/GITHUB_SETUP.md`](docs/GITHUB_SETUP.md) - Guide to generating GitHub tokens.
*   [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) - Detailed Sprint/Phase tracking.

---

## 🏗️ Architecture
The system follows the **"Inbox Pattern"** to decouple ingestion from processing:

`Figma Webhook (or Sim)` -> `Webhook Server` -> `SQLite (events.db)` -> `Claude Tools` -> `GitHub PR`

---

## 📝 License
Proprietary / Internal Use Only.
