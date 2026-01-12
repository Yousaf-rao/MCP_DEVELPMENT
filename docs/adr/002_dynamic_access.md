# ADR 002: Dynamic Repository Access & Universal File Search

**Date:** 2025-12-18
**Status:** Accepted

## Context
In Sprint 1, we implemented a strict "Allow-List" security model where every repository path had to be explicitly configured in `ServerConfig`. While secure, this friction prevented ad-hoc usage (e.g., "Open this folder on my Desktop") and required users to manually edit code to access new projects.

Additionally, the `locate_component` tool was restricted to specific UI file extensions (`.tsx`, `.jsx`, etc.), which limited its utility for general-purpose file navigation.

## Decisions

### 1. Dynamic Repository Access (Wildcard Support)
**Decision:** Introduce a wildcard (`*`) capability in `allowed_repos`.
**Implementation:**
- If `allowed_repos` contains `"*"`, `validate_repo` will return `True` for any repository name.
- The server will allow access to any subdirectory within the configured `allowed_roots`.

### 2. Desktop Integration
**Decision:** Add the user's Desktop to the default `allowed_roots`.
**Implementation:**
- Added `Path.home() / "Desktop"` to `ServerConfig.allowed_roots`.
- Combined with Decision #1, this allows accessing **any folder on the Desktop** by simply using its name as the `repo` argument.

### 3. Universal File Search
**Decision:** Generalize `locate_component` to `locate_file`.
**Implementation:**
- Removed the strict allowed-extension list (previously restricted to web component types).
- Tool now searches for **any file** matching the hint string.
- Renamed description to "Find files by name hint (any extension)".

## Consequences

### Positive
- **Usability:** Zero-config access to new projects. Users can simply drop a folder on the Desktop and ask Claude to read it.
- **Flexibility:** The search tool is now useful for finding scripts, config files, and documentation, not just React components.

### Negative
- **Security Scope:** The attack surface is now "Everything on the Desktop" rather than "Specific opted-in folders". This is considered an acceptable trade-off for a local developer tool, provided the user is aware (implicit consent by running the tool).

## Compliance
This ADR updates the security model defined in ADR 001 from "Strict Explicit Allow-List" to "Root-based Containment with Wildcard Access".
