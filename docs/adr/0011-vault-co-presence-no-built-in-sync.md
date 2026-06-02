# 0011. Vault co-presence; no built-in sync

- Status: accepted
- Date: 2026-06-02

## Context and problem statement

The major version targets two deployment topologies: an always-on hub and a VPS,
with the user's local editor on separate devices. That raises the question the
design must answer: how do the Markdown files get from Engram's host to the
editor's device and back?

v1 already drew a line here. Git-backing of the vault is "out of scope"; a user who
wants history runs `git init` themselves, and "startup reconciliation absorbs
out-of-band changes" (`IMPLEMENTATION_PLAN.md` §5). Engram makes no outbound calls
and runs as one process against one directory (ADR-0002, ADR-0003). Nothing in
that model moves files between machines.

We must state, as a decision of record, whether Engram takes on cross-host
synchronisation or continues to assume the vault directory is simply *present* on
its host — and if the latter, what Engram must do to be correct when files appear
or change underneath it.

## Considered options

- **Build cross-host sync into Engram** (its own replication, or a managed git
  auto-commit/pull loop). Batteries-included, but a large, stateful, conflict-prone
  subsystem that duplicates mature tools and contradicts the self-hosted-minimal,
  no-outbound posture.
- **An editor-side sync plugin** that shuttles notes over Engram's API.
  Reintroduces two sources of truth, misuses a request/response API as a
  replication protocol, and makes one editor load-bearing for the core value —
  rejected at planning.
- **Co-presence: Engram stays sync-agnostic.** The vault directory is made
  co-present on Engram's host by a user-chosen mechanism (same machine; or
  Syncthing/iCloud/Dropbox/git; or a hub that also runs an editor client with that
  editor's own sync). Engram only reads/writes the local directory and makes itself
  robust to external change.

## Decision

Engram does **not** implement cross-host synchronisation. It assumes the vault
directory is co-present on its host, replicated by a user-chosen, Engram-external
mechanism. Engram's responsibility is to remain correct under external change, via
three properties:

- **Live reconciliation** — a filesystem watcher reconciles the index/graph during
  operation, not only at startup, so replicated changes are reflected promptly.
- **Conflict-file tolerance** — files created by sync tools (e.g.
  `... (conflicted copy).md`, `.sync-conflict-...`) are indexed harmlessly rather
  than crashing or corrupting state.
- **Optimistic concurrency** on writes (ADR-0009), so an Engram write and an
  inbound replicated change cannot silently overwrite each other.

## Rationale

Synchronisation is a hard, well-solved problem; the tools users already run
(Syncthing, git, an editor's own sync) handle deltas, conflicts, binaries, and
offline edits far better than anything we would bolt on, and building it would
contradict ADR-0003's self-hosted-minimal stance and the no-outbound posture. The
editor-plugin route was rejected because it recreates the two-sources-of-truth
problem the shared-vault design (ADR-0007) exists to avoid and couples Engram to a
single editor, against the editor-neutral posture.

Co-presence keeps Engram a lens on one directory (consistent with ADR-0002/0003
and §5's existing git stance) and concentrates the real work where it belongs:
being unfalteringly correct when the directory changes beneath it. That is an
extension of machinery v1 already has (startup reconciliation), not a new
subsystem.

## Consequences

- v2 must add a filesystem watcher and make reconciliation incremental rather than
  startup-only; this is required work, not optional, because both target topologies
  are remote and replicated.
- The index/parser must treat unexpected files (conflict copies, editor temp files)
  defensively.
- Documentation must explain the topologies with concrete recipes (hub; VPS +
  Syncthing/git) and state plainly that Engram does not sync — setting expectations
  is part of the decision.
- Engram never resolves a sync conflict; it stays consistent and surfaces conflicts
  (ADR-0009's `409`, and by listing conflict files). Resolution is the replication
  tool's or the user's job.
- If first-class history/sync is ever wanted, it returns as its own ADR (as §5
  already anticipated for git); this ADR records why it is deliberately absent now.
