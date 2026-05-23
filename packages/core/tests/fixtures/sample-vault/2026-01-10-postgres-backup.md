---
id: 01KSB998H8WTTDZCMR8C67KBR7
title: Postgres backup command
created_at: '2026-01-10T08:30:00Z'
updated_at: '2026-01-10T08:30:00Z'
tags:
- ops
- postgres
source_url: https://example.com/postgres-backup
idempotency_key: seed-postgres-backup
---

Run a nightly logical backup of the primary Postgres database:

```
pg_dump --format=custom --file=/backups/db.dump mydb
```

Restore with `pg_restore`. Keep at least seven daily backups.
