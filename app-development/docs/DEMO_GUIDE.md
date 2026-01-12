# 🎭 Figma-to-Code Automation: Demo Guide

This guide outlines the steps to demonstrate the "Zero Touch" pipeline, where a design update in Figma automatically triggers code generation and a Pull Request.

**Scenario**: A designer updates the "MCP Dashboard" in Figma. The system detects the change and generates the corresponding React code.

---

## 🏗️ Pre-Demo Setup (Do this 5 mins before)

1.  **Open Terminal 1 (The Server)**
    ```bash
    cd c:\Users\s\Downloads\mcp_sprint1_bundle
    venv\Scripts\activate
    python webhook_server.py
    ```
    *Check*: You should see `Uvicorn running on http://0.0.0.0:8000`.

2.  **Open Terminal 2 (The Tunnel)**
    ```bash
    npx ngrok http 8000
    ```
    *Check*: You should see `Status: online` and a URL like `https://xxxx.ngrok-free.app`.

---

## 🎬 The Demo Script

### Step 1: The Trigger ⚡
*Narrator: "Authorized webhooks from Figma trigger our automation pipeline. Since we are on a developer setup, we will simulate the incoming signal that Figma normally sends."*

**Action (Terminal 3):**
```bash
venv\Scripts\python.exe simulate_webhook.py
```

**Expected Output:**
```text
Sending to http://localhost:8000/figma-webhook...
Response: 200
Success! The MCP Server received the event.
```

### Step 2: The Reception 📥
*Narrator: "Our decoupled Webhook Server verifies the signature and instantly acknowledges the event to prevent timeouts."*

**Action:** Switch to **Terminal 1**.
**Show:** 
```text
INFO: 127.0.0.1:xxx - "POST /figma-webhook HTTP/1.1" 200 OK
```

### Step 3: The Intelligence 🧠
*Narrator: "The event is now safely stored in our database (`events.db`). The MCP Server polls this 'Inbox' to process changes."*

**Action:** Open **Claude Desktop** (or your MCP Client).
**Ask Claude:**
> "Check for pending Figma events and process the latest one."

**Mechanism:** 
1.  Claude calls `figma.list_pending_events`.
2.  Sees the "FILE_UPDATE" for `2n7rxUZJyaAZsi2HrlDN9B`.
3.  Calls `figma.fetch_figma_pattern` (using your Token).
4.  Generates code with `figma.generate_react_code`.

### Step 4: The Delivery 📦
*Narrator: "Finally, the system commits the new code to a new branch and opens a Pull Request."*

**Note:** In this Sprint 8 configuration, the *processing* (Step 3) is manual via Claude to show the tools working. In full "Zero Touch" mode (Spring 9), a background worker handles this automatically.

---

## ❓ Troubleshooting

**"Connection Error" in Simulation?**
- Is `webhook_server.py` running?
- Did `import logging` get added? (Yes, we fixed this).

**"404 Not Found" from Figma API?**
- The simulation uses a hardcoded file key (`2n7rxUZJyaAZsi2HrlDN9B`). Ensure this file exists or update `simulate_webhook.py` with your own File Key.
