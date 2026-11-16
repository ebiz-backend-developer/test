# Scope and User Roles (c1)

Source of truth: `schoolms/plan.py` (`SCOPE`, `ROLES`); live at `GET /api/v1/plan/scope` and `/plan/roles`.

## In scope (MVP → Phase 3)
User accounts + RBAC, student records, teacher records, classes/sections,
enrollments, attendance, grades/report cards, fee invoices + payments,
dashboards/reports.

## Out of scope for MVP
Payroll/HR, transport fleet, hostels, library circulation, online proctoring,
native mobile apps.

## Roles
| Role | Description |
|------|-------------|
| admin | Full access (`*` permission) |
| staff | Front office: admissions, fees, attendance oversight |
| teacher | Attendance + grades for assigned classes |
| student | Self-service: own classes, attendance, grades, fees |
| parent | Self-service for linked children |

RBAC is enforced server-side in `schoolms/deps.py:require_roles` and covered
by `tests/test_schoolms.py` (allowed + denied cases per role).
