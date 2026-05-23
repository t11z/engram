# API reference

!!! note "Hand-maintained for now"
    Until the server exists, this summary is maintained by hand. Once the server
    ships, the full reference will be generated from the committed OpenAPI schema
    in `packages/contract`.

All endpoints are under `/api/v1` and require `Authorization: Bearer <token>`
(except `/healthz`). Responses are JSON.

| Method & path | Purpose |
|---------------|---------|
| `POST /notes` | Create a note. Idempotent via `idempotency_key`. |
| `GET /notes` | List notes, newest first (`limit`, `cursor`, `tag`). |
| `GET /notes/{id}` | Read a note in full. |
| `DELETE /notes/{id}` | Soft-delete (move to `.trash/`). |
| `POST /notes/{id}/restore` | Restore a trashed note. |
| `GET /search` | Full-text search (`q` required). |
| `GET /trash` | List trashed notes. |
| `GET /healthz` | Liveness/readiness (no auth). |

Errors use a consistent shape:

```json
{ "error": { "code": "not_found", "message": "No note with that id." } }
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
