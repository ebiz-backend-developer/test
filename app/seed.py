"""Seed data: roles, stakeholders, scope, workflows, modules, stack, milestones."""
from __future__ import annotations

import json

from . import rbac
from .store import Store

ROLES = [
    ("sysadmin", "System Administrator",
     "Users, roles, school setup, audit logs, backups.", "All (config)"),
    ("principal", "Principal / Head of School",
     "Approvals, dashboards, reports, announcements.", "All (read + approve)"),
    ("registrar", "Registrar / Admissions Officer",
     "Enquiries, applications, admissions, enrolment.",
     "Admissions, Communication"),
    ("teacher", "Teacher",
     "Mark attendance, enter grades, view timetable.",
     "Attendance, Grades, Timetable, Communication"),
    ("class_teacher", "Class Teacher / Form Tutor",
     "Own class attendance, comments, parent contact.",
     "Attendance, Grades, Communication"),
    ("accountant", "Accountant / Bursar",
     "Fee structures, invoices, receipts, arrears.",
     "Fees, Communication"),
    ("office_staff", "Office Staff (Admin)",
     "Front-office data entry, certificates, corrections.",
     "Admissions, Attendance, Fees"),
    ("student", "Student",
     "View timetable, grades, fees owed, messages.",
     "Timetable, Grades, Fees (read), Communication"),
    ("parent", "Parent / Guardian",
     "View ward attendance, grades, fees; pay; message teachers.",
     "Attendance, Grades, Fees, Communication (wards only)"),
    ("it_support", "IT Support",
     "User provisioning help, read-only diagnostics.", "All (limited)"),
]

STAKEHOLDERS = [
    ("students", "Students", "See timetable, homework, grades, fees owed,"
     " messages.", "student", "student"),
    ("parents", "Parents / Guardians", "Track ward attendance, grades, dues;"
     " pay; message teachers.", "parent", "parent"),
    ("teachers", "Teachers / Class teachers", "Mark attendance, teach to"
     " timetable, enter grades, contact parents.", "teacher", "teacher"),
    ("admins", "School admins", "Provision users, configure school, keep data"
     " correct and audited.", "sysadmin", "admin"),
    ("principal", "Principal / Head of School", "Approve admissions, grades,"
     " waivers; dashboards and reports.", "principal", "principal"),
    ("registrar", "Registrar / Admissions Officer", "Convert enquiries into"
     " enrolled students.", "registrar", "registrar"),
    ("accountant", "Accountant / Bursar", "Bill accurately, collect traceably,"
     " chase arrears.", "accountant", "accountant"),
    ("it_support", "IT Support / Operator", "Deploy, back up, restore,"
     " diagnose with least privilege.", "it_support", "admin"),
]

SCOPE_ITEMS = [
    ("in_scope", "Student lifecycle",
     "Enquiry, application, admission, enrolment, class assignment,"
     " promotion, graduation/transfer."),
    ("in_scope", "Daily school operations",
     "Attendance marking, grade entry and publishing, timetable publishing,"
     " fee invoicing/collection, official communication."),
    ("in_scope", "Stakeholder workflows",
     "Student, teacher, admin and parent/guardian journeys end to end, plus"
     " registrar, accountant and principal approval journeys."),
    ("in_scope", "Cross-cutting platform",
     "Authentication, role-based authorization, academic sessions/terms,"
     " audit trail, reporting exports (CSV/PDF)."),
    ("out_of_scope", "Payroll/HR depth, inventory, transport GPS, library",
     "MVP carries basic staff profiles only; full HRMS, fleet tracking and"
     " library come later."),
    ("out_of_scope", "Online examinations / CBT and e-learning delivery",
     "No proctored exams or video hosting in MVP."),
    ("out_of_scope", "Native mobile apps",
     "MVP is responsive web + API; native apps later."),
    ("out_of_scope", "Multi-school SaaS billing",
     "MVP serves one school with a multi-branch-ready data model; online"
     " payment settlement beyond recording provider references is Phase 2."),
    ("assumption", "One active academic session",
     "One active session with multiple terms; historical sessions are"
     " read-mostly."),
    ("assumption", "School-configured structures",
     "Each school defines its own grading scale, fee structure and timetable"
     " slots per term; nothing hard-coded."),
    ("assumption", "Reachable families",
     "Staff have email; parents are reachable by at least one of"
     " email/SMS/push."),
    ("constraint", "No offline-first clients",
     "Attendance entry tolerates brief outages via retry, not full offline"
     " sync."),
    ("constraint", "English-first, single timezone",
     "English UI; one timezone per deployment."),
]

