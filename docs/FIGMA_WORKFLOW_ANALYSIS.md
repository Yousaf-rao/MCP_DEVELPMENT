# Figma Automation Pipeline - Workflow & Requirements Analysis

## 🔄 The "Figma Inbox" Workflow

This project implements an **asynchronous event-driven pipeline** (The "Inbox Pattern"). It decouples the *reception* of events from the *processing* of them to ensure reliability.

### Step 1: Design Change (Figma)
*   **Trigger**: A designer updates a component in Figma and saves/comments.
*   **Action**: Figma sends a webhook `POST` request to your server's endpoint (`/figma-webhook`).

### Step 2: Reliable Reception (Webhook Server)
*   **Component**: `webhook_server.py`
*   **Action**:
    1.  Verifies the security signature (`X-Figma-Passcode`).
    2.  Writes the raw event to an **SQLite Database** (`events.db`) with status `pending`.
    3.  Returns `200 OK` immediately.
*   **Why**: This ensures we never lose an event, even if the processing takes time or the GitHub API is down. It handles "bursts" of traffic without crashing.

### Step 3: Asynchronous Processing (Automation Worker)
*   **Component**: `automation_worker.py` (Background Loop)
*   **Action**:
    1.  Polls the database every 30 seconds for `pending` events.
    2.  **Fetch**: Calls Figma API (`fetch_figma_pattern`) with `depth=4` to get the full design tree.
    3.  **Generate**: Uses LLM (`LLMCoder`) to generate **React + Tailwind** code.
    4.  **MR Action**: Calls `create_figma_update_mr` (GitLab).

### Step 4: The Developer Inbox (GitLab)
*   **Component**: `gitlab_automation.py`
*   **Action**:
    1.  **De-duplication**: Checks if a branch/MR for this file already exists.
    2.  **Update**: If yes, it just updates the existing MR. If no, it creates a new one.
*   **Result**: The developer sees a Merge Request titled "Update [Component Name] from Figma".

---

## ✅ Requirements It Fulfills

This architecture was designed to solve specific operational & production risks:

| Requirement | How We Solved It |
| :--- | :--- |
| **1. No "Infinite PR Loops"** | **De-duplication Logic**: The worker checks for an open PR before creating a new one. If a designer saves 10 times, you get **1 PR** with 10 commits, not 10 PRs. |
| **2. Operational Stability** | **Async IO + SQLite WAL**: The server uses `aiosqlite` and Write-Ahead Logging to handle concurrent writes without locking or blocking the event loop. |
| **3. Complete Data ("No Hollow Shells")** | **Depth=4**: We explicitly fetch deep nested trees (Frame -> Group -> Button -> Text) so the generated code is functional, not just empty containers. |
| **4. Security (Replay Prevention)** | **Nonce Persistence**: We store used approval tokens in the database to prevent a malicious actor from re-using an intercepted packet to overwrite files. |
| **5. Developer Experience** | **The "Inbox" Model**: Changes are not forced into `main`. They arrive as **Proposals (PRs)**. Developers retain control to review, edit, or reject the code before it goes live. |
| **6. Usable Code Quality** | **Responsive Heuristics**: The generator infers `w-full` instead of `w-[1440px]` and semantic tags (`<button>`) instead of generic `<div>`s, creating mobile-friendly code. |

## Summary
You now have a **Production-Grade Design System Pipeline**. It is secure, crash-resistant, keeps your repo clean (no PR spam), and generates high-quality React code automatically.
