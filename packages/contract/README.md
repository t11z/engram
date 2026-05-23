# Bartleby API contract

Generated artifacts — **do not hand-edit**. They are committed so the browser
extension and web UI can consume the API types without running Python.

- `openapi.json` — the FastAPI OpenAPI schema, exported canonically (sorted keys).
- `types.ts` — TypeScript types generated from `openapi.json`.

## Regenerate

```bash
uv run bartleby-export-openapi packages/contract/openapi.json
pnpm exec openapi-typescript packages/contract/openapi.json -o packages/contract/types.ts
```

CI (`contract-drift`) runs exactly these and fails if the result differs from
what is committed. Regenerate and commit whenever the REST API changes.