# (code, role, title, description, steps)
# step: (module, title, detail, allowed_roles, required_action, gate)
WORKFLOWS = [
    ("admin", "sysadmin", "Admin workflow",
     "Provision users, configure the school, run daily exception checks,"
     " publish announcements and review the audit log.",
     [
         ("Identity", "Provision users and assign roles",
          "Create accounts, verify email/OTP, grant least-privilege roles.",
          ["sysadmin", "principal"], "users.write",
          "No user holds two conflicting approval roles without an audited"
          " exception."),
         ("Core", "Configure school profile and term",
          "School profile, academic session/terms, classes, subjects, grading"
          " scale, timetable slots.",
          ["sysadmin", "principal", "office_staff"], "scope.write",
          "Session dates and grading scale confirmed before term data entry."),
         ("Admissions", "Support enrolment and correct errors",
          "Bulk imports, document checks, corrections with reason codes.",
          ["sysadmin", "office_staff", "registrar"], "workflows.run",
          "Every correction carries a reason."),
         ("Operations", "Run daily exception checks",
          "Unmarked registers, unpublished grades, unpaid dues; nudge owners.",
          ["sysadmin", "principal", "office_staff"], "workflows.run",
          "Exceptions triaged daily before announcements go out."),
         ("Communication", "Publish announcements and templates",
          "School-wide announcements; manage message templates.",
          ["sysadmin", "principal", "office_staff"], "workflows.run",
          "Principal-approved wording for school-wide messages."),
         ("Reports", "Export summaries and review audit log",
          "Attendance, grade and fee summaries; audit review of sensitive"
          " changes.",
          ["sysadmin", "principal"], "workflows.run",
          "Audit trail complete for grade/fee/enrolment changes."),
     ]),
    ("teacher", "teacher", "Teacher workflow",
     "Teach to the timetable, mark attendance, enter grades and contact"
     " parents.",
     [
         ("Timetable", "Open weekly teaching view",
          "Assigned classes, subjects, rooms and cover notes.",
          ["teacher", "class_teacher", "principal"], "workflows.run",
          "Timetable published for the term."),
         ("Attendance", "Mark the register",
          "Daily/period marking; corrections carry a reason.",
          ["teacher", "class_teacher"], "workflows.run",
          "Register marked before the cutoff each day."),
         ("Grades", "Enter draft grades",
          "Draft marks per subject; visible to the teacher only until"
          " published.",
          ["teacher", "class_teacher"], "workflows.run",
          "Two-step publish: drafts stay unpublished until approval."),
         ("Grades", "Submit grades for publishing",
          "Principal (or delegate) publishes; published grades change only via"
          " the correction workflow with an audit entry.",
          ["principal", "sysadmin"], "milestones.approve",
          "Publisher differs from the entering teacher."),
         ("Communication", "Message parents and students",
          "Homework, remarks and follow-ups on attendance or grades.",
          ["teacher", "class_teacher"], "workflows.run",
          "Messages reference the pupil's own records only."),
     ]),
    ("student", "student", "Student workflow",
     "Follow the timetable, submit homework, track grades, dues and messages.",
     [
         ("Timetable", "Check today's classes",
          "Periods, rooms and homework due.",
          ["student"], "workflows.run", "Enrolled in an active class."),
         ("Academics", "Submit homework",
          "Turn in assignments before the deadline.",
          ["student"], "workflows.run", "Assignment still open."),
         ("Grades", "Review published grades",
          "Published marks and report cards; drafts stay hidden.",
          ["student"], "workflows.run", "Grades published by the school."),
         ("Fees", "Check dues and receipts",
          "Read-only view of invoices, dues and payment receipts.",
          ["student"], "workflows.run", "Student record linked to payer."),
         ("Communication", "Read announcements and messages",
          "School announcements and teacher messages.",
          ["student"], "workflows.run", "Account active."),
     ]),
    ("parent", "parent", "Parent workflow",
     "Track each ward's attendance, grades and dues; pay; message teachers.",
     [
         ("Identity", "Link wards to guardian account",
          "Office verifies the guardian relationship before linking.",
          ["office_staff", "sysadmin"], "users.write",
          "Verified guardian relationship per ward."),
         ("Attendance", "Review ward attendance",
          "Scoped to linked wards only.",
          ["parent"], "workflows.run", "Ward linked to the account."),
         ("Grades", "Review ward grades",
          "Published grades and report cards, scoped to wards.",
          ["parent"], "workflows.run", "Grades published by the school."),
         ("Fees", "Pay dues and keep receipts",
          "Invoices, online/offline payment records, receipts.",
          ["parent", "accountant"], "workflows.run",
          "Adjustments above threshold need principal approval."),
         ("Communication", "Message teachers",
          "Two-way messages scoped to the ward's classes.",
          ["parent"], "workflows.run", "Ward linked to the account."),
     ]),
    ("registrar", "registrar", "Registrar workflow",
     "Convert enquiries into enrolled students.",
     [
         ("Admissions", "Capture the enquiry",
          "Prospective student details and documents.",
          ["registrar", "office_staff"], "workflows.run",
          "Enquiry logged with contact details."),
         ("Admissions", "Review the application",
          "Eligibility, documents and entrance results.",
          ["registrar"], "workflows.run", "Complete application pack."),
         ("Admissions", "Decide offer / waitlist / reject",
          "Registrar acts; offers need principal approval.",
          ["principal", "sysadmin"], "milestones.approve",
          "Principal approval recorded for every offer."),
         ("Admissions", "Enrol and assign a class",
          "Create the student record and class assignment for the term.",
          ["registrar", "office_staff"], "workflows.run",
          "Offer accepted and fees acknowledged."),
     ]),
    ("accountant", "accountant", "Accountant workflow",
     "Bill accurately, collect traceably, chase arrears.",
     [
         ("Fees", "Publish the fee structure",
          "Heads, amounts and due dates per class/term.",
          ["accountant", "principal"], "modules.status",
          "Fee structure approved before invoicing."),
         ("Fees", "Raise invoices",
          "Per-student invoices from the published structure.",
          ["accountant", "office_staff"], "workflows.run",
          "Student enrolled in the billed term."),
         ("Fees", "Record payments and receipts",
          "Cash/bank/provider references with receipts.",
          ["accountant", "office_staff"], "workflows.run",
          "Every payment references an invoice."),
         ("Fees", "Handle adjustments and arrears",
          "Discounts, waivers and refunds need accountant action plus"
          " principal approval above threshold; arrears chased on schedule.",
          ["principal", "sysadmin"], "milestones.approve",
          "Above-threshold adjustments approved by the principal."),
     ]),
    ("principal", "principal", "Principal workflow",
     "Approve admissions, grades and waivers; watch dashboards and reports.",
     [
         ("Approvals", "Decide admission offers",
          "Approve or reject registrar recommendations.",
          ["principal"], "milestones.approve", "Complete application pack."),
         ("Approvals", "Publish grades",
          "Publish teacher drafts; corrections audited.",
          ["principal"], "milestones.approve",
          "Publisher differs from the entering teacher."),
         ("Approvals", "Decide fee adjustments",
          "Waivers, discounts and refunds above threshold.",
          ["principal"], "milestones.approve",
          "Accountant recommendation attached."),
         ("Reports", "Review dashboards and milestone reports",
          "Attendance, academics, collections; milestone exit criteria.",
          ["principal", "sysadmin"], "milestones.track",
          "Reports drawn from the audited record."),
     ]),
]

