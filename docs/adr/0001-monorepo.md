# 0001. Single monorepo for all components

- Status: accepted
- Date: 2026-05-23

## Context and problem statement

Engram ships several components that must move together: a Python core library,
a FastAPI server, a SvelteKit web UI, a browser extension, and a generated
API contract shared between server and clients. We need to decide whether these
live in one repository or several. The contract in particular couples the server
to the clients: the OpenAPI schema and generated TypeScript types must stay in
lockstep.

## Considered options

- One monorepo containing all components.
- One repo per component (polyrepo), with the contract published as a package.
- A hybrid (server + core together, clients separate).

## Decision

Use a single public monorepo containing `packages/` and `apps/`.

### Rationale

The components are developed by one maintainer and released as a set. A monorepo
lets a single PR change the REST API and its generated client types atomically,
and lets CI fail on contract drift in one place. Polyrepo would add cross-repo
version coordination and publishing overhead that buys nothing at this project's
scale.

## Consequences

- One CI pipeline, one issue tracker, one release cadence; atomic cross-component
  changes.
- Generated contract artifacts are committed once and consumed locally by clients
  with no cross-repo publishing.
- The repo mixes Python and JS toolchains; CI must run both and skip cleanly when
  a given project isn't present yet.
- If a component ever needs an independent release cadence, it can be extracted
  later — this decision is not hard to reverse.
