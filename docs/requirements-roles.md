# Task 3: Requirements and Roles — Stakeholders, Workflows, Scope, Modules, Architecture, Milestones

School management platform covering **Admissions, Attendance, Grades,
Timetable, Fees, and Communication**, with explicit stakeholder
workflows for **students, teachers, admins, and parents**.

This document is the authoritative requirements record for Task 3. Each
section maps to its acceptance criterion (`c1`–`c4`).

- **c1** — Scope and user roles defined: sections `c1-a` (scope),
  `c1-b` (stakeholders), `c1-c` (user roles), `c1-d` (permission
  rules), `c1-e` (role workflows).
- **c2** — Core modules and MVP prioritized: section `c2`.
- **c3** — Architecture and tech stack selected: section `c3`.
- **c4** — Delivery milestones approved: section `c4`.

---

## c1-a: Scope

### Problem and goal

Schools run admissions, attendance, grades, timetables, fees, and
parent communication on disconnected spreadsheets, paper registers,
and chat apps. The goal is one backend-driven system of record with
role-based access, so every stakeholder (student, teacher, admin,
parent, principal, registrar, accountant) works from the same student,
class, and term data, with an audit trail on sensitive changes.

### In scope (platform)

- Student lifecycle: enquiry → application → admission → enrolment →
  class assignment → promotion → graduation/transfer.
- Daily school operations: attendance marking, grade entry and
  publishing, timetable publishing, fee invoicing/collection, and
  official communication (announcements, direct messages).
- Stakeholder workflows: student, teacher, admin (system
  administrator, office staff), and parent/guardian journeys end to
  end, plus registrar, accountant, and principal approval journeys.
- Cross-cutting: authentication, role-based authorization, academic
  sessions/terms, audit trail, reporting exports (CSV/PDF).

### Out of scope for MVP (explicit non-goals)

- Payroll/HR depth, inventory, transport GPS tracking, library
  management (basic staff profiles only in MVP).
- Online examinations/CBT and e-learning content delivery.
- Native mobile apps (MVP is responsive web + API; native later).
- Multi-school SaaS tenancy billing (MVP supports one school with a
  multi-branch-ready data model where cheap to do so).
- Payment gateway settlement beyond recording provider references
  (online payment links in Phase 2).

### Assumptions and constraints

- One active academic session with multiple terms; historical sessions
  are read-mostly.
- Each school defines its own grading scale, fee structure, and
  timetable slots per term (all configurable, no hard-coding).
- Staff have email; parents are reachable by at least one of
  email/SMS/push.
- Offline-first clients are out of scope; attendance entry tolerates
  brief outages via retry, not full offline sync.
- English-first UI; one timezone per deployment.

---

## c1-b: Stakeholders

| Stakeholder | Interest | Representative journey |
|-------------|----------|------------------------|
| Students | See timetable, homework, grades, fees owed, messages | c1-e student workflow |
| Parents / Guardians | Track ward's attendance, grades, dues; pay; message teachers | c1-e parent workflow |
| Teachers / Class teachers | Mark attendance, teach to timetable, enter grades, contact parents | c1-e teacher workflow |
| School admins (System Administrator, Office Staff) | Provision users, configure school, keep data correct and audited | c1-e admin workflow |
| Principal / Head of School | Approve admissions, grades, waivers; dashboards and reports | c1-e principal workflow |
| Registrar / Admissions Officer | Convert enquiries into enrolled students | c1-e registrar workflow |
| Accountant / Bursar | Bill accurately, collect traceably, chase arrears | c1-e accountant workflow |
| IT Support / Operator | Deploy, back up, restore, diagnose with least privilege | Runs runbooks; read-only diagnostics |

Every stakeholder maps to exactly one primary role (next section);
a person may hold more than one role only via explicit grants, each
grant audited.

---

## c1-c: User roles

| Role | Primary responsibilities | Modules used |
|------|--------------------------|--------------|
| System Administrator | Users, roles, school setup, audit logs, backups | All (config) |
| Principal / Head of School | Approvals, dashboards, reports, announcements | All (read + approve) |
| Registrar / Admissions Officer | Enquiries, applications, admissions, enrolment | Admissions, Communication |
| Teacher | Mark attendance, enter grades, view timetable | Attendance, Grades, Timetable, Communication |
| Class Teacher / Form Tutor | Own class attendance, comments, parent contact | Attendance, Grades, Communication |
| Accountant / Bursar | Fee structures, invoices, receipts, arrears | Fees, Communication |
| Office Staff (Admin) | Front-office data entry, certificates, corrections | Admissions, Attendance, Fees |
| Student | View timetable, grades, fees owed, messages | Timetable, Grades, Fees (read), Communication |
| Parent / Guardian | View ward's attendance, grades, fees; pay; message | Attendance, Grades, Fees, Communication (scoped to wards) |
| IT Support | User provisioning help, read-only diagnostics | All (limited) |

