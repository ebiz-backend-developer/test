# Core Modules and MVP Prioritisation (c2)

Source of truth: `schoolms/plan.py` (`MODULES`, `MVP_PRIORITY`); live at `GET /api/v1/plan/modules`.

## MVP (shipped in this PR)
| # | Module | API |
|---|--------|-----|
| 1 | Users & Access Control | `/auth/*`, `/users/*` |
| 2 | Student Records | `/students/*` |
| 3 | Teacher Records | `/teachers/*` |
| 4 | Classes & Sections | `/classes/*` |
| 5 | Enrollments | `/enrollments/*` |
| 6 | Attendance | `/attendance/*` |
| 7 | Grades & Report Cards | `/assignments`, `/grades`, `/report-cards/*` |

## Phase 2 / 3 (planned, not built)
Fees & Payments, Timetable, Messaging, Library, Transport.
