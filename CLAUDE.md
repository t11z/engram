# CLAUDE.md — repo-wide working manual

How to work in this repository. **Architecture is not here** — it lives in
[`docs/IMPLEMENTATION_PLAN.md`](./docs/IMPLEMENTATION_PLAN.md); individual
decisions live in [`docs/adr/`](./docs/adr/). This file is the working manual.

## Working loop (issue-first)

No file changes without a tracking issue. The loop:

1. **Create a GitHub issue** for the change.
2. **Record it** so the local guard passes:
   `echo "<issue-url-or-number>" > .claude/state/active-issue`
   (or `export ENGRAM_ACTIVE_ISSUE=<issue>`).
3. **Branch**: `git checkout -b <type>/<short-description>`.
4. **Implement** with tests; run the checks below.
5. **Open the PR** with `Closes #<issue>` in the body.

A `PreToolUse` hook (`.claude/hooks/require-issue.sh`, wired in
`.claude/settings.json`) blocks edits when no active issue is recorded; edits
under `.claude/` are exempt so the marker can always be written. CI enforces the
same rule on PRs via the `require-linked-issue` job.

## Branch & commit conventions

- Branches: `feat/…`, `fix/…`, `docs/…`, `chore/…`, `ci/…`, `refactor/…`.
- Commits: [Conventional Commits](https://www.conventionalcommits.org/) —
  `feat(server): add restore endpoint`. Release notes depend on it.
- Repository language is **English** (code, comments, docs, commits).

## Running tests across the monorepo

```bash
# Python (packages/core, apps/server)
uv run ruff check . && uv run mypy . && uv run pytest

# TS / Svelte (apps/extension, apps/web-ui)
pnpm -r lint && pnpm -r exec tsc --noEmit && pnpm -r test
```

Early on, some packages don't exist yet; run only what's present. CI skips jobs
whose project files are absent.

## Local dev loop (server + ui + extension)

- **Server** against the sample vault:
  `ENGRAM_VAULT_PATH=packages/core/tests/fixtures/sample-vault ENGRAM_AUTH_TOKEN=dev uv run engram` (see `apps/server/CLAUDE.md`).
- **Web UI**: `pnpm --filter web-ui dev`, proxying the API to the server.
- **Extension**: build, then load unpacked (see `apps/extension/CLAUDE.md`).

## When to update what

- **Release notes** — there is no hand-maintained changelog. GitHub Releases are
  the source of truth; their notes are auto-generated from merged PRs when a
  `v*.*.*` tag is pushed, so write a clear Conventional-Commit PR title.
- **Contracts** (`packages/contract`) — whenever the REST API changes:
  regenerate the OpenAPI schema + TS types and **commit them**. CI fails on drift.
- **API version** (`/api/v1`) — only for breaking REST changes; additive changes
  stay in v1.
- **Roadmap** — if a PR completes a `- [ ]` item in `docs/IMPLEMENTATION_PLAN.md`,
  flip it to `- [x]` in that PR.
- **ADRs** — add `docs/adr/NNNN-title.md` (copy `docs/adr/template.md`) for any
  decision with non-trivial trade-offs. Don't restate architecture in CLAUDE.md.

## Pointers

- Architecture & roadmap → [`docs/IMPLEMENTATION_PLAN.md`](./docs/IMPLEMENTATION_PLAN.md)
- Decisions → [`docs/adr/`](./docs/adr/)
- Server specifics → [`apps/server/CLAUDE.md`](./apps/server/CLAUDE.md)
- Extension specifics → [`apps/extension/CLAUDE.md`](./apps/extension/CLAUDE.md)
