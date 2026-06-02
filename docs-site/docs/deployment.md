# Deployment topologies

Engram is a lens onto one vault directory. It does **not** synchronise that
directory between machines: it reads and writes only the local filesystem and
makes no outbound calls ([ADR-0011](https://github.com/t11z/engram/blob/main/docs/adr/0011-vault-co-presence-no-built-in-sync.md)).
For Engram to serve your notes, the vault directory must be **co-present on
Engram's host** — either because it lives on the same machine you edit on, or
because a tool you choose keeps a copy of it there.

Replication is handled by mature, general-purpose tools that already solve
deltas, conflicts, binaries, and offline edits well — Syncthing, git, an editor's
own sync, or a cloud-sync folder. Engram's job is to stay correct while that
directory changes underneath it:

- A **live filesystem watcher** reconciles the search index and link graph during
  operation, not only at startup, so replicated changes appear promptly. It is
  debounced (`ENGRAM_WATCH_DEBOUNCE_SECONDS`) and can be turned off (`ENGRAM_WATCH`).
- **Sync conflict copies** (e.g. `note (conflicted copy).md`, `.sync-conflict-…`)
  are indexed harmlessly rather than crashing or corrupting state.
- **Optimistic concurrency** on writes (a content-hash `ETag` with `If-Match`)
  means an Engram write and an inbound replicated change cannot silently
  overwrite each other.

!!! note "Conflict resolution is not Engram's job"
    Engram never resolves a sync conflict. It stays consistent and surfaces the
    conflict — a `409` on a stale write, and by listing conflict files — and
    leaves resolution to your sync tool or to you ([ADR-0011](https://github.com/t11z/engram/blob/main/docs/adr/0011-vault-co-presence-no-built-in-sync.md)).

The two topologies below are the common shapes. Both keep the vault co-present
with Engram by a means of your choosing.

## Topology A — Always-on hub

Run Engram on a machine that is always on and that already holds (or can hold) a
fresh copy of the vault: a home server, a NAS, or a small always-on Mac mini /
mini-PC. Your editing devices reach Engram (and your LLM clients reach `/mcp`)
over your network or a reverse proxy.

To keep the hub's copy of the vault fresh, run a sync mechanism **on the hub**.
A convenient option is to run an ordinary Markdown editor client on the hub and
let that editor's own sync keep the folder current; the vault is then co-present
with Engram, edited from your other devices, and reconciled live by the watcher.

```text
[ phone / laptop editor ] --(editor's own sync or Syncthing)--> [ hub vault dir ]
                                                                       |
                                                            [ Engram reads/writes ]
                                                                       |
                                              REST + /mcp <----- LLM clients, web UI, extension
```

Recipe:

1. Install Engram on the hub (see [Installation](installation.md)); point
   `ENGRAM_VAULT_PATH` at the shared vault directory.
2. Keep that directory fresh on the hub with a sync tool of your choice (an
   editor client running on the hub with its own sync, Syncthing, a cloud-sync
   folder, or a scheduled `git pull`).
3. Leave `ENGRAM_WATCH=true` (the default) so Engram reconciles inbound changes
   live.

## Topology B — VPS + neutral file sync

Run Engram on a VPS and replicate the vault directory between the VPS and your
devices with a neutral, editor-agnostic sync tool. **Syncthing** and **git** are
the natural fits because neither requires a third-party cloud account and both
run anywhere.

```text
[ device A vault ] <---\
                        >--(Syncthing / git)--> [ VPS vault dir ] --> [ Engram ]
[ device B vault ] <---/                                                  |
                                                    REST + /mcp <----- LLM clients
```

Recipe (Syncthing):

1. Install Syncthing on the VPS and on each editing device; share the vault
   folder between them.
2. Point `ENGRAM_VAULT_PATH` at the VPS-side folder Syncthing maintains.
3. Terminate TLS at a reverse proxy (see the Caddy example in `infra/`) so MCP
   clients and the web UI reach the VPS over HTTPS.

Recipe (git):

1. Host the vault as a git repo (any remote you control).
2. On the VPS, clone it to `ENGRAM_VAULT_PATH` and pull on a schedule (cron /
   systemd timer); commit and push from your devices as you edit.
3. The watcher reconciles each pull; commit your work before pulling to avoid
   creating merge conflicts the way you would in any git workflow.

In both topologies, replication and conflict resolution are the sync tool's (and
ultimately your) responsibility; Engram simply stays consistent with whatever is
on disk.
