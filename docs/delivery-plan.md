# Delivery plan (Task 8) — served live by the app, summarized here

This file mirrors the seeded plan in [seed.py](/data/workspaces/rouvr__8__a3/delivery/seed.py).
The running server is the source of truth: open the dashboard or
`GET /api/v1/roadmap`.

## Scope & roles (c1)

Vision: ship a shippable delivery-milestones product — scoped MVP, selected
tech stack, phased timeline with risks tracked and milestones formally approved.

In scope: scope/roles management, module registry with MVP prioritization,
tech-stack decision log, phased milestones with timeline/risks/criteria,
approval workflow with readiness gates, dashboard UI + REST API on one SQLite store.
Out of scope: multi-tenant orgs/SSO, deployment pipelines, mobile clients, billing.

Roles: `admin` (full access), `product_owner` (scope, MVP priority, approvals),
`tech_lead` (architecture, execution status), `developer` (progress updates),
`stakeholder` (read-only). Enforced per endpoint via the `X-Role` header.

## Core modules & MVP (c2)

MVP slice (P0): scope-roles, module-registry, arch-log, milestone-api,
approval-workflow, dashboard-ui; plus risk-register (P1). Post-MVP: reporting-export,
notifications. Priorities P0/P1/P2 with dependency checks; `GET /api/v1/mvp` rolls up
points and done counts.

## Architecture & tech stack (c3)

Selected: Python 3.12 standard library only, SQLite + versioned migrations,
REST + JSON over stdlib `http.server`, server-served static page + vanilla JS,
`unittest` for tests. One selected option per category; rejections recorded with
rationale (e.g. Node.js unavailable here, Postgres kept as a proposed candidate).

## Phases, timeline, risks, acceptance (c4)

| Milestone | Phase | Timeline | Entry state |
|---|---|---|---|
| M1 Discovery & scope sign-off | discovery | 2026-11-16 → 2026-11-23 | approved (seeded) |
| M2 MVP backend | mvp | 2026-11-24 → 2026-12-05 | in progress |
| M3 MVP UI & approvals live | mvp | 2026-12-06 → 2026-12-19 | planned |
| M4 Beta hardening | beta | 2027-01-04 → 2027-01-23 | draft |
| M5 General availability | ga | 2027-01-24 → 2027-02-06 | draft |

Top risks: UI rework after first walkthrough (medium×high, open, M3),
key-person dependency (medium×high, mitigating, program-level),
approval gate friction (medium×medium, mitigating, M2).
Exposure = likelihood × impact on a 1–3 scale; high-exposure (≥6) risks require
mitigation text and block approval while open.

Acceptance: every milestone carries criteria with verification methods
(e.g. M2: "Approval blocked until criteria met and risks low" verified by the
rejected-approval test case). Approval requires all criteria met and no
high-exposure open risks; only admin/product_owner can approve.
