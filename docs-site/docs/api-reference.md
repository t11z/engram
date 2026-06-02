# API reference

This summarizes the REST API. The machine-readable contract is the committed
[OpenAPI schema](https://github.com/t11z/engram/blob/main/packages/contract/openapi.json)
(`packages/contract/openapi.json`), from which the TypeScript client types are
generated; CI fails on drift between the server and that schema.

All endpoints are under `/api/v1` and require `Authorization: Bearer <token>`
(except `/healthz`). Responses are JSON unless noted. Notes are addressed by
their **vault-relative path** — the canonical handle; `{handle}` additionally
accepts an `id` or a top-level-path alias.

### Notes

| Method & path | Purpose |
|---------------|---------|
| `POST /notes` | Create a note. Idempotent via `idempotency_key`. |
| `POST /links` | Import a URL as a note. |
| `GET /notes` | List notes, newest first (`limit`, `cursor`, `tag`). |
| `GET /notes/by-path/{path}` | Read a note in full. Returns an `ETag` header. |
| `PUT /notes/by-path/{path}` | Update a note in place. Requires `If-Match` (see below). |
| `DELETE /notes/by-path/{path}` | Soft-delete (move to `.trash/`). |
| `GET /notes/by-title?title=` | Read a note by its exact title. |
| `GET /notes/{handle}` | Read by `id` or top-level-path alias. |
| `DELETE /notes/{handle}` | Soft-delete by alias. |
| `POST /notes/restore` | Restore a trashed note (`{path}`). |
| `POST /notes/append` | Append text to a note (`{path, text}`). |
| `POST /notes/patch-section` | Replace a heading's section (`{path, heading, content}`). |
| `POST /notes/daily/append` | Append to today's daily note (`{text}`). |

### Search, graph & vault structure

| Method & path | Purpose |
|---------------|---------|
| `GET /search` | Full-text search (`q`, `tag`, `limit`). |
| `GET /trash` | List trashed notes. |
| `GET /backlinks?path=` | Notes that link to this note. |
| `GET /related?path=` | Notes related via the link graph. |
| `GET /links?path=` | Outbound links from this note. |
| `GET /graph?path=&depth=` | Link neighbourhood around a note to a depth. |
| `GET /folders` | List vault folders. |
| `GET /tags` | List tags (frontmatter ∪ inline `#tags`). |

### Attachments & health

| Method & path | Purpose |
|---------------|---------|
| `GET /attachments` | List attachments. |
| `GET /attachments/by-path/{path}` | Serve the attachment file bytes. |
| `GET /healthz` | Liveness/readiness (no auth). |

### Optimistic concurrency (editing)

Reads of a note return a content-hash `ETag` header. `PUT /notes/by-path/{path}`
requires that token in an `If-Match` header:

- **`428 Precondition Required`** if `If-Match` is missing.
- **`409 Conflict`** if the token is stale (the note changed on disk since you
  read it — for example a concurrent edit or an inbound replicated change).

Re-read the note to obtain the current `ETag`, reconcile, and retry. Engram never
resolves a conflict for you (see [Deployment topologies](deployment.md)).

Errors use a consistent shape:

```json
{ "error": { "code": "not_found", "message": "No note at that path." } }
```

### Create a note

```bash
curl -X POST https://your-host/api/v1/notes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "title": "Meeting notes",
        "body": "# Sync\n- shipped the thing",
        "tags": ["work"],
        "idempotency_key": "2026-05-23-sync"
      }'
```

Repeating the same request with the same `idempotency_key` returns the existing
note instead of creating a duplicate.
