# 0010. MCP resources and prompts

- Status: accepted
- Date: 2026-06-02

## Context and problem statement

Engram exposes the vault to MCP clients as five *tools* only (`mcp_server.py`;
`IMPLEMENTATION_PLAN.md` §4). The MCP spec also defines **resources** (addressable,
readable content a client can attach as context) and **prompts** (server-supplied,
parameterised templates). For a vault whose whole point is to be the user's
memory, exposing notes only through tool calls is a thin use of the protocol: a
client cannot browse or attach a note as a first-class context resource, and every
client re-invents the same "summarise / find-related / review" prompting by hand.

The major version's goal is to be *the* universal MCP interface onto the vault.
That argues for using more of the protocol surface — provided it stays a thin
layer over the same service layer (ADR-0002) and adds no new write semantics of
its own.

## Considered options

- **Tools only (status quo).** Keep tools (plus the new graph/edit/structure
  tools), stop there. Lowest effort; leaves resources/prompts unused.
- **Tools + resources.** Additionally expose notes (and folders) as MCP resources
  via templates, so clients can read/attach a note by a stable URI.
- **Tools + resources + prompts.** Also ship a small set of server-defined prompts
  that operate over the vault.

## Decision

Expose the vault as MCP **resources** and ship a curated set of MCP **prompts**, in
addition to the expanded tool set:

- Resources via templates, e.g. `engram://note/{path}` for a note plus a
  folder/listing resource, resolved through the same service layer as the tools.
- A small, curated prompt set (e.g. `summarize-note`, `find-related`,
  `daily-review`) parameterised by note id/path or tag.

These are read-oriented or compose existing tools; they introduce no storage
behaviour beyond ADR-0008/ADR-0009.

## Rationale

Resources are the natural representation for "a note as context": they let a
client attach a note directly rather than scripting a `read_note` call — what
users actually want from a memory vault. Prompts move the few obvious, repeatable
vault workflows from every client into one tested place, raising baseline quality
for any MCP client without coupling to a specific one. Both are additive and thin
over the existing service layer, fitting ADR-0002 and the LLM-agnostic posture;
the only real cost is MCP SDK/spec churn, already a logged risk (§9) mitigated by
pinning and thin handlers.

## Consequences

- The MCP surface grows beyond tools; `mcp_server.py` (FastMCP setup) must register
  resource templates and prompts, and tests should cover them (MCP Inspector path,
  as for tools).
- Resource URIs are a small contract of their own; they use the path-based
  addressing that is now the vault's native model (ADR-0007), so a note's URI
  changes when it is renamed — the optional `id` alias is available where a stable
  URI is needed.
- Prompts are opinionated content needing maintenance discipline; we keep the set
  small and English (repo language), with descriptions written for LLM consumption
  like the tool descriptions.
- No new auth surface: resources and prompts ride the same bearer/OAuth path as the
  existing MCP endpoint (ADR-0004).
