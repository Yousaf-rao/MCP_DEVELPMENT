# Project Codebase Analysis
**Date:** January 16, 2026

This document provides a line-by-line function analysis of the current project structure.

---

## 📂 Core Application (`root` & `mcp_core/`)

### `mcp_server.py`
**Purpose:** The main entry point for the MCP Server using Standard Input/Output (stdio) transport.
- **Lines 1-23:** Imports dependencies, loads `.env`, and configures logging.
- **Lines 25-37 (`main`)**: Defines server configuration (allowed roots), initializes `RepoToolsServer`, and starts the `stdio` listener.
- **Lines 39-40:** Execution guard.

### `mcp_core/server.py`
**Purpose:** The central logic hub. It defines the MCP tools and routes requests to specific modules.
- **`RepoToolsServer` Class**:
  - `__init__`: Initializes security, audit logs, and the shared `ToolContext`.
  - `_tool_schemas`: Defines the JSON API contract for all 10 tools (filesystem, git, figma).
  - `_register_tools`: Connects the schemas to the actual Python functions.
  - `call_tool`: The "Router". It receives a tool name (e.g., `list_repo_files`) and calls the corresponding function in `mcp_core/tools/`.

### `mcp_core/tools/`
- **`filesystem.py`**: Handles local file operations (`list_repo_files`, `read_file`, `search_content`).
- **`git.py`**: Wraps GitPython for `create_branch`.
- **`figma.py`**:
  - `fetch_figma_pattern`: Async fetcher for Figma designs (optimized with depth control).
  - `list_pending_events`: Queries `events.db`.
  - `mark_event_processed`: Updates `events.db`.
  - `download_node_image_to_temp`: Downloads images for LLM vision processing.

---

## 🤖 Automation Suite (Figma Pipeline)

### `webhook_server.py`
**Purpose:** Receives "push" notifications from Figma.
- **`verify_signature`**: Security check using HMAC-SHA256 and `FIGMA_WEBHOOK_PASSCODE`.
- **`receive_webhook`**: FastAPI endpoint (`POST /figma-webhook`) that saves valid events to the database.

### `events.db` (SQLite)
- **Table `webhooks`**: Stores the queue of design updates.
  - Schema: `id`, `event_id`, `file_key`, `status` ('pending'/'processed'), `payload`.

### `automation_worker.py`
**Purpose:** The background daemon that automates the workflow.
- **`process_pending_events`**:
  1. Polls `list_pending_events`.
  2. Calls `fetch_figma_pattern`.
  3. Calls `generate_react_code`.
  4. Calls `create_merge_request` (GitLab).
  5. Calls `mark_event_processed`.

### `mcp_core/utils/gitlab_automation.py`
**Purpose:** Helper for GitLab API interactions.
- **`create_figma_update_mr`**: Creates a unique branch, commits the new code, and opens a Merge Request using `python-gitlab`.

---

## 🛠️ Support & Utilities

### `init_db.py`
- One-time script to create the `events.db` file and `webhooks` table. **Status:** Keep (for setup).

### `generate_test_token.py`
- Utility to generate HMAC tokens for testing Write Operations manually. **Status:** Keep (dev tool).

### `mcp_server_http.py`
- **Analysis:** Provides an HTTP transport (JSON-RPC over POST) instead of stdio.
- **Status:** **Potentially Unnecessary**. If you only use Claude Desktop (stdio), this file is dead code.

---

## 🧪 Tests & Verification

- `test_suite.py`: Unit tests. **Keep.**

---

## 🗑️ Cleanup Recommendations

1. **Archive/Ignore**: `mcp_server_http.py` (Unless you plan to build a custom web UI).
2. **Review**: Documentation files periodically for accuracy.
