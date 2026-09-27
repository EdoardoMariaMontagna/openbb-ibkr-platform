# Security Policy

This platform connects to a real brokerage account (Interactive Brokers)
and, in read-write mode, can place real orders. Security reports are taken
seriously, and this policy is written to be consistent with the project's
[AGPL-3.0 license](LICENSE): security is not a paid feature, and no fork or
sponsor gets a fix before the public release does.

## Supported Versions

This project is pre-1.0 (`0.x`). Only the latest commit on `main` is
supported — there are no maintained release branches yet. Always run the
latest `main` if you depend on this project for anything that touches real
money.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for a security vulnerability.**

Use GitHub's private vulnerability reporting instead: go to the
[Security tab](../../security/advisories) of this repository and click
**"Report a vulnerability."** This opens a private advisory visible only to
you and the maintainers — nothing is public until a fix is ready and everyone
agrees to disclose.

(If that option isn't visible — GitHub only enables it for free on public
repositories — please open a regular issue asking a maintainer to enable it,
without describing the vulnerability itself, or reach out through any other
contact channel the maintainers have listed on their GitHub profile.)

Please include:

- A description of the vulnerability and its impact.
- Steps to reproduce it (a minimal example is very helpful).
- Which component is affected — e.g. IBKR order placement (`/ibkr/order`),
  the API-key check (`security.py`), the audit trail (`audit.py`), CORS
  handling, or an upstream dependency (OpenBB, `ib_async`, FastAPI/Starlette).

## Severity: what counts as critical here

Because this platform can place real orders, **any vulnerability that
bypasses the order-placement guards is treated as critical regardless of how
hard it is to exploit**. That specifically includes anything that lets a
request:

- Place, modify, or cancel an order without a valid `X-API-Key` (when one is
  configured).
- Place an order while `IBKR_READONLY=true`, or without the request's
  `confirm: true` flag.
- Read live IBKR account/portfolio data without a valid API key.
- Escape the audit trail — an order that is placed or attempted without a
  corresponding record in `OBB_IBKR_AUDIT_LOG`.

Vulnerabilities confined to read-only OpenBB market-data endpoints (no IBKR
account exposure, no auth bypass) are still valued but are not automatically
critical.

## Response Process

This is a community-maintained project without a dedicated security team, so
response times are best-effort, not a contractual SLA:

- **Acknowledgment:** target within 5 business days of a report.
- **Triage:** we'll confirm whether it's in scope and its severity, and keep
  you updated as we work on a fix.
- **Fix and disclosure timeline:** we ask for up to 90 days from
  acknowledgment before public disclosure, to give users time to update once
  a fix ships. We'll work with you if more or less time is warranted given
  severity and complexity.

## Disclosure Policy

This is the part that matters for staying true to the license:

- When a fix is ready, it is released as an ordinary AGPL-3.0 update to this
  repository's `main` branch — **published to everyone at the same moment**.
  There is no private patch, no early-access branch for sponsors, and no
  "enterprise" fork that receives it first. Anyone running this software,
  free of charge, gets the fix at the same time as anyone else.
- After the fix ships (or the 90-day window elapses, whichever comes first),
  details are published as a public GitHub Security Advisory, crediting the
  reporter — unless they'd rather stay anonymous, which we'll always honor.
- We won't pursue legal action against good-faith security research
  conducted under this policy (no unauthorized access to other users' real
  accounts or data, no service disruption, and a genuine attempt at private
  disclosure first).
- There is no bug bounty — this is a personal/community project — but every
  reporter is credited in the advisory and in this file's history unless they
  ask not to be.

## Out of Scope

- Reports that assume the operator already ignored the documented safety
  posture — e.g. running with `IBKR_READONLY=false` and no `OBB_IBKR_API_KEY`
  on a network-exposed deployment. That configuration is explicitly called
  out as dangerous in the README; if you find a *new* way it can go wrong,
  that's still worth reporting.
- Vulnerabilities that require local, unauthenticated access to a machine
  that already has an unlocked, logged-in TWS/IB Gateway session — that's a
  compromise of the underlying OS, not of this project.
- Vulnerabilities purely in upstream dependencies (OpenBB Platform,
  `ib_async`, FastAPI/Starlette, etc.) with no project-specific twist —
  please report those upstream. Feel free to also flag them here if they
  materially affect this project's *default* configuration, so we can track
  or mitigate on our side while upstream fixes land.
