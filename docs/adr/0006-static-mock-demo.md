# 0006. Static mock-data demo of the web UI on GitHub Pages

- Status: accepted
- Date: 2026-05-31

## Context and problem statement

[ADR-0003](./0003-self-hosted-only.md) rules out a *hosted demo*: we will not run
a server that holds other people's data, and a consequence we accepted there was
"no demo to point newcomers at." In practice that makes the project hard to
evaluate — the only way to see the web UI is to install Docker, set a token, and
run the server. We want a low-friction way for someone to see the interface
without that, while keeping the privacy posture of ADR-0003 intact.

The web UI is already a static SvelteKit SPA (`@sveltejs/adapter-static`) whose
only server dependency is the `/api/v1` REST API. The docs site is already
published to GitHub Pages by `pages.yml`. GitHub allows only **one** published
Pages site per repository.

## Considered options

- **No demo** (status quo): keep ADR-0003's consequence; the README screenshot is
  the only preview.
- **Hosted backend demo:** run a real Engram server somewhere. Directly
  contradicts ADR-0003 (someone's server, operational and data-handling burden).
- **Static client-only demo:** build the existing UI with an in-memory mock API
  and curated sample data, served as a sub-path of the existing Pages site.
- **Separate repo for the demo:** its own Pages site at `engram-demo`. A second
  repo to keep in sync for no real benefit.

## Decision

Ship a **static, client-only demo** of the web UI, published under `/demo` on the
existing Pages site (`https://t11z.github.io/engram/demo/`). It is built with
`VITE_ENGRAM_DEMO=1`, which swaps the API client for an in-memory mock store
seeded from a curated, deliberately harmless sample dataset. The demo is fully
interactive (browse, search, delete→trash, restore) but holds no real data, talks
to no backend, and resets on reload. `pages.yml` builds it alongside the docs and
places it in the combined Pages artifact.

### Rationale

This refines ADR-0003 rather than reversing it. The thing ADR-0003 forbids is a
*hosted backend* that handles real user data; a static bundle of HTML/JS with
fake data carries none of that burden — no accounts, no multi-tenancy, no server,
no outbound calls. It runs entirely in the visitor's browser. Reusing the real UI
(not a mock-up) keeps the demo honest and free, and a sub-path avoids a second
repository since GitHub permits only one Pages site per repo.

## Consequences

- Newcomers can try the actual UI in one click; the README links to the demo in
  place of the former static screenshot.
- The UI gained a build-time `DEMO` switch and a base-path option
  (`ENGRAM_BASE_PATH`) so it can be served from a sub-path; normal server-hosted
  builds are unaffected (empty base, real `/api/v1`).
- A small amount of demo-only code ships in the repo (mock API, sample dataset,
  demo banner) and the sample data must stay neutral and non-sensitive.
- The demo can drift from the real API surface; it is covered by unit tests and
  rebuilt on every UI change, but it is not a substitute for running the server.
- ADR-0003 still holds for any *backend* hosting; this ADR narrows its "no demo"
  consequence to "no hosted backend demo."
