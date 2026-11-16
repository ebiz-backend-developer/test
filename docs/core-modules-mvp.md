# Task 4: Core Modules and MVP Definition

School management platform covering **Admissions, Attendance, Grades,
Timetable, Fees, and Communication**.

This document is the authoritative scope record for Task 4. Each section
maps to its acceptance criterion (`c1`–`c4`).

---

## c1-a: Scope

### Problem and goal

Schools run admissions, attendance, grades, timetables, fees, and parent
communication on disconnected spreadsheets, paper, and chat apps. The goal
is one backend-driven system of record with role-based access, so every
stakeholder works from the same student, class, and term data.

### In scope (platform)

- Student lifecycle: enquiry → application → admission → enrolment →
  class assignment → graduation/transfer.
- Daily school operations: attendance marking, grade entry, timetable
  publishing, fee invoicing/collection, and official communication.
- Cross-cutting: authentication, role-based authorization, academic
  terms/sessions, audit trail, reporting exports (CSV/PDF).

### Out of scope for MVP (explicit non-goals)

- Payroll/HR, inventory, transport tracking, library management.
- Online examinations/CBT and e-learning content delivery.
- Mobile native apps (MVP is responsive web + API; native later).
- Multi-school SaaS tenancy billing (MVP supports one school with
  multi-branch-ready data model where cheap to do so).
- Payment gateway settlement beyond recording provider references
  (online payment links in Phase 2).

### Assumptions and constraints

- One active academic session with multiple terms; historical sessions
  are read-mostly.
- School defines its own grading scale, fee structure, and timetable
  slots per term (all configurable, no hard-coding).
- Offline-first clients are out of scope; attendance entry tolerates
  brief outages via retry, not full offline sync.

---

## c1-b: User roles

| Role | Primary responsibilities | Modules used |
|------|--------------------------|--------------|
| System Administrator | Users, roles, school setup, audit logs, backups | All (config) |
| Principal / Head of School | Approvals, dashboards, reports, announcements | All (read + approve) |
| Registrar / Admissions Officer | Enquiries, applications, admissions, enrolment | Admissions, Communication |
| Teacher | Mark attendance, enter grades, view timetable | Attendance, Grades, Timetable, Communication |
| Class Teacher / Form Tutor | Own class attendance, comments, parent contact | Attendance, Grades, Communication |
| Accountant / Bursar | Fee structures, invoices, receipts, arrears | Fees, Communication |
| Student | View timetable, grades, fees owed, messages | Timetable, Grades, Fees (read), Communication |
| Parent / Guardian | View ward's attendance, grades, fees; pay; message | Attendance, Grades, Fees, Communication (scoped to wards) |
| IT Support | User provisioning help, read-only diagnostics | All (limited) |

### Permission rules

- Every API action is authorized by `(role, module, action)`; deny by
  default.
- Students see only their own records; parents see only their linked
  wards' records.
- Teachers see only assigned classes/subjects unless granted
  class-teacher scope.
- Fee adjustments, discounts, and refunds require the Accountant role
  plus Principal approval above a configurable threshold.
- Grade publishing is two-step: Teacher enters draft → Principal (or
  delegate) publishes; published grades are immutable except by
  correction workflow with audit entry.
- Admissions decisions (offer/waitlist/reject) require Registrar action
  plus Principal approval for offers.

---

## c2: Core modules and MVP prioritization

Prioritization uses MoSCoW per feature: **M**ust (MVP), **S**hould
(Phase 2), **C**ould (later), **W**on't (out of scope). MVP ships the
Must slice of every module so the six modules integrate end to end.

### Module 1: Admissions (priority P0)

Purpose: convert enquiries into enrolled students.

- M: Enquiry capture; application form with documents; application
  review queue; offer / waitlist / reject decision with approval;
  acceptance and enrolment into class/session; unique student ID.
- S: Online application portal for parents; bulk import; waitlist
  auto-promotion.
- C: Entrance-exam scheduling and scoring inside Admissions.

MVP acceptance: an application can move from submitted → offered →
accepted → enrolled, and the enrolled student appears in Attendance,
Grades, Timetable, and Fees without re-entry.

