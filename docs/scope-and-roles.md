# School Management System — Scope and User Roles

Covers criterion **c1**: scope and user roles defined.

## 1. Goal

Build a multi-school (multi-tenant) School Management System (SMS) that
centralizes admissions, student records, attendance, timetable, gradebook,
fees, HR, and parent/teacher communication in one web application with
role-based access.

## 2. In scope

- Multi-tenant SaaS: one deployment serves many schools; data strictly
  isolated per school (`school_id` on every tenant-owned row).
- Academic structure: academic years, terms/semesters, classes/grades,
  sections, subjects.
- Student lifecycle: admission enquiry → application → enrollment →
  promotion/graduation/transfer.
- Daily operations: attendance, timetable, homework/assignments, exams,
  gradebook/report cards.
- Fees and billing: fee structures, invoices, payments, receipts,
  dues/defaulter reports.
- Staff/HR basics: staff profiles, leave tracking, payroll inputs.
- Communication: announcements, SMS/email/push notifications to
  staff, students, parents.
- Transport and library (post-MVP, see modules doc).
- Reports and exports (CSV/PDF) for all core modules.
- Audit log of who changed what and when.
- English-first UI; extensible to additional languages.

## 3. Out of scope (non-goals)

- Online live classes / video conferencing (integrate via link only).
- Full accounting/ERP (only school-fee ledger; export to accounting tools).
- Payroll disbursement/bank payouts (compute only; pay externally).
- Custom mobile apps in MVP (responsive web first; APIs mobile-ready).
- AI proctoring, biometric hardware drivers (accept file/API imports).

## 4. User roles

| Role | Description | Key capabilities |
|---|---|---|
| Super Admin (platform) | Operates the SaaS platform | Manage schools/tenants, plans, global settings; no access to school PII beyond support with consent |
| School Admin | Runs one school | Manage users, academic structure, admissions, fees, reports, settings |
| Principal | Academic oversight | Approve admissions, view all classes/reports, publish report cards |
| Teacher | Class/subject teacher | Mark attendance, manage assignments/exams/grades for assigned classes, message parents |
| Class Teacher | Teacher + homeroom duties | Teacher rights plus promote students, approve leave, publish class timetable |
| Student | Enrolled learner | View timetable, attendance, assignments, grades, fees due; submit assignments |
| Parent/Guardian | Linked to one or more students | View child's attendance/grades/fees, pay fees, message teachers, request leave |
| Accountant | Fee collection | Create invoices, record payments, issue receipts, defaulter follow-up; no grade edits |
| HR Officer | Staff management | Manage staff profiles, leave approvals, payroll inputs |
| Librarian | Library module | Issue/return books, manage catalogue, fines input |
| Transport Manager | Transport module | Manage routes, vehicles, drivers, rider lists |
| Receptionist | Front desk | Log enquiries, visitors, calls; create admission applications |

### Role rules

- Every account belongs to exactly one school except Super Admin.
- Roles are additive via permissions, not hard-coded menus: each API
  endpoint and UI route checks a named permission (e.g.
  `attendance.mark`, `grades.publish`).
- Parent accounts link to students via verified invite code; a parent
  sees only linked children.
- Students cannot see other students' grades or fee details.
- Teachers see only their assigned classes/subjects unless granted
  a wider permission.
- Super Admin access to tenant data is read-only, consent-based, and
  audit-logged.

## 5. Permission highlights (MVP)

- `students.read/write`, `admissions.review/approve`
- `attendance.mark/view`, `timetable.manage/view`
- `assignments.manage/submit/grade`
- `exams.manage`, `grades.enter/publish`
- `fees.structure/invoice/collect/refund`
- `staff.manage`, `leave.approve`
- `comms.broadcast/message`
- `reports.view/export`, `settings.manage`, `audit.view`

## 6. Assumptions

- One school = one tenant; school year/term dates configured per school.
- Fee payment gateways integrate per country in a later milestone;
  MVP records manual/bank-transfer payments plus one online gateway.
- MVP supports up to ~5,000 students per school and ~50 schools per
  deployment without re-architecture.

## 7. Acceptance for c1

- [x] In/out of scope listed.
- [x] All user roles named with capabilities and access rules.
- [x] MVP permission set enumerated.
