# ADR 001: Technology Choices for MCP Server (Sprint 1)

**Date:** 2025-12-17
**Status:** Accepted

## Context
We are implementing a Model Context Protocol (MCP) server to allow AI agents (specifically Claude Code/Desktop) to inspect local repositories. For Sprint 1, the requirements were to provide read-only access (list, read, locate) via a secure implementation that can run both locally and remotely.

## Decisions

### 1. Programming Language: Python
**Decision:** Use Python 3.9+ with the official `mcp` SDK.
**Rationale:**
- **Ease of Maintenance:** Python code is generally more concise and readable for file system operations.
- **Ecosystem:** The official `mcp` Python SDK is correctly typed and maintained.
- **Environment:** Most target environments (developer machines, CI/CD containers) already have Python installed.
- **Alternatives Considered:** TypeScript/Node.js. Rejected for Sprint 1 to minimize build step complexity (no compilation required for Python).

### 2. Transports: Dual Support (Stdio + HTTP)
**Decision:** Implement both `stdio` and `SSE` (Server-Sent Events) over HTTP.
**Rationale:**
- **Stdio (`mcp_server.py`):** Primary transport for local usage. Zero network overhead, easiest to secure (inherits parent process permissions). Required for easy integration with Claude Desktop.
- **HTTP (`mcp_server_http.py`):** Required for remote scenarios or when the agent runs in a different container (e.g., Docker). Allows for distinct security boundaries (Origin checks).

### 3. Security Model: Allow-List & Read-Only
**Decision:**
- Enforce strict repository allow-lists (no implicit access to entire disk).
- Restrict to Read-Only tools for Sprint 1.
- Sanitize all repository IDs and file paths to prevent traversal attacks.
**Rationale:**
- **Safety:** Prevents agents from accidentally exfiltrating sensitive system files (e.g., `/etc/passwd`) or modifying code without explicit user consent (deferred to Sprint 2).
- **Control:** Users must explicitly "opt-in" folders via configuration.

## Consequences
- **Positive:** System is secure by default. Integration with Claude is seamless via stdio.
- **Negative:** Users must manually edit `ServerConfig` or environment variables to add new repositories, which adds a setup step.

## Compliance
This ADR satisfies the acceptance criteria for "Decide host, transport & SDK" in Sprint 1.