### Module 2: Attendance (priority P0)

Purpose: daily truth of who is present.

- M: Class/session register per day; present/absent/late/excused codes;
  class-teacher marking with same-day edit window; per-student and
  per-class summaries; term attendance percentage.
- S: Biometric/RFID import; parent absence notifications; truancy
  alerts.
- C: Timetable-period-level attendance (MVP is daily + optional period).

MVP acceptance: a class register closes daily; summary feeds report
cards and parent views.

### Module 3: Grades (priority P0)

Purpose: record, compute, and publish student performance.

- M: Assessment setup per subject (CA/exam weights); score entry with
  validation; automatic totals/grades per school scale; draft →
  published workflow; term report card data; class broadsheet.
- S: Grade analytics and trends; parent SMS/push on publish.
- C: Custom transcript templates per school.

MVP acceptance: scores entered once compute totals correctly per the
configured scale, and only published grades are visible to
students/parents.

### Module 4: Timetable (priority P1)

Purpose: schedule classes, teachers, and rooms without clashes.

- M: Terms, days, and period slots; class-subject-teacher-room
  assignments; clash detection (teacher/room/class double-booking);
  published class and teacher timetables.
- S: Auto-generation suggestions; substitute-teacher handling; room
  utilization reports.
- C: Parent-visible exam timetable with seat allocation.

MVP acceptance: publishing a timetable with a clash is rejected with
the conflicting entries named; every student/teacher sees their own
weekly view.

### Module 5: Fees (priority P0)

Purpose: bill accurately and collect traceably.

- M: Fee structures per class/term; per-student invoices; payments with
  receipts; partial payments and arrears aging; discounts/waivers with
  approval; daily collection report.
- S: Online payment links with provider reconciliation; dunning
  reminders; multi-currency.
- C: Instalment plans engine.

MVP acceptance: invoice → payment → receipt balances to zero or shows
correct arrears; every money mutation has an audit entry with actor
and timestamp.

### Module 6: Communication (priority P1)

Purpose: official channel between school, parents, and students.

- M: Announcements (school/class scoped); direct messages
  teacher ↔ parent; message templates for fees/grades/admissions
  events; notification log; opt-out-safe record of what was sent.
- S: SMS/email/push provider integration; scheduled messages.
- C: In-app chat, forums.

MVP acceptance: admissions offers, published grades, and fee invoices
each trigger the correct template to the correct audience, logged.

### MVP definition (the shippable slice)

MVP = all **Must** features above, integrated: one student record flows
from Admissions into Attendance, Grades, Timetable, Fees, and
Communication with role-based access. No module ships standalone.

### Build order (dependency-driven)

1. Foundation: auth/RBAC, sessions/terms, school setup, audit (all
   modules depend on this).
2. Admissions → student record (feeds everything).
3. Timetable skeleton (classes/subjects needed by Attendance/Grades).
4. Attendance + Grades (parallel, share class/subject data).
5. Fees (needs enrolled students; invoices reference terms).
6. Communication (wires events from 2–5 last).

---

## c3: Architecture and tech stack

### Architecture

- **Modular monolith, API-first.** One deployable backend with strict
  module boundaries matching the six modules above plus `identity`
  (auth/RBAC), `core` (school/session/term), and `shared` (audit,
  notifications, file storage). Modules communicate through service
  interfaces, never direct table access across modules.
- **Clients:** responsive web app (MVP) consuming a versioned REST API
  (`/api/v1/...`); the same API serves future mobile apps.
- **Data:** relational database as system of record; per-module tables
  with foreign keys into `core` (students, classes, terms). No
  cross-module joins in application code outside reporting views.
- **Background jobs:** queued workers for notifications, report
  generation, and fee reminders (no long work in request handlers).
- **Files:** object storage for documents/uploads (admissions docs,
  receipts, exports); only metadata in the database.
- **Security:** JWT access tokens + refresh rotation, password hashing
  (argon2/bcrypt), RBAC enforcement at API layer, audit log on all
  mutations of student, grade, and money data.
