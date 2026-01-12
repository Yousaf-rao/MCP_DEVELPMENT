# ADR 003: Write Operations & Security Model (v2)

**Date:** 2025-12-22  
**Status:** Accepted  
**Supersedes:** ADR 001 (extends security model), ADR 002 (restricts wildcard for writes)  
**Version:** 2.0 (Production-Grade Refinements)

---

## Context

Sprint 1 established read-only MCP tools with dynamic repository access. Sprint 2A introduces **write operations** (branch creation, patch application, PR management) which require production-grade security controls.

**Changes in v2:**
- Enhanced approval token design (TTL, claims, server-side minting)
- Fixed regex validation bug
- Added search workload limits for production scale
- Introduced WritePolicy framework for fine-grained control
- Reclassified `propose_patch` as read-only

---

## Decision

### 1. Tool Classification: Read vs Write

**Read Operations** (no approval token required):
- `list_repo_files`, `read_file`, `locate_component`, `search_content`
- **`propose_patch`** (NEW: reclassified from write to read)
  - Generates diff preview only
  - No filesystem mutations
  - Returns: `{ diff, summary, risks }`
  - Rationale: Dry-run operations don't need consent gates

**Write Operations** (approval token mandatory):
- `create_branch`, `apply_patch`, `open_pull_request`, `merge_guarded`
- Explicit repo required (no wildcards, no auto-discovery)
- Desktop excluded from `allowed_roots` in production
- WritePolicy enforcement (deny-by-default)

### 2. Enhanced Approval Token System

**Token Structure v2**:
```python
{
  "version": 1,                    # Protocol version
  "operation": "create_branch",    # Tool name
  "repo": "myproject",             # Repository name
  "timestamp": 1703234567,         # Unix timestamp
  "nonce": "abc123...",            # 32-byte hex (replay protection)
  "approver_id": "user@example.com",
  "aud": "mcp-server",             # Audience (prevents cross-service misuse)
  "host_id": "claude-code",        # Minting host identifier
  "signature": "hmac-sha256..."    # HMAC signature
}
```

**Key Improvements**:
- **TTL: 2-5 minutes** (was 60s) with ±30s clock skew tolerance
- **Version field**: Enables protocol evolution
- **Audience validation**: Tokens scoped to specific server
- **Host tracking**: Know which client minted the token

**Server-Side Minting**:
```
Client → Server: POST /mint-token {operation, repo, approver_id}
          ↓
Server: Validate user session, create token, sign with secret
          ↓
Client ← Server: {token} (signed, never sees secret_key)
          ↓
Client → Server: Tool call with {approval_token}
```

**Security Properties**:
- Secret key never leaves server
- Nonce store with TTL (in-memory LRU or Redis)
- HMAC constant-time comparison
- Token reuse prevented (nonce tracking)

### 3. Repository Validation (Bug Fix)

**Regex Error (v1)**:
```python
SAFE_REPO_RE = re.compile(r"^\[A-Za-z0-9._-\]\+$")  # WRONG! Matches literal brackets
```

**Corrected (v2)**:
```python
SAFE_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+$")     # Correct character class
```

Validates: `myproject`, `api-service`, `frontend_v2`  
Blocks: `../../etc/passwd`, `repo/with/slashes`

### 4. Search Workload Limits (Production Scale)

**Problem**: `search_content` on large monorepos can cause:
- Memory exhaustion (millions of files)
- Slow P95 latency (scanning binaries)
- DoS risk (unbounded work)

**Solution - Configuration Caps**:
```python
@dataclass
class SearchConfig:
    max_files_per_root: int = 10_000           # Total files to scan
    max_matches_per_file: int = 10             # Matches returned per file
    max_results: int = 100                     # Total files in response
    allowed_extensions: List[str] = [          # Whitelist code files
        ".js", ".ts", ".tsx", ".jsx", ".py",
        ".css", ".html", ".json", ".md", ".yaml"
    ]
    binary_size_threshold: int = 8192         # Skip files >8KB non-text bytes
```

**Implementation**:
- Early exit when `max_files_per_root` reached
- Extension filter before reading file
- Binary detection heuristic (byte ratio check)

### 5. WritePolicy Framework

