# 0007. Convention-based vault model

- Status: accepted
- Date: 2026-06-02

## Context and problem statement

Engram v1 is opinionated about how a note is stored. `VaultStore` injects a ULID
into every note's frontmatter, derives a `YYYY-MM-DD-<slug>.md` filename, keeps
the vault flat, requires `title`/`created_at`/`updated_at` in frontmatter, and
never parses the body for meaning (`IMPLEMENTATION_PLAN.md` §3, §5). These choices
are coherent for a vault that Engram alone owns and writes.

The next major version repositions Engram as a universal MCP gateway and companion
web client onto a vault the user curates with a local Markdown editor. Such vaults
follow widely-used portable conventions Engram currently ignores or fights:
arbitrary nested folders, free-form filenames, `[[wikilinks]]` and `![[embeds]]`,
inline `#tags` alongside frontmatter tags, an attachments folder, and frontmatter
that is minimal or absent rather than a fixed required set.

There are two ways to support this. One is to bolt portable handling on as an
alternate *mode* beside the v1 behaviour, selected by configuration. The other is
to make portable conventions the single native model. A mode switch is a
permanent tax in exactly the place that should stay simplest: two code paths
through `VaultStore`, identity, and naming; two test matrices; a configuration
axis that can be set wrong; and an identity rule that differs by mode. Engram is
editor-agnostic, and "the filesystem is the source of truth" — that posture is
most honestly expressed by reading the vault as it is found, not by imposing a
shape and offering a mode to relax it.

## Considered options

- **Dual mode.** Keep v1 behaviour as one profile; add a portable profile;
  toggle by configuration.
- **Single convention-based model.** Portable conventions are the native model.
  v1's opinionated behaviours (auto id, dated filenames) survive only as optional
  defaults at note-creation time, not as a separate mode.
- **Adapter/bridge** between an external vault and an Engram-shaped vault.
  (Rejected at planning: two sources of truth, drift.)

## Decision

Adopt a single convention-based vault model:

- A note is any `.md` file at any depth. The **vault-relative path is its
  canonical handle.**
- **Frontmatter is minimal and optional.** `title` comes from frontmatter, else
  the first H1, else the filename. `created_at`/`updated_at` come from frontmatter
  when present, else from filesystem timestamps. `tags` is the union of
  frontmatter `tags` and inline `#tags`. `source_url`, `idempotency_key`, and an
  optional `id` are honoured when present.
- **`id` (ULID) is an optional stable alias:** honoured for lookup when present,
  never force-injected into notes Engram did not create. Engram-created notes may
  carry one (configurable, default off) for clients that want a rename-stable
  handle.
- The body is parsed for `[[wikilinks]]`, `![[embeds]]`, inline `#tags`, and
  Markdown links (ADR-0008).
- **No forced filename or layout.** Engram-created notes default to
  `<sanitized-title>.md` in a configurable new-note folder.
- There is **no `vault_profile` switch.**

## Rationale

One model is simpler and more honest than a mode switch. A single path through
`VaultStore`, identity, and naming is easier to reason about and test, removes a
configuration axis that can be misconfigured, and yields one identity rule (path,
with an optional stable `id`) instead of one rule per mode. Making frontmatter
optional-with-derivation rather than a required set matches how portable notes are
actually written, and lets Engram coexist with hand-authored and tool-authored
notes without rewriting them — the decisive property for a vault Engram shares
rather than owns. The opinionated v1 conveniences lose nothing essential by
becoming creation-time defaults instead of a mode.

Path-primary addressing with an optional `id` alias is the right default for this
model: it is how the vault already addresses itself (wikilinks resolve by
name/path), while the optional `id` preserves the rename-stable identity v1 valued
(§3) for any client that wants it.

## Consequences

- Identity/addressing shifts from ULID-primary to path-primary with an optional
  `id` alias; `models.py`, `store.py`, `ids.py`, and REST/MCP addressing must
  accept a path handle and encode it in routes and resource URIs (ties into
  ADR-0009 version tokens and ADR-0010 resource URIs). A rename changes a note's
  path-handle; `id` is the stable escape hatch.
- `slug.py`'s forced date-slug naming is retired as an invariant; it survives only
  as one possible creation-time default.
- Required-frontmatter assumptions relax to optional-with-derivation;
  `Note`/`NoteSummary`/`NoteCreate` change shape, and the contract
  (`packages/contract`) regenerates.
- One code path and one `portable-vault` test fixture, instead of two of each.
- Existing vault data stays valid under this model — present `id`s are honoured
  and arbitrary filenames are fine — so adopting it is a change in how Engram
  *writes*, not a data migration of what is already stored.
- This ADR fixes the model only; graph (ADR-0008), editing/concurrency
  (ADR-0009), MCP resources/prompts (ADR-0010), and co-presence/sync (ADR-0011)
  build on it.
