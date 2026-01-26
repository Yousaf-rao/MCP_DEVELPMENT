# ADR 004: Modular Project Structure

## Status
Accepted

## Context
As the project evolved from a prototype to a production-grade system, the root directory became cluttered with utility scripts, test files, and legacy artifacts (like `_legacy_mcp_server_http.py` and `component_registry.json`). This made navigation difficult and obscured the core application logic.

## Decision
We have reorganized the codebase into a modular structure:
1.  **`scripts/`**: All utility and maintenance scripts (`init_db.py`, `migrate_db.py`, etc.).
2.  **`tests/`**: All test suites (`test_pipeline.py`, etc.).
3.  **Root Directory**: Reserved for core servers (`mcp_server.py`, `webhook_server.py`, `automation_worker.py`) and configuration (`mcp_config.json`, `requirements.txt`).
4.  **Legacy Deletion**: Removed outdated files and the deprecated `component_registry` system.

## Consequences
### Positive
*   **Maintainability:** Clear separation of concerns makes the project easier to navigate and maintain.
*   **Clarity:** New developers can instantly identify the core application vs. support scripts.

### Negative
*   **Path Updates:** Requires updating import paths and relative path logic in scripts (completed).