- **Why not microservices for MVP:** six modules with shared student
  data do not justify distributed-transaction overhead; module
  boundaries keep the extraction path open later.

### Tech stack (selected)

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend language/framework | TypeScript + NestJS (Node.js) | Modular structure maps 1:1 to the six modules; strong typing; large hiring pool |
| API style | REST, versioned `/api/v1`, OpenAPI spec | Simple for web + future mobile; contract-first via OpenAPI |
| Database | PostgreSQL | Relational integrity for grades/fees; JSONB for flexible config (grading scales) |
| ORM/migrations | Prisma | Typed queries; reviewable SQL migrations |
| Auth | JWT + refresh tokens, RBAC guard per module | Matches c1 permission rules |
| Queue/jobs | Redis + BullMQ | Notifications, reminders, report jobs |
| File storage | S3-compatible object storage | Admissions documents, exports |
| Frontend (MVP) | React + Next.js, responsive | One web client for all roles; role-aware routes |
| Validation | DTO validation (class-validator) + DB constraints | Scores, money, and timetable rules enforced twice |
| Testing | Jest (unit/integration) + Supertest (API) | Covers grade computation, fee balancing, clash detection |
| DevOps | Docker Compose (local), CI pipeline (lint/test/build), container deploy | Reproducible envs; hosting-agnostic |
| Observability | Structured logs + health endpoint + audit table | MVP-minimum operability |

### Key data entities (per module)

- Core: `School, Session, Term, Class, Subject, User, Role, AuditLog`.
- Admissions: `Enquiry, Application, Document, Decision, Enrolment`.
- Attendance: `Register, AttendanceEntry (student, date, code)`.
- Grades: `Assessment, Score, GradeScale, ReportCard`.
- Timetable: `TimeSlot, Lesson (class, subject, teacher, room, slot)`.
- Fees: `FeeStructure, Invoice, Payment, Receipt, Waiver`.
- Communication: `Announcement, Message, NotificationLog`.

---

## c4: Delivery milestones

Durations assume a small team (2 backend, 1 frontend, 0.5 QA/design).
Each milestone gates on its exit criteria; nothing merges to `main`
without them.

| Milestone | Scope | Duration | Exit criteria |
|-----------|-------|----------|---------------|
| M0 — Foundation approved | Repo, CI, auth/RBAC, school/session/term setup, audit, API skeleton, OpenAPI | Week 1–2 | Login + role guard demo; OpenAPI published; CI green |
| M1 — Admissions + Timetable core | Application → enrolment flow; slots/lessons with clash detection | Week 3–5 | Enrolled student flows to all modules; clash rejection demo |
| M2 — Attendance + Grades | Registers, summaries; assessments, score entry, publish workflow, report data | Week 6–8 | Daily register close; grade publish visible only after approval |
| M3 — Fees + Communication (MVP complete) | Invoicing, payments, receipts, arrears; announcements, messaging, event templates | Week 9–11 | Invoice→payment→receipt balances; event notifications logged |
| M4 — MVP hardening & release | UAT with pilot school, data migration dry-run, docs, runbooks | Week 12–13 | UAT sign-off; pilot data migrated; release tagged |

Post-MVP (Phase 2, not gated here): online application portal,
payment-gateway reconciliation, SMS/push providers, analytics
dashboards, timetable auto-generation.

### Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Principal / Sponsor | _pending_ | _pending_ | _pending_ |
| Engineering lead | _pending_ | _pending_ | _pending_ |
| Product / Registrar rep | _pending_ | _pending_ | _pending_ |

Milestones M0–M4 above are **proposed for approval**; MVP scope is
frozen once all three sign. Changes after freeze follow the change
note below.

### Change control (post-freeze)

Scope changes require: description, affected module(s) and milestone,
effort estimate, and re-approval by the same three roles. No silent
scope additions to the MVP slice.

---

## Traceability (criteria coverage)

- **c1** — Scope and user roles: sections `c1-a`, `c1-b`.
- **c2** — Core modules and MVP prioritized: section `c2`.
- **c3** — Architecture and tech stack selected: section `c3`.
- **c4** — Delivery milestones approved: section `c4` (milestones +
  approval table + change control).
