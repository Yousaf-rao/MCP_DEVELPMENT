# Figma Change Detection Workflow: Setup & Usage Guide

This guide will walk you through setting up the complete **Figma to GitHub** changelog and code generation workflow on your local machine.

---

## 1. Prerequisites

Before we begin, ensure you have the following:

- **Python 3.8+** installed.
- **Git** installed and initialized in this repository.
- **ngrok** installed (for exposing your local server to the internet).
  - [Download ngrok here](https://ngrok.com/download) if you haven't.
- **Figma Account** with access to create tokens and webhooks.
- **GitHub Account** with a repository for this project.

---

## 2. Environment Configuration

1.  **Locate the template**: Find the `.env.template` file in `app-development`.
2.  **Create your config**: Copy `.env.template` to a new file named `.env`.
    ```powershell
    copy .env.template .env
    ```
3.  **Fill in the secrets**: Open `.env` and fill in the values:
    - **`FIGMA_ACCESS_TOKEN`**: Generate this in Figma (Settings -> Personal Access Tokens).
    - **`FIGMA_WEBHOOK_PASSCODE`**: Create a strong, random string (e.g., `my-super-secret-passcode`). You will paste this into Figma later.
    - **`GITHUB_TOKEN`**: Generate a Personal Access Token (Classic) in GitHub with `repo` scope.
    - **`GITHUB_REPO`**: The name of your target repository (e.g., `Yousaf/my-app`).

---

## 3. Start the Webhook Server (Step 1 & 5)

This server listens for events from Figma.

1.  Open a terminal in `app-development`.
2.  Install dependencies (if not already done):
    ```powershell
    pip install -r requirements.txt
    ```
3.  Start the server:
    ```powershell
    python webhook_server.py
    ```
    ✅ You should see: `Starting Figma Async Webhook Receiver on http://localhost:8000`

---

## 4. Expose Local Server via ngrok (Step 2)

Since Figma needs a public URL to send events to, we use ngrok.

1.  Open a **new** terminal window.
2.  Run ngrok forwarding to port 8000:
    ```powershell
    ngrok http 8000
    ```
3.  Copy the **HTTPS** URL provided by ngrok (e.g., `https://a1b2-c3d4.ngrok-free.app`).

> [!IMPORTANT]
> Keep the running `ngrok` terminal open. If you close it, the URL will stop working.

---

## 5. Configure Figma Webhook (Step 3)

1.  Go to your **Figma File** that you want to track.
2.  You can set up a webhook via the Figma API or using a helper tool. Since we are developers, we can use `curl` or a simple script. 
    *Alternatively, if you have a "Manage Webhooks" plugin in Figma, you can use that.*
    
    **API Command to create webhook:**
    Replace `<FILE_KEY>`, `<YOUR_ACCESS_TOKEN>`, `<NGROK_URL>`, and `<PASSCODE>` below:
    ```bash
    curl -X POST "https://api.figma.com/v2/webhooks" \
      -H "X-Figma-Token: <YOUR_ACCESS_TOKEN>" \
      -H "Content-Type: application/json" \
      -d '{
        "event_type": "FILE_UPDATE",
        "team_id": "YOUR_TEAM_ID_OR_OMIT_IF_FILE_SCOPED", 
        "file_key": "<FILE_KEY>",
        "endpoint": "<NGROK_URL>/figma-webhook",
        "passcode": "<PASSCODE>"
      }'
    ```
    
    *Note: Figma Webhooks are a paid feature on some plans (Professional/Org), but often work on Personal tokens for specific scopes. If `file_key` is provided in the body, it creates a webhook specific to that file.*

---

## 6. Run the Automation Worker (Step 6-10)

This worker processes the events, fetches data, and creates PRs.

1.  Open a **third** terminal window in `app-development`.
2.  Run the worker:
    ```powershell
    python automation_worker.py
    ```
    ✅ You should see: `Figma-to-GitHub Automation Worker Started`

---

## 7. Testing the Workflow (The "Apply" Phase)

Now, let's verify the loop:

1.  **Trigger Event**: Go to your Figma file and make a change (e.g., change a color, text, or move a button). Figma autosaves after a few moments.
2.  **Verify Webhook**: 
    - Check your **ngrok** terminal: You should see a `POST /figma-webhook 200 OK`.
    - Check your **webhook_server** terminal: It might log the request.
3.  **Verify Worker Processing**:
    - Check the **automation_worker** terminal.
    - It should log: `Found pending events...`, `Fetching design pattern...`, `Generating React code...`.
    - Finally: `✅ Created PR: https://github.com/...`
4.  **View Comparison (Step 8 & 9)**:
    - Click the link to the **GitHub Pull Request**.
    - The "Files changed" tab in GitHub acts as your **Comparison Tool**. It shows the **Diff** between the old code (loaded from Git) and the new code (generated from Figma).

---

## Summary of Components

| Component | Status | Role |
| :--- | :--- | :--- |
| **Common** | 🧰 | `mcp_core` library (Tools: `figma.py`, `git.py`, `audit.py`) |
| **Server** | 🟢 | `webhook_server.py` (Receives data) |
| **Worker** | 🤖 | `automation_worker.py` (Process data -> GitHub PR) |
| **Tunnel** | 🚇 | `ngrok` (Exposes Server) |

## Troubleshooting

- **Signature Errors**: Ensure the `FIGMA_WEBHOOK_PASSCODE` in your `.env` matches EXACTLY what you sent to Figma when creating the webhook.
- **Database Locks**: If `automation_worker` crashes, `events.db` might be locked. Restarting the process usually fixes it.
- **No Events**: Figma triggers webhooks on "updates" which happen periodically, not arguably instantaneously on every keystroke. Wait 1-2 minutes after modifying the file.

