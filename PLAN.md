# School Management System — Scope, Architecture & Delivery Plan

## Goal

Deliver a web-based School Management System (SMS) that runs a single school's
daily operations — admissions, attendance, academics, fees, staff, and parent
communication — with role-based access and auditability.

## Success Criteria

| Criterion | Statement | Section |
|---|---|---|
| c1 | Scope and user roles defined | Scope, User roles |
| c2 | Core modules and MVP prioritized | Modules, MVP |
| c3 | Architecture and tech stack selected | Architecture, Tech stack |
| c4 | Delivery milestones defined with approval gate | Milestones, Approval |

The plan is done when each row above is unambiguous enough to estimate and build
without inventing scope, roles, modules, stack, or dates.

## Scope

### In scope

- Single-school operations for up to ~2,000 students and ~200 staff.
- Student lifecycle: enquiry, admission, enrollment, promotion, transfer out.
- Daily operations: attendance, timetable, gradebook, homework/assignments.
- Fees: invoicing, payments recording, receipts, dues reminders, refunds.
- Staff: profiles, roles, leave records (payroll integration is out; export only).
- Communication: announcements, SMS/email/push notifications, parent portal.
- Reports: attendance, academic, fee collection, statutory exports (CSV).
- Audit log on all grade, fee, and enrollment changes.

### Non-goals (out of scope for this plan)

- Multi-school / district SaaS tenancy (design must not block it later).
- Online payments gateway integration beyond manual reconciliation in MVP.
- Payroll processing, full HRMS, hostel, fleet GPS tracking.
- Native mobile apps (responsive web + PWA first).
- Learning Management System depth (video hosting, proctored exams).

### Assumptions

- One school, one academic calendar per year; academic year rollover required.
- English-first UI; one timezone per deployment.
- Staff have email; parents reachable by at least one of email/SMS.
- Deployment on managed infrastructure the school/operator controls.

## User roles (c1)

| Role | Users | Key capabilities |
|---|---|---|
| Super Admin | IT / operator | Tenancy config, user provisioning, roles, audit, backups |
| Principal | School head | Dashboards, approvals (admissions, leave, fee waivers), all reports |
| Office Staff | Front office | Enquiries, admissions, enrollment, certificates, fee invoices/receipts |
| Accountant | Finance | Fee structures, discounts, refunds, dues follow-up, finance reports |
| Teacher | Teaching staff | Mark attendance, timetable view, gradebook, homework, remarks |
| Class Teacher | Teacher + class | Promote/assign sections, consolidate report cards, parent notes |
| Student | Pupils (age-gated) | Timetable, homework, grades, fee dues view, announcements |
| Parent/Guardian | Families | Linked wards' attendance, grades, dues, pay-status, teacher messages |
| HR | HR staff | Staff profiles, leave approvals, documents, staff reports |
| Librarian | Library staff | Catalogue, issue/return (Phase 2) |

Rules: least privilege by default; every role sees only its school; grade and
fee mutations always write an audit entry with actor, timestamp, before/after.

## Core modules and MVP (c2)

| # | Module | Contains | Priority |
|---|---|---|---|
| M1 | Identity & Access | Users, roles (RBAC), password + OTP, sessions, audit log | P0 (MVP) |
| M2 | Admissions & Enrollment | Enquiry, application, approval, enrollment, sections, rollover | P0 (MVP) |
| M3 | Attendance | Daily/period marking, corrections with reason, defaulter list | P0 (MVP) |
| M4 | Academics | Subjects, timetable, homework, gradebook, report cards | P0 (MVP) |
| M5 | Fees & Finance | Fee heads, invoices, receipts, dues, discounts, refunds, reminders | P0 (MVP) |
| M6 | Communication | Announcements, templates, email/SMS/push queue, parent inbox | P0 (MVP) |
| M7 | Staff & Leave | Profiles, documents, leave requests/approvals, export for payroll | P1 |
| M8 | Reports & Exports | Cross-module reports, CSV/statutory exports, dashboards | P1 (MVP slice: attendance/fee/grade summaries in P0) |
| M9 | Library | Catalogue, issue/return, fines | P2 |
| M10 | Transport | Routes, stops, vehicle roster, rider lists | P2 |
| M11 | Discipline & Health | Incident log, clinic visits, vaccinations | P2 |

### MVP definition (P0)

M1–M6 plus the MVP slice of M8. Exit rule: a school can admit students, run a
term (attendance + grades + report cards), bill and collect fees, and message
parents — with audit coverage — using only this slice.

### Phase 2 (P1)

M7 and full M8. Phase 3 (P2): M9–M11 by demand, each shippable independently.

## Architecture (c3)

Style: modular monolith behind one API, one web app. Modules M1–M11 are
separate code modules with their own services and tables; they call each other
through internal service interfaces, never raw cross-module SQL. Split into
services later only when a module needs independent scaling.

```text
Browser / PWA --> Web app --> REST API (auth, RBAC, validation)
                                   |
              +--------+--------+--+---+--------+--------+
              |        |        |      |        |        |
            Auth  Admissions Attendance Academics Fees  Comms ... (modules)
              |        |        |      |        |        |
              +--------+--------+--+---+--------+--------+
                                   |
                        PostgreSQL (row-level school scope)
                        Redis (sessions, cache, job queue)
                        S3-compatible storage (documents, exports)
                        Email/SMS/push providers (queued workers)
```