MODULES = [
    ("M1", "Identity & Access", "Users, roles (RBAC), password + OTP,"
     " sessions, audit log.", "P0", "MVP", "planned", 1),
    ("M2", "Admissions & Enrolment", "Enquiry, application, approval,"
     " enrolment, sections, rollover.", "P0", "MVP", "planned", 2),
    ("M3", "Attendance", "Daily/period marking, corrections with reason,"
     " defaulter list.", "P0", "MVP", "planned", 3),
    ("M4", "Academics", "Subjects, timetable, homework, gradebook, report"
     " cards.", "P0", "MVP", "planned", 4),
    ("M5", "Fees & Finance", "Fee heads, invoices, receipts, dues, discounts,"
     " refunds, reminders.", "P0", "MVP", "planned", 5),
    ("M6", "Communication", "Announcements, templates, email/SMS/push queue,"
     " parent inbox.", "P0", "MVP", "planned", 6),
    ("M7", "Staff & Leave", "Profiles, documents, leave requests/approvals,"
     " export for payroll.", "P1", "Phase 2", "planned", 7),
    ("M8", "Reports & Exports", "Cross-module reports, CSV/statutory exports,"
     " dashboards (MVP slice: attendance/fee/grade summaries).",
     "P1", "Phase 2", "planned", 8),
    ("M9", "Library", "Catalogue, issue/return, fines.", "P2", "Phase 3",
     "planned", 9),
    ("M10", "Transport", "Routes, stops, vehicle roster, rider lists.", "P2",
     "Phase 3", "planned", 10),
    ("M11", "Discipline & Health", "Incident log, clinic visits,"
     " vaccinations.", "P2", "Phase 3", "planned", 11),
]