---

## c1-d: Permission rules

- Every API action is authorized by `(role, module, action)`; deny by
  default. Every role sees only its own school.
- Students see only their own records; parents see only their linked
  wards' records.
- Teachers see only assigned classes/subjects unless granted
  class-teacher scope.
- Fee adjustments, discounts, and refunds require the Accountant role
  plus Principal approval above a configurable threshold.
- Grade publishing is two-step: Teacher enters draft → Principal (or
  delegate) publishes; published grades are immutable except by a
  correction workflow with an audit entry (actor, timestamp,
  before/after).
- Admissions decisions (offer/waitlist/reject) require Registrar
  action plus Principal approval for offers.
- Grade, fee, and enrolment mutations always write an audit entry.
- Least privilege by default; role grants are themselves audited.

---

## c1-e: Stakeholder workflows

Each workflow below is the happy path plus its gating rule. Steps name
the module in brackets.

### Admin workflow (System Administrator + Office Staff)

1. [Identity] Provision users and assign roles; verify email/OTP.
2. [Core] Configure school profile, academic session/terms, classes,
   subjects, grading scale, timetable slots.
3. [Admissions] Support registrar with bulk imports and document
   checks; correct data errors with reason codes.
4. [Attendance/Grades/Fees] Run daily exception checks (unmarked
   registers, unpublished grades, unpaid dues) and nudge owners.
5. [Communication] Publish school-wide announcements; manage message
   templates.
6. [Reports/Audit] Export attendance, grade, and fee summaries;
   review audit log for grade/fee/enrolment changes.
7. [Ops] Verify backups, queue health, and notification delivery.

Gating rules: no user holds two conflicting approval roles without an
audited exception; every correction carries a reason.

### Teacher workflow (Teacher + Class Teacher)

1. [Timetable] Open weekly view; see assigned classes, subjects,
   rooms, and periods.
2. [Attendance] Mark the class register daily
   (present/absent/late/excused) within the same-day edit window.
3. [Academics] Post homework/assignments with due dates.
4. [Grades] Enter draft scores per assessment (CA/exam weights);
   system validates ranges and computes totals.
5. [Grades] Submit drafts for publishing; respond to principal
   rejections with corrections.
6. [Communication] Message parents of flagged students; receive
   absence/late notifications.
7. [Class Teacher] Consolidate report-card comments and promote/assign
   sections at term end.

Gating rules: attendance closes daily; late edits need a reason and
are audited; only published grades are visible to students/parents.

### Student workflow

1. [Timetable] View personal weekly timetable and room changes.
2. [Academics] See homework/assignments and submission status.
3. [Attendance] View own attendance record and term percentage.
4. [Grades] View published grades and term report cards (drafts are
   hidden).
5. [Fees] View own invoices, dues, and receipt history.
6. [Communication] Read announcements and teacher messages; reply
   where the thread allows.

Gating rules: a student sees only their own records; grade drafts and
other students' data are never exposed.

### Parent / Guardian workflow

1. [Identity] Link to one or more wards via registrar-verified
   invitation; manage notification preferences.
2. [Attendance] View each ward's daily record, streaks, and term
   percentage; receive absence alerts.
3. [Grades] View each ward's published grades and report cards.
4. [Fees] View invoices and dues per ward; record/pick up payment
   instructions; download receipts.
5. [Communication] Receive admissions, grade-publish, and fee event
   notifications; message class teachers directly.
6. [Approvals] Acknowledge report cards, consent requests, and fee
   undertakings where required.

Gating rules: a parent sees only linked wards; unlinked lookups are
denied and logged.

### Principal workflow (approvals)

1. Review admissions offer queue; approve/reject offers.
2. Review grade-publish queue; publish or return with comments.
3. Approve fee waivers/discounts/refunds above threshold.
4. Review dashboards (attendance, collection, performance) and sign
   milestone exit criteria.

### Registrar workflow (admissions)

1. Capture enquiry → create application with documents.
2. Move application through review queue → decision
   (offer/waitlist/reject) with principal approval for offers.
3. Record acceptance → enrol student into class/session → unique
   student ID issued; record flows to Attendance, Grades, Timetable,
   Fees, and Communication without re-entry.

### Accountant workflow (fees)

1. Define fee structures per class/term; generate per-student
   invoices.
2. Record payments (full/partial) → issue receipts; track arrears
   aging.
3. Apply discounts/waivers/refunds within approval rules.
4. Send dues reminders via Communication templates; close the daily
   collection report.

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

- M: Class/session register per day; present/absent/late/excused
  codes; class-teacher marking with same-day edit window;
  per-student and per-class summaries; term attendance percentage.
- S: Biometric/RFID import; parent absence notifications; truancy
  alerts.
