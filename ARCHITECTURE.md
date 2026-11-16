# SchoolMS Architecture (supporting note — the code is the delivery)

## c1 — Scope and user roles

In scope: people records (students, teachers), classes & enrollments,
attendance, grades/GPA, fee billing/payments, reports, dashboard UI.
Out of scope for MVP: timetable scheduling, transport, library, payroll.

Roles (`config/roles.json`, enforced by `school/auth.py` + ownership
scoping in `school/service.py`):

| Role | Access |
|---|---|
| admin | everything, incl. user management |
| teacher | own classes: roster, attendance, grades; reads students/classes |
| student | own record, attendance, grades, fees |
| parent | linked student's data (read) |
| staff | student records, enrollments, fee billing |

## c2 — Core modules and MVP priority

(`config/modules.json`, implemented in `school/service.py`)

- P1: auth, students, teachers, classes/enrollments
- P2: attendance, grades, fees
- P3: reports/dashboard polish

## c3 — Architecture and tech stack

Layered monolith, Python 3 stdlib only (no install step):
`models → store → auth/service → app (REST + static UI)`.
JSON-file persistence with atomic writes; bearer-token auth with
PBKDF2-hashed passwords; RBAC matrix plus per-class/per-student ownership
checks. Ships as one process (`run.py`).

## c4 — Delivery milestones (all approved)

(`config/milestones.json`; live status at `GET /api/milestones`,
computed by `school/milestones.py` from shipped modules)

- M1 Foundation: users, roles, student & teacher records — delivered
- M2 Academics: classes, enrollments, attendance, grades — delivered
- M3 Finance: fee billing, payments, revenue summary — delivered
- M4 Reporting: dashboard UI and analytics endpoints — delivered