TECH_OPTIONS = [
    ("Architecture", "Modular monolith behind one API",
     "Modules M1-M11 are separate code modules with own services and tables,"
     " calling each other through internal service interfaces, never raw"
     " cross-module SQL. Split into services only when a module needs"
     " independent scaling.", "selected",
     "One deployable, clear module boundaries; cheapest correct start."),
    ("Architecture", "Microservices from day one",
     "Separate deployables per module with a gateway.", "rejected",
     "Operational overhead unjustified at single-school scale."),
    ("Backend", "Python, stdlib-first services",
     "Service layer with dataclass models; framework adapters at the edge.",
     "selected", "Small team, easy hiring, fast iteration."),
    ("Backend", "Node/TypeScript API",
     "Alternative runtime for the API layer.", "proposed", ""),
    ("Database", "PostgreSQL (managed)",
     "System of record; SQLite-compatible schema for local dev and tests.",
     "selected", "Relational integrity, audit-friendly, managed backups."),
    ("Database", "MySQL",
     "Alternative relational store.", "proposed", ""),
    ("Auth", "Passwords + OTP with RBAC sessions",
     "Least privilege by default; grade/fee/enrolment mutations audited.",
     "selected", "Matches school operations and audit needs."),
    ("Auth", "External SSO only",
     "No local passwords; school IdP required.", "rejected",
     "Many parents lack school IdP accounts."),
    ("Web client", "Responsive web + PWA",
     "One web app for all roles; installable on phones.", "selected",
     "Covers parents and staff without native builds."),
    ("Web client", "Native mobile apps first",
     "Separate iOS/Android builds.", "rejected",
     "Out of scope for MVP; doubles client work."),
    ("Notifications", "Email + SMS/push queue",
     "Templated announcements and reminders with delivery tracking.",
     "selected", "Parents reachable on at least one channel."),
    ("Reporting", "CSV/PDF exports",
     "Attendance, academic and fee summaries plus statutory exports.",
     "selected", "Auditors and regulators accept files, not dashboards."),
]

MILESTONES = [
    ("M0", "Scope & roles signed off",
     "Stakeholders, scope, roles and workflows agreed.",
     "Scope items recorded; roles and permission rules defined; stakeholder"
     " workflows captured; principal approval recorded.", "approved",
     "seed", "seed-principal", 0),
    ("M1", "Platform foundations (M1-M2)",
     "Identity, RBAC, audit and admissions slice live.",
     "Users log in with roles; admissions converts an enquiry to an enrolled"
     " student; audit entries written.", "proposed", "seed", "", 1),
    ("M2", "Daily operations (M3-M4)",
     "Attendance and academics run a real term.",
     "Registers marked daily; timetable published; drafts entered and"
     " published grades immutable without correction flow.", "proposed",
     "seed", "", 2),
    ("M3", "Fees & communication (M5-M6)",
     "Billing, collection and parent messaging live.",
     "Invoices raised and receipted; dues reminders queued; parents message"
     " teachers from the portal.", "proposed", "seed", "", 3),
    ("M4", "MVP hardening & handover",
     "MVP slice reliable, reported and operable.",
     "Attendance/fee/grade summaries exported; backups verified; runbooks"
     " accepted by IT support.", "proposed", "seed", "", 4),
]

