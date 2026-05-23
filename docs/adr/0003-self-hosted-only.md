# 0003. Self-hosted only — no hosted demo, no multi-tenancy

- Status: accepted
- Date: 2026-05-23

## Context and problem statement

A knowledge vault holds personal, often sensitive data. We must decide the
project's hosting posture: whether to offer a hosted instance or demo, support
multiple tenants/accounts, or restrict the project to self-hosting by a single
user. This choice shapes the auth model, the data model, the privacy story, and
the maintenance burden.

## Considered options

- Self-hosted only: one user runs their own server; no accounts, no hosted
  instance.
- Offer a hosted demo instance (still self-hostable).
- Build for multi-tenancy from the start (accounts, per-user isolation).

## Decision

Self-hosted only. No hosted demo, no multi-tenancy, no accounts. One user, one
server, their own data. The server makes no outbound calls (no telemetry, no
update checks).

### Rationale

The project's value proposition is data ownership: your notes stay on your
machine. A hosted demo would require handling other people's data and the
operational/security burden that brings, contradicting the premise. Multi-tenancy
would add accounts, isolation, and auth complexity that a single-user tool does
not need. A single shared bearer token is sufficient when there is exactly one
user.

## Consequences

- Auth is a single bearer token shared by REST and MCP — no user table, no OAuth,
  no session management in v1.
- The data model has no tenant dimension; the vault is one directory of files.
- No demo to point newcomers at; the README and docs must make self-hosting easy
  enough to be the on-ramp (quick-start via docker-compose).
- The maintainer carries no operational responsibility for anyone's data.
- Should multi-user ever be wanted, it would be a major change with its own ADRs;
  it is explicitly out of scope for v1.
