# School Management System — Core Modules and MVP Priority

Covers criterion **c2**: core modules and MVP prioritized.

## 1. Module catalogue

| # | Module | Purpose | Key entities |
|---|---|---|---|
| M1 | User & Access (IAM) | Accounts, roles, permissions, parent linking | User, Role, Permission, StudentGuardian |
| M2 | Academic Structure | Years, terms, classes, sections, subjects | AcademicYear, Term, Grade, Section, Subject |
| M3 | Admissions & Enrollment | Enquiry → application → offer → enrollment | Enquiry, Application, Offer, Enrollment |
| M4 | Student Information (SIS) | Canonical student record | Student, Guardian, Document, MedicalNote |
| M5 | Attendance | Daily/session attendance, leave requests | AttendanceRecord, LeaveRequest |
| M6 | Timetable | Class schedules, teacher allocation, room use | Timetable, Period, Room, Allocation |
| M7 | Assignments & Homework | Create, submit, grade | Assignment, Submission, Attachment |
| M8 | Exams & Gradebook | Exams, marks entry, report cards, promotion | Exam, Mark, ReportCard, Promotion |
| M9 | Fees & Billing | Structures, invoices, payments, receipts | FeeStructure, Invoice, Payment, Receipt |
| M10 | HR & Leave | Staff profiles, leave, payroll inputs | Staff, LeaveBalance, PayrollRun |
| M11 | Communication | Announcements, messaging, SMS/email/push | Announcement, Message, Notification |
| M12 | Reports & Analytics | Dashboards, exports | SavedReport, Dashboard |
| M13 | Audit & Settings | Audit log, school settings, templates | AuditLog, Setting, Template |
| M14 | Transport | Routes, vehicles, riders (post-MVP) | Route, Vehicle, Rider |
| M15 | Library | Catalogue, issue/return, fines (post-MVP) | Book, Loan, Fine |
| M16 | Inventory/Assets | Stock, assets (later) | Item, StockMove, Asset |

## 2. MVP definition (must ship first)

MVP = M1–M13 with the narrow scope below. M14–M16 are explicitly
post-MVP.

### P0 — MVP must-haves (MoSCoW: Must)

- M1: email/password + invite codes, role-based permissions, parent
  linking, password reset.
- M2: one active academic year, terms, grades/sections/subjects CRUD.
- M3: application form, review queue, approve/reject, convert to
  enrollment.
- M4: student CRUD, documents upload, guardian links, CSV import.
- M5: teacher marks daily attendance; parent/student view; leave
  requests with approval.
- M6: weekly timetable per section; teacher clash detection.
- M7: teacher posts assignment; student submits; teacher grades.
- M8: term exams, marks entry, percentage/grade computation,
  printable report card, year-end promotion.
- M9: fee structure per grade, invoice generation, record manual
  payment + one online gateway, receipt PDF, defaulter list.
- M10: staff CRUD, leave request/approve, monthly payroll-input export.
- M11: announcements + direct teacher↔parent messages; email in MVP,
  SMS/push via provider abstraction (one provider wired).
- M12: attendance %, grade distribution, fee collection dashboards;
  CSV/PDF export on every list.
- M13: audit log on all writes; school profile, term dates, report
  templates.

### P1 — Should (first release after MVP)

- M14 transport and M15 library.
- Bulk SMS packs, push notifications to all parents.
- Second payment gateway; partial-payment plans.
- Parent mobile-friendly PWA polish.

### P2 — Could/Won't in first two releases

- M16 inventory, alumni module, multi-language UI, public API for
  third parties, native mobile apps.

## 3. Prioritization rationale

1. Schools cannot operate without M1–M6 (identity, structure,
   attendance, timetable) — highest operational value.
2. M7–M9 (assignments, exams, fees) are the daily workflows that
   justify replacing spreadsheets — highest adoption value.
3. M10–M13 are small, shared foundations (people, comms, reports,
   audit) needed by every module above.
4. M14–M16 serve subsets of schools and add operational surface
   (fleet, barcode scanners); correctly deferred.

## 4. MVP exit criteria

- A school can run a full term: admit → enroll → timetable →
  attendance → assignments → exams → report cards → fee collection.
- All MVP permissions enforced server-side; audit log covers writes.
- CSV import for students/staff; CSV/PDF export for attendance,
  grades, fees.
- 95th-percentile page/API response < 500 ms on reference data
  (5,000 students/school).

## 5. Acceptance for c2

- [x] Full module catalogue listed with entities.
- [x] MVP (P0) scope explicitly bounded per module.
- [x] P1/P2 deferred work named with rationale.
- [x] MVP exit criteria measurable.