- C: Timetable-period-level attendance (MVP is daily + optional
  period).

MVP acceptance: a class register closes daily; summary feeds report
cards and parent views.

### Module 3: Grades (priority P0)

Purpose: record, compute, and publish student performance.

- M: Assessment setup per subject (CA/exam weights); score entry
  with validation; automatic totals/grades per school scale; draft →
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

- M: Fee structures per class/term; per-student invoices; payments
  with receipts; partial payments and arrears aging;
  discounts/waivers with approval; daily collection report.
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

MVP = all **Must** features above, integrated: one student record
flows from Admissions into Attendance, Grades, Timetable, Fees, and
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
- **Data:** relational database as system of record; per-module
  tables with foreign keys into `core` (students, classes, terms).
  No cross-module joins in application code outside reporting views.
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

```text
Browser / PWA --> Web app --> REST API (auth, RBAC, validation)
                                   |
              +--------+--------+---+---+--------+--------+
              |        |        |       |        |        |
            Auth  Admissions Attendance Grades Timetable Fees ... Comms
              |        |        |       |        |        |
              +--------+--------+---+---+--------+--------+
                                   |
                        PostgreSQL (school-scoped rows)
                        Redis (sessions, cache, job queue)
                        S3-compatible storage (documents, exports)
                        Email/SMS/push providers (queued workers)
```

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
| Frontend (MVP) | React + Vite, responsive + PWA-ready | One web client for all roles; role-aware routes |
| Validation | DTO validation (class-validator) + DB constraints | Scores, money, and timetable rules enforced twice |
| Testing | Vitest/Jest (unit/integration) + Playwright (E2E) | Covers grade computation, fee balancing, clash detection, role workflows |
| DevOps | Docker Compose (local), CI pipeline (lint/test/build), container deploy | Reproducible envs; hosting-agnostic |
| Observability | Structured logs + health endpoint + audit table | MVP-minimum operability |

Alternatives rejected: microservices (operational cost exceeds MVP
benefit); separate backend language from frontend (splits a small
team); NoSQL primary store (weak integrity for fees/grades); native
mobile first (web covers MVP).

### Key data entities (per module)

- Core: `School, Session, Term, Class, Subject, User, Role, AuditLog`.
- Admissions: `Enquiry, Application, Document, Decision, Enrolment`.
- Attendance: `Register, AttendanceEntry (student, date, code)`.
- Grades: `Assessment, Score, GradeScale, ReportCard`.
- Timetable: `TimeSlot, Lesson (class, subject, teacher, room, slot)`.
- Fees: `FeeStructure, Invoice, Payment, Receipt, Waiver`.
- Communication: `Announcement, Message, NotificationLog`.
- Links: `Student, Guardian, StudentGuardian (ward links)`.

### Non-functional requirements

- Security: hashed passwords (argon2/bcrypt), OTP for resets, RBAC on
  every endpoint, rate limits on auth, encrypted secrets, HTTPS
  everywhere.
- Privacy: minimal PII collection, role-scoped reads, export/delete
  on request.
- Reliability: 99.5% monthly for core CRUD; queued notifications
  retry with backoff.
- Performance target: p95 < 500 ms for list/detail pages at MVP
  scale (~2,000 students, ~200 staff).
- Observability: structured logs, health endpoint, error tracking.

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
frozen once all three sign. Final MVP approval at M4 is the c4
acceptance event. Each milestone needs recorded sign-off before the
next starts: demo on staging, exit criteria checked, and open P0/P1
defects at zero.

### Change control (post-freeze)

Scope changes require: description, affected module(s) and milestone,
effort estimate, and re-approval by the same three roles. No silent
scope additions to the MVP slice.

---

## Traceability (criteria coverage)

- **c1** — Scope and user roles: sections `c1-a` … `c1-e`
  (scope, stakeholders, roles, permission rules, admin/teacher/
  student/parent/principal/registrar/accountant workflows).
- **c2** — Core modules and MVP prioritized: section `c2`
  (Admissions, Attendance, Grades, Timetable, Fees, Communication;
  MoSCoW Must/Should/Could; MVP slice; build order).
- **c3** — Architecture and tech stack selected: section `c3`
  (modular monolith, REST/OpenAPI, PostgreSQL, Redis, tech stack
  table, data entities, NFRs).
- **c4** — Delivery milestones approved: section `c4` (milestones
  M0–M4 with exit criteria, approval table, change control).

## Validation plan

- Trace each acceptance criterion to its section (list at top).
- Walk MVP E2E flows against the module list: admit → attend →
  grade → report card; invoice → pay → receipt → dues.
- Walk each stakeholder workflow (student, teacher, admin, parent)
  against the permission rules: confirm every step names its module
  and gating rule.
- Confirm every fee/grade path names its audit entry.
- Confirm each milestone has an exit check runnable on staging.
