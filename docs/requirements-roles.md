# Task 3: Requirements and Roles — record (supporting note)

The runnable implementation is the record: `app/seed.py` holds the scope
items, stakeholders, roles, workflows, modules, tech options and milestones;
`app/rbac.py` holds the permission rules; `app/service.py` enforces the gates.
This note summarizes the same content for reviewers.

## c1-a: Scope

In scope: student lifecycle (enquiry → admission → enrolment → promotion →
graduation/transfer); daily operations (attendance, grades, timetable, fees,
communication); stakeholder workflows for student, teacher, admin, parent plus
registrar, accountant, principal; cross-cutting auth/RBAC, sessions/terms,
audit trail, CSV/PDF exports.

Out of scope for MVP: payroll/HR depth, inventory, transport GPS, library;
online exams/CBT and e-learning; native mobile apps (responsive web + API);
multi-school SaaS billing; payment-gateway settlement beyond provider
references.

Assumptions: one active session with multiple terms; school-configured grading,
fees, timetable slots; staff have email, parents reachable by email/SMS/push.
Constraints: no offline-first clients (retry, not sync); English-first UI; one
timezone per deployment.

## c1-b/c/d/e: Stakeholders, roles, permission rules, workflows

Stakeholders: students, parents/guardians, teachers/class teachers, school
admins, principal, registrar, accountant, IT support — each mapped to one
primary role; extra grants are explicit and audited.

Permission rules: every API action authorized by (role, module, action), deny
by default; students see own records, parents see linked wards only, teachers
see assigned classes; fee adjustments above threshold need principal approval;
grades publish in two steps (teacher drafts → principal publishes, corrections
audited); admission offers need registrar + principal; grade/fee/enrolment
mutations write audit entries.

Workflows (each enforced step-by-step by the engine): admin (provision →
configure → support enrolment → exception checks → announcements → audit);
teacher (timetable → register → draft grades → submit for publishing →
message); student (classes → homework → grades → dues → messages); parent
(link wards → attendance → grades → pay → message); registrar (enquiry →
review → offer decision → enrol); accountant (fee structure → invoices →
payments → adjustments/arrears); principal (admission, grade and fee approvals
→ dashboards).

## c2: Core modules and MVP

M1 Identity & Access, M2 Admissions & Enrolment, M3 Attendance, M4 Academics,
M5 Fees & Finance, M6 Communication = P0/MVP. M7 Staff & Leave and M8 Reports
= P1/Phase 2. M9 Library, M10 Transport, M11 Discipline & Health = P2/Phase 3.
MVP exit rule: admit students, run a term, bill/collect, message parents, with
audit coverage.

## c3: Architecture and tech stack

Architecture: modular monolith behind one API and one web app; modules own
their services and tables and call each other through service interfaces.
Tech stack (selected): Python stdlib-first services; PostgreSQL managed
(SQLite-compatible schema for dev/test); passwords + OTP with RBAC sessions;
responsive web + PWA; email + SMS/push queue; CSV/PDF exports. Rejected with
reasons: day-one microservices, SSO-only auth, native-first clients.

## c4: Delivery milestones and approval

M0 Scope & roles signed off (approved); M1 Platform foundations; M2 Daily
operations; M3 Fees & communication; M4 MVP hardening & handover — each with
goal and exit criteria. Flow: proposed → approved → in_progress → done;
approval restricted to principal/sysadmin; rejections require notes; every
decision records actor and timestamp plus an audit entry.
