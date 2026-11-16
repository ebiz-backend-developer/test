# Delivery Milestones (c4)

Source of truth: `schoolms/plan.py` (`DELIVERY_MILESTONES`); live at `GET /api/v1/plan/milestones`.

| ID | Milestone | Modules | Acceptance |
|----|-----------|---------|------------|
| M1 | Foundation | users | Login works; RBAC enforced; plan API live |
| M2 | People & classes | students, teachers, classes, enrollments | Rosters build end-to-end with capacity checks |
| M3 | Daily ops | attendance, grades | Attendance + grades captured; dashboards render |
| M4 | Phase 2 | fees, timetable | Invoices paid; timetable published |
| M5 | Phase 3 | messaging, library, transport | Notifications sent; circulation/routes tracked |

This PR delivers M1–M3 (MVP) with tests; M4–M5 are scheduled follow-ups.