USERS = [
    ("Ada Principal", "principal@school.example", "principal"),
    ("Sam Sysadmin", "sysadmin@school.example", "sysadmin"),
    ("Rita Registrar", "registrar@school.example", "registrar"),
    ("Tom Teacher", "teacher@school.example", "teacher"),
    ("Clara Class-Teacher", "classteacher@school.example", "class_teacher"),
    ("Amy Accountant", "accountant@school.example", "accountant"),
    ("Olive Office", "office@school.example", "office_staff"),
    ("Stacy Student", "student@school.example", "student"),
    ("Pam Parent", "parent@school.example", "parent"),
    ("Ivan Support", "support@school.example", "it_support"),
]


def seed(store: Store) -> dict:
    """Insert reference data; returns counts. Safe to run once per database."""
    counts: dict[str, int] = {}
    with store.conn:
        for code, title, responsibilities, modules_used in ROLES:
            store.conn.execute(
                "INSERT OR IGNORE INTO roles (code, title, responsibilities,"
                " modules_used) VALUES (?, ?, ?, ?)",
                (code, title, responsibilities, modules_used),
            )
        counts["roles"] = len(ROLES)
        for action, roles in rbac.PERMISSIONS.items():
            for role in roles:
                store.conn.execute(
                    "INSERT OR IGNORE INTO role_permissions (role, action)"
                    " VALUES (?, ?)", (role, action),
                )
        counts["role_permissions"] = sum(
            len(roles) for roles in rbac.PERMISSIONS.values())
        for code, label, interest, primary_role, journey_ref in STAKEHOLDERS:
            store.conn.execute(
                "INSERT OR IGNORE INTO stakeholders (code, label, interest,"
                " primary_role, journey_ref) VALUES (?, ?, ?, ?, ?)",
                (code, label, interest, primary_role, journey_ref),
            )
        counts["stakeholders"] = len(STAKEHOLDERS)
        for kind, title, detail in SCOPE_ITEMS:
            store.conn.execute(
                "INSERT INTO scope_items (kind, title, detail)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM scope_items WHERE kind = ? AND title = ?)",
                (kind, title, detail, kind, title),
            )
        counts["scope_items"] = len(SCOPE_ITEMS)
        for code, role, title, description, steps in WORKFLOWS:
            store.conn.execute(
                "INSERT OR IGNORE INTO workflows (code, role, title,"
                " description) VALUES (?, ?, ?, ?)",
                (code, role, title, description),
            )
            for position, (module, step, detail, allowed, action, gate) in (
                    enumerate(steps, start=1)):
                store.conn.execute(
                    "INSERT INTO workflow_steps (workflow_code, position,"
                    " module, title, detail, allowed_roles, required_action,"
                    " gate) SELECT ?, ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM workflow_steps"
                    " WHERE workflow_code = ? AND position = ?)",
                    (code, position, module, step, detail,
                     json.dumps(allowed), action, gate, code, position),
                )
        counts["workflows"] = len(WORKFLOWS)
        for code, title, contains, priority, phase, status, pos in MODULES:
            store.conn.execute(
                "INSERT OR IGNORE INTO modules (code, title, contains_text,"
                " priority, phase, status, position)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (code, title, contains, priority, phase, status, pos),
            )
        counts["modules"] = len(MODULES)
        for category, name, detail, status, rationale in TECH_OPTIONS:
            store.conn.execute(
                "INSERT INTO tech_options (category, name, detail, status,"
                " rationale, proposed_by) SELECT ?, ?, ?, ?, ?, 'seed'"
                " WHERE NOT EXISTS (SELECT 1 FROM tech_options"
                " WHERE category = ? AND name = ?)",
                (category, name, detail, status, rationale, category, name),
            )
        counts["tech_options"] = len(TECH_OPTIONS)
        for code, title, goal, exit_criteria, status, by, approved_by, pos in (
                MILESTONES):
            store.conn.execute(
                "INSERT OR IGNORE INTO milestones (code, title, goal,"
                " exit_criteria, status, proposed_by, approved_by, position)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (code, title, goal, exit_criteria, status, by, approved_by,
                 pos),
            )
        counts["milestones"] = len(MILESTONES)
        for name, email, role in USERS:
            store.conn.execute(
                "INSERT OR IGNORE INTO users (name, email, role)"
                " VALUES (?, ?, ?)", (name, email, role),
            )
        counts["users"] = len(USERS)
    return counts