**Per-Repository Fine-Grained Control**:
```python
@dataclass
class WritePolicy:
    repo: str
    allowed_branches: List[str] = field(default_factory=lambda: ["^feature/.*$", "^bugfix/.*$"])
    max_diff_size: int = 10_000                # Bytes
    max_changed_files: int = 10                # Number of files
    max_changed_lines: int = 400               # Total line changes
    require_codeowners: bool = True
    disallowed_paths: List[str] = field(default_factory=lambda: [
        ".github/workflows/",                  # Prevent CI poisoning
        "src/auth/",                           # Sensitive code
    ])
    allowed_operations: List[str] = field(default_factory=lambda: [
        "create_branch", "apply_patch", "open_pull_request"
    ])
```

**Enforcement**:
- Deny-by-default: No WritePolicy = no writes allowed
- Regex branch matching (`re.match(pattern, branch_name)`)
- Path intersection check for `disallowed_paths`

### 6. Environment Configuration

**Development**:
```python
DEV_ALLOW_ALL_REPOS=true
ALLOWED_ROOTS=[Desktop, ./sample-projects, .]
MCP_APPROVAL_SECRET=dev-secret-change-in-prod
```

**Production**:
```python
DEV_ALLOW_ALL_REPOS=false
ALLOWED_REPOS=["myproject", "api-service"]  # Explicit, no wildcards
ALLOWED_ROOTS=[/repos/allowed]              # No Desktop
MCP_APPROVAL_SECRET=<32-byte-random-key-from-secrets-manager>
```

### 7. Enhanced Audit Schema (Final)

```python
@dataclass
class AuditLog: 
    # Core fields
    timestamp: str
    tool_name: str
    inputs: Dict[str, Any]
    outputs: Optional[Any]
    duration_ms: float
    success: bool
    error: Optional[str] = None
    
    # Write operation tracking
    approver: Optional[str] = None           # From token.approver_id
    correlation_id: Optional[str] = None     # Workflow UUID
    side_effects: bool = False               # True for writes
    target_ref: Optional[str] = None         # Branch/commit/merge SHA
    host_id: Optional[str] = None            # From token.host_id
```

---

## Consequences

### Positive
- **Production-ready security**: Enhanced tokens prevent common attacks
- **Observable operations**: Comprehensive audit trail with host tracking
- **Scalable search**: Workload limits prevent DoS on large repos
- **Flexible policies**: Per-repo WritePolicy enables gradual rollout
- **Bug fixes**: Regex validation now correct

### Negative
- **Increased complexity**: More configuration to manage
- **Token minting endpoint**: Requires server-side HTTP or stdio handler
- **Policy management**: Teams must maintain WritePolicy configs

### Mitigations
- **Default policies**: Sensible defaults for common use cases
- **Policy validation**: Startup checks for malformed policies
- **Clear errors**: Structured responses when policies block operations

---

## Implementation Roadmap

### Phase 1: Core Refinements (Week 1.1 v2)
1. ✅ Fix `SAFE_REPO_RE` regex
2. ✅ Enhance `ApprovalToken` with v2 fields
3. ✅ Add `SearchConfig` and workload limits
4. ✅ Create `WritePolicy` dataclass
5. ✅ Update environment validation

### Phase 2: Token Minting (Week 1.2 Prep)
6. Add `/mint-token` endpoint (stdio/HTTP)
7. Implement nonce store with TTL
8. Add clock skew tolerance (±30s)

### Phase 3: Diff Operations (Week 1.2)
9. Implement `propose_patch` (read-only)
10. Implement `apply_patch` with WritePolicy enforcement
11. Add `git apply --check` validation

### Phase 4: PR Integration (Week 1.3)
12. GitHub API integration with WritePolicy
13. `merge_guarded` with real-time CI re-query
14. CODEOWNERS parsing

---

## Security Considerations

### Threat Model
| Threat | Mitigation |
|--------|-----------|
| Token replay | Nonce tracking + TTL |
| XSS → token theft | Server-side minting (no secret in client) |
| Massive diff DoS | `max_diff_size`, `max_changed_files` limits |
| CI poisoning | `disallowed_paths` blocks `.github/workflows/` |
| Stale approvals | 2-5 min TTL requires re-approval for long ops |
| Cross-service token misuse | `aud` field validation |

### Compliance
- **SOC2**: Audit log includes approver, correlation_id, timestamp
- **ISO27001**: Deny-by-default, principle of least privilege
- **GDPR**: Approver PII can be pseudonymized in logs

---

## See Also
- [ADR 001](ADR_001_Technology_Choices.md): Original read-only design
- [ADR 002](ADR_002_Dynamic_Access.md): Wildcard repos & universal search
- [Sprint 2 Tasks](task.md): Implementation tracking
