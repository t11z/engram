# Contributing to Engram

Thanks for your interest. Engram is a small, single-maintainer project, so the
process is lightweight — but a few conventions keep it maintainable.

> New to the codebase? Read [`docs/IMPLEMENTATION_PLAN.md`](./docs/IMPLEMENTATION_PLAN.md)
> for the architecture, and [`CLAUDE.md`](./CLAUDE.md) for day-to-day working
> conventions.

## Issue-first

**Open an issue before you start work.** Every change — code or docs — should
trace to an issue, and your pull request must link it with `Closes #<issue>`.
This keeps the roadmap honest and avoids duplicated effort. (Trivial typo fixes
are the obvious exception, but when in doubt, file the issue.)

## Development environment

This is a monorepo with a Python backend and TypeScript/Svelte frontends.

- **Python** (`packages/core`, `apps/server`): managed with [uv](https://docs.astral.sh/uv/).
  ```bash
  uv sync
  ```
- **JavaScript/TypeScript** (`apps/extension`, `apps/web-ui`): managed with
  [pnpm](https://pnpm.io/) workspaces.
  ```bash
  pnpm install
  ```
- **Docs site**: MkDocs Material.
  ```bash
  pip install -r docs-site/requirements.txt
  mkdocs serve -f docs-site/mkdocs.yml
  ```

> During early development some of these directories may not exist yet — see the
> phased roadmap in the implementation plan. The CI workflow is written to skip
> jobs whose project isn't present yet.

## Running checks

Run the same checks CI runs before opening a PR:

```bash
# Python
uv run ruff check .
uv run mypy .
uv run pytest

# TypeScript / Svelte (per app)
pnpm -r lint
pnpm -r exec tsc --noEmit
pnpm -r test
```

## Coding style

- **Python**: formatted and linted by `ruff`; fully type-annotated and checked by
  `mypy`. No web-framework imports in `packages/core`.
- **TypeScript**: linted by `eslint`, type-checked by `tsc`.
- Keep `packages/core` the single source of truth for what a Note is; REST and
  MCP handlers stay thin.

## Test expectations

- New behavior comes with tests. Backend tests use the sample-vault fixture under
  `packages/core/tests/fixtures/`.
- Don't lower coverage to make a change land; fix the test or the code.

## Commit messages — Conventional Commits

This project uses [Conventional Commits](https://www.conventionalcommits.org/).
The release notes and CHANGELOG depend on it.

```
<type>(<optional scope>): <summary>
```

Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`.
Examples:

```
feat(server): add restore endpoint for trashed notes
fix(core): preserve frontmatter order on update
docs: clarify bearer token setup in quick start
```

## Pull request flow

1. Branch off `main`: `git checkout -b <type>/<short-description>`.
2. Make the change with tests; run the checks above.
3. **Update the contract** if you changed the REST API: regenerate the OpenAPI
   schema and TS types in `packages/contract` and commit them (CI fails on drift).
4. **Update `CHANGELOG.md`** under `[Unreleased]` for any user-visible change.
5. **Tick the roadmap.** If your PR completes a `- [ ]` item in
   `docs/IMPLEMENTATION_PLAN.md`, flip it to `- [x]` in the same PR.
6. Open the PR using the template; link the issue with `Closes #<issue>`.

## Be civil

Keep discussion respectful and on-topic. The maintainer may close or moderate
threads that become hostile or unproductive.