Key decisions:

- One relational database; every tenant-scoped row carries `school_id`.
- Synchronous REST for CRUD; background workers for notifications, reminders,
  report exports, and rollover jobs.
- Academic-year versioning on enrollment, sections, timetable, and gradebook.
- Documented API (OpenAPI) so a future mobile app and integrations reuse it.
- Backups daily with point-in-time recovery; audit table append-only.

### Core data model (MVP slice)

- `users`, `roles`, `user_roles`; `students`, `guardians`, `student_guardians`
- `academic_years`, `classes`, `sections`, `enrollments`
- `attendance_days`, `attendance_records`
- `subjects`, `timetable_slots`, `assignments`, `grades`, `report_cards`
- `fee_heads`, `fee_structures`, `invoices`, `payments`, `receipts`
- `messages`, `notification_queue`, `audit_log`

### Non-functional requirements

- Security: hashed passwords (argon2/bcrypt), OTP for resets, RBAC on every
  endpoint, rate limits on auth, encrypted secrets, HTTPS everywhere.
- Privacy: minimal PII collection, role-scoped reads, export/delete on request.
- Reliability: 99.5% monthly for core CRUD; queued notifications retry.
- Performance target: p95 < 500 ms for list/detail pages at MVP scale.
- Observability: structured logs, health endpoint, error tracking.

## Tech stack (c3)

| Layer | Choice | Why |
|---|---|---|
| Language | TypeScript (API + web) | One language, static types for billing/grade logic |
| API framework | NestJS (Node 22 LTS) | Modular structure maps 1:1 to M1–M11, guards for RBAC |
| Web app | React + Vite + PWA | Responsive first, installable later, wide hiring pool |
| API style | REST + OpenAPI | Simple clients, generated docs/SDKs |
| ORM / migrations | Prisma | Typed queries, reviewable migrations |
| Database | PostgreSQL 16 | Relational integrity, JSONB for flexible report fields |
| Queue/cache | Redis + BullMQ | Sessions, notification jobs, exports |
| File storage | S3-compatible | Documents, backups of exports |
| Auth | Session + OIDC-ready, TOTP/OTP | School SSO later without rework |
| Testing | Vitest + Playwright | Unit/integration + E2E on MVP flows |
| CI/CD | GitHub Actions + Docker | Lint, typecheck, test, image build, deploy |
| Deploy | Managed containers + managed Postgres/Redis | No bespoke ops for MVP |

Alternatives rejected: microservices (operational cost exceeds MVP benefit);
separate backend language from frontend (splits a small team); NoSQL primary
store (weak integrity for fees/grades); native mobile first (web covers MVP).

## Delivery milestones (c4)

12-week MVP calendar for a small team (2 backend, 1 frontend, 0.5 QA, 0.25 PM).

| Milestone | Weeks | Delivers | Exit criteria |
|---|---|---|---|
| M0 Foundations | 1–2 | Repo, CI, auth/RBAC, audit, module skeleton, environments | Login + roles + audit demo on staging |
| M1 Admissions | 3–5 | M2 + M7 slice (staff profiles), rollover design | Admit-to-enroll E2E on staging |
| M2 Daily ops | 6–8 | M3 + M4 + M6 | Attendance-to-report-card E2E, parent notified |
| M3 Fees | 9–10 | M5 + M8 MVP slice | Invoice-to-receipt E2E, dues report correct |
| M4 Hardening & pilot | 11–12 | Perf, backups, runbooks, pilot with 1 school | Pilot sign-off, open P0/P1 count = 0 |

Phase 2 (M7 full + M8 full): weeks 13–18. Phase 3 (P2 modules): on demand.

### Approval

Each milestone needs recorded sign-off before the next starts: demo on staging,
exit criteria checked, and open P0/P1 defects at zero. Approval is captured in
the milestone's sign-off row (approver, date, decision). Final MVP approval at
M4 is the c4 acceptance event.

| Milestone | Approver | Date | Decision |
|---|---|---|---|
| M0 | _pending_ | _pending_ | _pending_ |
| M1 | _pending_ | _pending_ | _pending_ |
| M2 | _pending_ | _pending_ | _pending_ |
| M3 | _pending_ | _pending_ | _pending_ |
| M4 (MVP) | _pending_ | _pending_ | _pending_ |

## Validation plan

- Trace each acceptance criterion to its section (table at top).
- Walk MVP E2E flows against the module list: admit → attend → grade →
  report card; invoice → pay → receipt → dues.
- Confirm every fee/grade path names its audit entry.
- Confirm each milestone has an exit check runnable on staging.

## Risks / Open questions

- Payment gateway choice deferred: MVP reconciles offline payments; gateway
  selection is a Phase 2 decision once the school names a provider.
- Statutory report formats vary by region: confirm the school's required
  formats before M3 closes.
- Parent data quality (phone/email coverage) gates notification value: verify
  during pilot import.
