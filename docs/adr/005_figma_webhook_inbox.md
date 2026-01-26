# ADR 005: Figma Webhook Inbox Pattern

**Status:** Accepted  
**Date:** 2025-12-30  
**Deciders:** Engineering Team  
**Tags:** `automation`, `figma`, `webhooks`, `mcp-tools`

---

## Context

Our existing Figma integration (`fetch_figma_pattern`, `generate_react_code`) requires manual invocation. Designers update Figma files frequently, but developers must manually check for changes and regenerate code. This creates friction and delays in the design-to-code pipeline.

**Key Challenge:** MCP is a **pull-based protocol** (host → server), but Figma provides **push-based webhooks**. We need to bridge this architectural gap.

---

## Decision

We implement the **Inbox Pattern**: a dual-process architecture that separates webhook receipt (push) from MCP tool access (pull).

### Architecture

```
Figma Cloud → Webhook (POST) → webhook_server.py → SQLite (events.db)
                                                           ↓
Claude Desktop ← MCP Tools (list_pending_events) ← Read from DB
```

### Components

1. **Webhook Receiver** (`webhook_server.py`)
   - FastAPI server listening on `POST /figma-webhook`
   - Verifies Figma signatures using HMAC-SHA256
   - Persists events to SQLite (`events.db`)
   - Runs independently from MCP server

2. **Shared Database** (`events.db`)
   - Simple SQLite file with `webhooks` table
   - Stores event metadata (file_key, event_type, timestamp, status)
   - Provides idempotency (duplicate webhooks ignored)

3. **MCP Inbox Tools** (new tools in `mcp_core/tools/figma.py`)
   - `list_pending_events`: Query unprocessed webhook events
   - `mark_event_processed`: Archive handled events

### Workflow

1. Designer updates component in Figma → Figma fires webhook
2. `webhook_server.py` receives event, verifies signature, writes to DB
3. User asks Claude: "Check for new Figma updates"
4. Claude calls `list_pending_events()` → sees pending changes
5. Claude orchestrates: fetch pattern → generate code → save file → mark processed

---

## Rationale

### Why Not Direct Push to Claude?

MCP's host-driven model doesn't support server-initiated "wake-ups." The host (Claude Desktop) must initiate tool calls. We cannot push events directly into Claude's conversation.

### Why SQLite Over In-Memory Queue?

- **Persistence:** Survives server restarts
- **Simplicity:** No external database required
- **Queryability:** Standard SQL for filtering/sorting
- **Audit Trail:** Retains processed events for historical review

### Why Separate Receiver Process?

- **Public Exposure:** Webhook receiver needs a public URL (ngrok/CloudFlare Tunnel)
- **Security Isolation:** MCP server doesn't need internet exposure
- **Independent Scaling:** Webhook receiver handles bursts; MCP server runs on-demand

---

## Alternatives Considered

### 1. Polling Figma API
**Rejected:** Rate limits, API complexity, no real-time updates.

### 2. Figma Plugin + Local File Watching
**Rejected:** Requires plugin installation, doesn't scale across teams.

### 3. Monolithic Server (Webhook + MCP in one process)
**Rejected:** Complicates deployment, mixes security contexts.

---

## Implementation Details

### Database Schema
```sql
CREATE TABLE webhooks (
    id INTEGER PRIMARY KEY,
    event_id TEXT UNIQUE,
    event_type TEXT,
    file_key TEXT,
    file_name TEXT,
    timestamp TEXT,
    status TEXT DEFAULT 'pending',
    payload TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Security

- **Signature Verification:** `X-Figma-Signature` header validated via HMAC-SHA256
- **Passcode Storage:** `FIGMA_WEBHOOK_PASSCODE` in `.env` (excluded from Git)
- **Rate Limiting:** Webhook receiver responds 200 immediately, processes async
- **Idempotency:** `event_id` UNIQUE constraint prevents duplicate processing

### Dependencies

- **Webhook Receiver:** `fastapi`, `uvicorn`, `sqlite3` (stdlib)
- **MCP Tools:** No new dependencies (reuse existing DB connection)

---

## Consequences

### Positive

- **Full Automation:** Designers' changes automatically queued for Claude
- **Real-Time:** Sub-second latency from Figma update to DB entry
- **Scalable:** Handles multiple files/teams with single webhook endpoint
- **Auditable:** Complete history of design changes in `events.db`

### Negative

- **Two Processes:** Must run `webhook_server.py` alongside MCP server
- **Public Endpoint:** Requires ngrok/tunnel for local dev, or cloud deployment
- **Manual Trigger:** User still needs to ask Claude to "check for updates" (acceptable UX)

### Neutral

- **Database Management:** SQLite is zero-config but not suitable for high-concurrency production (easy migration to Postgres if needed)

---

## Testing Strategy

1. **Unit Tests:** Signature verification, event deduplication
2. **Integration Tests:** POST to webhook → verify DB write → MCP tool query
3. **Manual Testing:** Use `test_webhook.py` to simulate Figma events
4. **End-to-End:** Configure real Figma webhook, trigger design update, verify flow

---

## Future Enhancements

- **Auto-PR Creation:** On event receipt, automatically create draft PR with skeleton code
- **Batch Processing:** `process_all_pending()` tool to handle multiple events
- **Event Filtering:** Subscribe to specific file keys or event types
- **Metrics:** Track event volume, processing latency, error rates

---

## References

- [Figma Webhooks V2 Documentation](https://www.figma.com/developers/api#webhooks-v2)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- ADR 004: Figma Design-to-Code Integration
- `guides/figma_inbox_pattern.md`: Detailed implementation walkthrough
