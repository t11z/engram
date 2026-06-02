# 0009. In-place editing and optimistic concurrency

- Status: accepted
- Date: 2026-06-02

## Context and problem statement

v1 is write-once-shaped: `POST /notes` creates, `DELETE` soft-deletes, restore
restores; there is no update path, and the five MCP tools likewise only
create/read/list/delete. The major version requires an MCP client and the web UI
to *edit* existing notes — append to a note, replace a section, set
tags/frontmatter, append to a daily note — and the UI gains a light editor.

This collides with a v1 assumption recorded as a risk: "single-user; serialize
writes in `VaultStore`; last-writer-wins via `updated_at`"
(`IMPLEMENTATION_PLAN.md` §9). Under ADR-0007/ADR-0011 the same vault is now edited
concurrently from at least two directions — Engram (UI or MCP) and the user's
local editor, whose changes arrive via file replication. Blind last-writer-wins
would let an Engram write silently clobber a note the user just changed elsewhere,
and vice versa.

A second question follows from *how* we detect "the file changed underneath me".
File-replication tools (Syncthing, cloud drives, a `git checkout`) routinely
rewrite a file's `mtime` without changing its content, and can also restore
content while leaving timestamps coarse or unchanged. So the change signal used for
concurrency control has to reflect the bytes, not the metadata.

## Considered options

- **Keep last-writer-wins.** Simplest; accepts silent data loss on concurrent
  edits. Tolerable for single-writer v1, not for a concurrently-edited shared vault.
- **Pessimistic locking.** Lock a note for editing. Meaningless across a
  file-replication boundary where the other writer (the local editor) never asks
  Engram for a lock.
- **Optimistic concurrency.** Every read exposes a version token; writes must
  present the token they based their edit on, and the server refuses with a
  conflict if the file changed underneath. The token can be derived from `mtime`
  or from a content hash.

## Decision

Add editing to the service layer and expose it over REST and MCP:

- REST: `PUT/PATCH /notes/{path}` and structured edits, carrying an `If-Match`
  precondition.
- MCP: `update_note`, `append_to_note`, `patch_section` (replace by heading),
  `append_to_daily_note`, `set_tags`, `set_frontmatter`.

All whole-note writes use **optimistic concurrency with a content-hash token**: a
read returns an ETag that is a hash of the file's bytes; a write supplies the ETag
it edited from; if the current file hashes differently, the write fails with a
`409`-class conflict instead of overwriting. Append-style operations
(`append_to_note`, `append_to_daily_note`) are retry-safe and may
re-read-and-append rather than hard-fail.

The hash is cached in the index, keyed by `(path, mtime, size)`, and recomputed
only when those change. Reconciliation keeps using the cheap `mtime`/`size` signal
to decide *what* to re-read (ADR-0008, §5); the hash is the comparison token for
*writes*, not a startup-time full-vault rehash.

## Rationale

Optimistic concurrency is the only option that protects a vault edited from
outside Engram's control: pessimistic locking cannot reach the local editor, which
writes files directly, and last-writer-wins is exactly the silent-loss behaviour
we can no longer accept once a second writer is normal rather than a risk.

The token is a content hash rather than `mtime` because the writers we must
tolerate are replication tools that treat timestamps as disposable. An `mtime`
token would raise false conflicts every time a sync touched a file without
changing it (merely annoying) and — worse — could miss a real change that arrived
with an unchanged or coarsely-rounded timestamp, reintroducing the silent clobber
we are trying to prevent. Hashing the bytes compares what actually matters. The
cost is bounded by caching the hash against `(path, mtime, size)`, so unchanged
files are never rehashed and startup stays as cheap as today.

Distinguishing whole-note writes (precondition-guarded) from appends (retry-safe)
matches real usage: an agent appending a finding to the daily note should not fail
because the file moved on; an agent rewriting a note's body should.

## Consequences

- Reads must surface the ETag; the contract (`packages/contract`) and schemas grow
  an ETag field, and clients (web UI, future thin clients) must echo it on write.
- `VaultStore` write paths gain a hash-compare-then-write step; the index gains a
  cached content-hash column keyed by `(path, mtime, size)`. The existing
  single-process write serialization still applies within Engram.
- Conflict is a first-class API outcome: the web UI's light editor must handle
  `409` (reload/merge prompt) rather than assume success.
- Addressing is path-based (ADR-0007); `If-Match` rides alongside the path handle,
  and the optional `id` alias is independently resolvable.
- Structured edits (`patch_section`) require locating a heading in the body; this
  reuses the body parsing introduced for ADR-0008.
- This does not implement merge/conflict resolution — Engram reports the conflict
  and stays consistent; resolving it is the user's or the replication tool's job
  (see ADR-0011).
