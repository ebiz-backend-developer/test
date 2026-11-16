# Integrations & Reports — Plan (supporting notes)

The runnable implementation is the source of truth: the same scope, roles,
modules, tech stack, and milestones below are seeded in
[002_seed.sql](/data/workspaces/rouvr__7__a4/app/migrations/002_seed.sql) and served by the
`/api/v1/planning/*` endpoints.

## c1 — Scope and user roles

In scope (MVP): card/bank payment intents with confirm/refund lifecycle;
transactional SMS/email with templates and a delivery log; analytics event
ingest with revenue/usage aggregates; compliance reports (transactions,
refunds, notifications, access audit, daily revenue) as audited CSV/JSON
exports; operator dashboard.

Out of scope (MVP): in-person/terminal payments, marketing bulk sends,
regulator e-filing, live PSP/messaging adapters (provider interfaces ship
now; adapters follow in M4).

Roles: `admin` (full access, milestone approval), `finance` (payments ops +
financial reports), `support` (payment lookup + notifications), `auditor`
(read-only compliance + report runs), `developer` (analytics, templates,
planning proposals), `user` (own payments only). Enforced per-endpoint; see
[auth.py](/data/workspaces/rouvr__7__a4/app/auth.py).

## c2 — Core modules and MVP prioritized

P0 (MVP): `payments`, `notifications`, `reports`.
P1 (MVP): `analytics`, `planning`, `dashboard-ui`.
P2 (post-MVP): `real-psp-adapters`, `scheduled-reports`.

## c3 — Architecture and tech stack

Python 3.12, FastAPI + Pydantic v2, SQLite (WAL) with versioned SQL
migrations, API-key RBAC, provider interfaces with mock PSP/messaging
adapters, synchronous audited report runs. Decisions recorded in
`tech_decisions` and `GET /api/v1/planning/tech`.

## c4 — Delivery milestones

M1 payments+notifications MVP → M2 analytics+reports → M3 dashboard+RBAC →
M4 live adapters. Milestones move `proposed → approved → done`; approval is
an admin-only audited API call (`POST /api/v1/planning/milestones/{id}/approve`).
