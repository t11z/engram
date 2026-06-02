# 0008. Wikilink and backlink graph model

- Status: accepted
- Date: 2026-06-02

## Context and problem statement

In v1 the note body "is never parsed for meaning" (`IMPLEMENTATION_PLAN.md` §3);
the SQLite FTS5 index stores text for ranked search only (`index.py`). A
convention-based vault (ADR-0007) is a *graph*: notes reference each other with
`[[wikilinks]]`, embed files with `![[...]]`, and carry inline `#tags`. The value
the major version promises — an MCP client and a companion UI that can follow
backlinks, list a note's neighbourhood, and render a local graph — requires Engram
to understand and store those relationships.

Walking and re-parsing the whole vault on every backlink or graph query does not
scale past a few hundred notes — the same reasoning that motivated the FTS index
(§5). We need a persistent, queryable representation of links and tags, and a rule
for keeping it true to the files.

## Considered options

- **Parse on demand.** Resolve links/tags by scanning files per query. Simple, no
  schema, but O(vault) per query and redundant with the existing index.
- **Extend the existing SQLite index** with `links` and `tags` tables, populated
  by the same write-through + reconciliation path that already maintains FTS rows.
- **A separate graph store** (e.g. an embedded graph DB). Adds a dependency and a
  second sync surface for no benefit at single-user scale.

## Decision

Add a wikilink/tag parser as a new `engram_core/links.py` module — kept distinct
from `link_extractor.py`, which fetches *remote URLs* (a different concern). It
parses `[[target]]`, `[[target|alias]]`, `[[target#heading]]`, `![[embed]]`,
standard Markdown links, and inline `#tags`, and unifies inline tags with
frontmatter tags.

Extend the SQLite index (`index.py`) with two tables:

- `links(src_path, dst_path, dst_raw, type)` — resolved edges plus the raw target
  for unresolved links.
- `tags(path, tag)` — one row per note/tag.

Links resolve to a target note using the portable "basename, then shortest
relative path" rule. Unresolved links are stored with `dst_path` null so the UI
can show them as dangling. Backlinks are `SELECT ... WHERE dst_path = ?`; the
local graph is a bounded traversal of `links`.

## Rationale

Reusing the index Engram already owns is the lowest-risk option: the write-through
and startup-reconciliation machinery that keeps FTS rows honest (§5) extends
naturally to link/tag rows, and the index stays a single disposable cache
rebuildable with `engram reindex`. A bespoke graph store would add a dependency
and a second consistency problem for query patterns (backlinks, one- or two-hop
neighbourhoods) that plain indexed SQL serves comfortably at single-user scale.
Parse-on-demand was rejected on the same performance grounds that justified the
index originally.

Storing unresolved links rather than dropping them preserves a real authoring
affordance — dangling links are how users stub future notes — and lets the graph
view and MCP tools report them.

## Consequences

- Reconciliation and reindex must parse links/tags, not just text; (re)indexing a
  note becomes slightly more expensive. The index remains disposable, so recovery
  is unchanged.
- Link resolution uses the path-based addressing of ADR-0007; a rename changes a
  note's path and therefore its edges — reconciliation re-resolves affected rows.
- New read paths over REST and MCP (backlinks, outgoing links, related, scoped
  graph; tag listing) build on these tables.
- Ambiguous targets (same basename in two folders) need a deterministic tiebreak;
  we follow the shortest-path convention and record the chosen target.
- Embeds (`![[...]]`) of non-note files connect to the attachments concern (a
  later ADR).
