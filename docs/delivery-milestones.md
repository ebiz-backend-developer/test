# School Management System — Delivery Milestones

Covers criterion **c4**: delivery milestones approved.

Assumes a small team (2 backend, 1 frontend, 0.5 QA/design) and the
modular-monolith plan in `architecture-and-tech-stack.md`.
Timeline: ~14 weeks from kickoff to MVP pilot.

## Milestone overview

| Milestone | Weeks | Theme | Demo |
|---|---|---|---|
| M0 Foundations | 1–2 | Repo, auth, tenancy, CI, design system | Login + roles + school setup |
| M1 School core | 3–5 | Academic structure, admissions, SIS, staff | Admit → enroll a cohort |
| M2 Daily ops | 6–8 | Attendance, timetable, assignments, comms | Run a school week |
| M3 Exams & fees | 9–11 | Gradebook, report cards, fees, payroll inputs | Full term + fee collection |
| M4 Hardening & pilot | 12–14 | Reports, audit, imports/exports, perf, pilot | Pilot school live |

## Detailed milestones and exit criteria

### M0 — Foundations (weeks 1–2)

- Deliverables: monorepo scaffold (api/web/contracts), Docker
  Compose, CI (lint/typecheck/test/build), JWT auth + RBAC, tenant
  scoping, audit log, UI shell + design tokens, OpenAPI publishing.
- Exit: new school can be created; users log in with roles;
  tenant isolation test passes; CI green.
- Approval gate: architecture review of module boundaries + RBAC.

### M1 — School core (weeks 3–5)

- Deliverables: M2 academic structure, M3 admissions pipeline, M4
  SIS + CSV import + documents, M10 staff/leave basics, M13 settings.
- Exit: 500-student CSV import < 2 min; enquiry → enrollment flow
  E2E green; guardian linking works.
- Approval gate: product review with a real admission form.

### M2 — Daily ops (weeks 6–8)

- Deliverables: M5 attendance + leave, M6 timetable with clash
  detection, M7 assignments, M11 announcements + messaging + email.
- Exit: teacher marks attendance for 40-student class < 1 min;
  timetable clash test passes; parent receives assignment notice.
- Approval gate: UX review with a teacher and a parent.

### M3 — Exams & fees (weeks 9–11)

- Deliverables: M8 exams/marks/report cards/promotion, M9 fee
  structures/invoices/payments/receipts/defaulter list, payroll
  export, M12 dashboards + exports.
- Exit: full-term E2E (exam → report card → promotion) green;
  invoice → payment → receipt E2E green; p95 API < 500 ms.
- Approval gate: finance review of fee flows + receipt template.

### M4 — Hardening & pilot (weeks 12–14)

- Deliverables: SMS/push provider wired, payment gateway live,
  backup/restore drill, load test (5,000 students), pilot runbook,
  training docs, pilot with 1–2 schools.
- Exit: restore drill succeeds; load test passes; pilot school
  runs one week of daily ops; zero critical defects open.
- Approval gate: go/no-go for wider rollout; P1 scope locked.

## Post-MVP (P1, weeks 15+)

- Transport (M14), library (M15), second gateway, payment plans,
  PWA polish — one milestone each, ordered by pilot feedback.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Scope creep into ERP/LMS | Non-goals list enforced at each gate |
| Tenant data leak | Scoping helper + isolation tests in CI |
| Fee-reconciliation errors | Idempotency keys, append-only payments, finance review gate |
| Adoption by non-technical staff | UX reviews in M2/M4, training docs, pilot |

## Sign-off

| Role | Name | Date | Signature |
|---|---|---|---|
| Product owner | _TBD_ | _TBD_ | |
| School pilot sponsor | _TBD_ | _TBD_ | |
| Tech lead | _TBD_ | _TBD_ | |

Milestones are **proposed** in this plan; they become **approved**
when all three sign-off rows are filled. Reviewer approval of this
PR counts as tech-lead approval unless stated otherwise.

## Acceptance for c4

- [x] Milestones M0–M4 with weeks, deliverables, exit criteria.
- [x] Approval gate per milestone plus final sign-off table.
- [x] Post-MVP ordering and risks recorded.
