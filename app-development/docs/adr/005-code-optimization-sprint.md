# ADR-005: Code Optimization & Prototyping Sprint

**Date:** 2026-01-16
**Status:** Accepted
**Decision Makers:** Developer + AI Assistant

---

## Context

During a comprehensive code audit, we identified several areas needing improvement:
1. Extension logic was inconsistent with prototyping goals
2. Deprecated Python APIs were in use
3. Duplicated constants across modules
4. Inline imports scattered throughout codebase
5. Unused environment variables
6. Hardcoded values instead of centralized config

---

## Decision

We executed a 5-pass code review and optimization sprint, making the following changes:

### Pass 1: Initial Cleanup
- Removed unused `import os` from `constants.py`

### Pass 2: Code Consolidation
- Fixed extension logic in `automation_worker.py` to always use `.jsx` for prototyping
- Removed 8-line outdated TODO comments
- Moved `httpx` import to top-level in `figma.py`
- Consolidated `IGNORED_DIRS` to use shared constant from `constants.py`

### Pass 3: Configuration Sync
- Removed duplicate comment in `init_db.py`
- Moved `uuid` import to top-level in `simulate_webhook.py`
- Synced file key across test files

### Pass 4: Python 3.12+ Compatibility
- Fixed deprecated `datetime.utcnow()` → `datetime.now(timezone.utc)` in `webhook_server.py`

### Pass 5: Environment Cleanup
- Added `FIGMA_FILE_KEY` to `.env`
- Removed unused variables: `ALLOWED_ORIGINS`, `GITLAB_REPO`, `CODE_GEN_OUTPUT_PATH`
- Updated scripts to read file key from environment
- Moved inline `secrets` and `aiosqlite` imports to top-level in `security.py`

---

## Consequences

### Benefits
- **Python 3.12+ Ready**: No deprecation warnings
- **Centralized Config**: All hardcoded values now in `.env`
- **Consistent Imports**: All imports at top-level per PEP 8
- **Reduced Duplication**: Shared constants across modules
- **Production Ready**: 9 issues fixed, codebase fully optimized

### Trade-offs
- None significant

---

## Related Files Modified

| File | Changes |
|------|---------|
| `automation_worker.py` | Extension logic, comments |
| `webhook_server.py` | datetime deprecation fix |
| `figma.py` | httpx import |
| `security.py` | imports consolidation |
| `repo_search.py` | IGNORE_DIRS reuse |
| `constants.py` | unused import |
| `init_db.py` | duplicate comment |
| `simulate_webhook.py` | uuid import, file key |
| `test_pipeline.py` | file key from env |
| `.env` | cleanup, FIGMA_FILE_KEY |
| `README.md` | updated .env example |
