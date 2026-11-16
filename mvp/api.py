"""Roleified HTTP JSON API over the six core modules.

Every route declares its required permission; mvp.roles.check enforces it.
Errors map to HTTP statuses: PermissionDenied->403, KeyError->404,
ValueError/ClashError->400.
"""
import json
from urllib.parse import parse_qs, urlparse

import config
from mvp import catalog, milestones, roles, store
from mvp.modules import (admissions, attendance, communication, fees, grades,
                         timetable)


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def _perm(role, permission):
    try:
        roles.check(role, permission)
    except roles.PermissionDenied as e:
        raise ApiError(403, str(e))


def _body(raw):
    if not raw:
        return {}
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ApiError(400, "invalid JSON body")
    if not isinstance(data, dict):
        raise ApiError(400, "JSON body must be an object")
    return data


def milestone_statuses(conn):
    saved = {r["milestone_id"]: r["status"] for r in
             conn.execute("SELECT * FROM milestone_status").fetchall()}
    out = []
    for m in milestones.MILESTONES:
        d = dict(m)
        d["status"] = saved.get(m["id"], "planned")
        out.append(d)
    return out


def set_milestone_status(conn, milestone_id, new_status):
    m = milestones.get_milestone(milestone_id)  # KeyError if unknown
    if new_status not in milestones.STATUSES:
        raise ApiError(400, f"status must be one of {milestones.STATUSES}")
    row = conn.execute("SELECT status FROM milestone_status WHERE milestone_id = ?",
                       (milestone_id,)).fetchone()
    old = row["status"] if row else "planned"
    try:
        milestones.check_transition(old, new_status)
    except ValueError as e:
        raise ApiError(400, str(e))
    conn.execute(
        "INSERT INTO milestone_status(milestone_id, status, updated_at)"
        " VALUES (?, ?, datetime('now'))"
        " ON CONFLICT(milestone_id) DO UPDATE SET status = excluded.status,"
        " updated_at = datetime('now')",
        (milestone_id, new_status),
    )
    conn.commit()
    d = dict(m)
    d["status"] = new_status
    return d


def handle(conn, method, path, query, raw_body, role):
    """Route one request. Returns (status, payload). Raises ApiError."""
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2 or parts[0] != "api":
        raise ApiError(404, "unknown path (want /api/...)")
    _, resource, *rest = parts
    data = _body(raw_body)

    def one(rest, name="id"):
        if len(rest) != 1:
            raise ApiError(404, f"want /api/{resource}/<{name}>")
        try:
            return int(rest[0])
        except ValueError:
            raise ApiError(400, f"invalid {name}: {rest[0]}")

    # ---- meta: scope / roles / modules / stack / milestones (c1-c4) ----
    if resource == "scope" and method == "GET" and not rest:
        return 200, {"scope": roles.SCOPE, "roles": roles.ROLES,
                     "permissions": roles.PERMISSIONS}
    if resource == "modules" and method == "GET" and not rest:
        return 200, {"modules": catalog.ordered_modules(),
                     "mvp": [m["id"] for m in catalog.mvp_modules()]}
    if resource == "stack" and method == "GET" and not rest:
        return 200, {"stack": config.STACK, "architecture": config.ARCHITECTURE}
    if resource == "milestones" and method == "GET" and not rest:
        return 200, {"milestones": milestone_statuses(conn)}
    if resource == "milestones" and method == "POST" and len(rest) == 2 \
            and rest[1] in ("approve", "advance", "status"):
        _perm(role, "admin.milestones")
        if rest[1] == "approve":
            return 200, set_milestone_status(conn, rest[0], "approved")
        return 200, set_milestone_status(conn, rest[0], data.get("status", ""))

    # ---- admissions ----
    if resource == "applications" and method == "GET" and not rest:
        _perm(role, "admissions.read")
        return 200, admissions.list_all(conn, query.get("status"))
    if resource == "applications" and method == "POST" and not rest:
        _perm(role, "admissions.apply")
        return 201, admissions.submit(
            conn, data.get("student_name", ""), data.get("grade_applying", ""),
            data.get("guardian_name", ""), data.get("notes", ""))
    if resource == "applications" and method == "GET" and rest:
        _perm(role, "admissions.read")
        return 200, admissions.get(conn, one(rest))
    if resource == "applications" and method == "POST" and len(rest) == 2 \
            and rest[1] == "decide":
        _perm(role, "admissions.review")
        return 200, admissions.decide(conn, one([rest[0]]),
                                      data.get("decision", ""),
                                      data.get("notes", ""))

    # ---- attendance ----
    if resource == "students" and method == "GET" and not rest:
        _perm(role, "attendance.read")
        return 200, attendance.list_students(conn, query.get("class_name"))
    if resource == "students" and method == "POST" and not rest:
        _perm(role, "attendance.mark")
        return 201, attendance.add_student(conn, data.get("full_name", ""),
                                           data.get("class_name", ""))
    if resource == "attendance" and method == "POST" and not rest:
        _perm(role, "attendance.mark")
        return 201, attendance.mark(conn, data.get("student_id"),
                                    data.get("class_date", ""),
                                    data.get("status", ""))
    if resource == "attendance" and method == "GET" and not rest:
        _perm(role, "attendance.read")
        if "student_id" in query:
            return 200, attendance.summary(conn, int(query["student_id"]))
        if "class_date" in query:
            return 200, attendance.day_roster(conn, query["class_date"],
                                              query.get("class_name"))
        raise ApiError(400, "pass ?class_date=YYYY-MM-DD or ?student_id=N")

    # ---- grades ----
    if resource == "assessments" and method == "GET" and not rest:
        _perm(role, "grades.read")
        return 200, grades.list_assessments(conn)
    if resource == "assessments" and method == "POST" and not rest:
        _perm(role, "grades.edit")
        return 201, grades.create_assessment(conn, data.get("title", ""),
                                             data.get("subject", ""),
                                             data.get("max_score", 0))
    if resource == "scores" and method == "POST" and not rest:
        _perm(role, "grades.edit")
        return 201, grades.record_score(conn, data.get("assessment_id"),
                                        data.get("student_name", ""),
                                        data.get("score", 0))
    if resource == "scores" and method == "GET" and not rest:
        _perm(role, "grades.read")
        if "assessment_id" in query:
            return 200, grades.scores_for(conn, int(query["assessment_id"]))
        if "student_name" in query:
            return 200, grades.student_average(conn, query["student_name"])
        raise ApiError(400, "pass ?assessment_id=N or ?student_name=NAME")

    # ---- timetable ----
    if resource == "slots" and method == "GET" and not rest:
        _perm(role, "timetable.read")
        return 200, timetable.list_slots(conn, query.get("weekday"),
                                         query.get("class_name"))
    if resource == "slots" and method == "POST" and not rest:
        _perm(role, "timetable.edit")
        return 201, timetable.add_slot(
            conn, data.get("weekday", ""), data.get("starts_at", ""),
            data.get("ends_at", ""), data.get("class_name", ""),
            data.get("subject", ""), data.get("teacher", ""),
            data.get("room", ""))
    if resource == "slots" and method == "DELETE" and rest:
        _perm(role, "timetable.edit")
        return 200, timetable.delete_slot(conn, one(rest))

    # ---- fees ----
    if resource == "invoices" and method == "GET" and not rest:
        _perm(role, "fees.read")
        return 200, fees.list_invoices(conn, query.get("student_name"))
    if resource == "invoices" and method == "POST" and not rest:
        _perm(role, "fees.invoice")
        return 201, fees.issue_invoice(conn, data.get("student_name", ""),
                                       data.get("term", ""),
                                       data.get("amount", 0))
    if resource == "invoices" and method == "GET" and rest:
        _perm(role, "fees.read")
        return 200, fees.get_invoice(conn, one(rest))
    if resource == "payments" and method == "POST" and not rest:
        _perm(role, "fees.collect")
        return 201, fees.record_payment(conn, data.get("invoice_id"),
                                        data.get("amount", 0),
                                        data.get("method", "cash"))
    if resource == "payments" and method == "GET" and not rest:
        _perm(role, "fees.read")
        inv = query.get("invoice_id")
        return 200, fees.list_payments(conn, int(inv) if inv else None)
    if resource == "balance" and method == "GET" and not rest:
        _perm(role, "fees.read")
        if "student_name" not in query:
            raise ApiError(400, "pass ?student_name=NAME")
        return 200, fees.student_balance(conn, query["student_name"])

    # ---- communication ----
    if resource == "messages" and method == "GET" and not rest:
        _perm(role, "comms.read")
        return 200, communication.inbox(conn, query.get("audience"))
    if resource == "messages" and method == "POST" and not rest:
        _perm(role, "comms.send")
        return 201, communication.send(
            conn, data.get("sender", role), role, data.get("subject", ""),
            data.get("body", ""), data.get("audience", "all"))

    raise ApiError(404, f"no route {method} {path}")


def dispatch(conn, method, raw_path, headers, raw_body):
    """Top-level entry: parse path/role, call handle, map errors to statuses."""
    parsed = urlparse(raw_path)
    query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    role = (headers.get("x-role") or query.pop("role", "") or "student").lower()
    if role not in roles.ROLES:
        return 403, {"error": f"unknown role '{role}'"}
    try:
        return handle(conn, method, parsed.path, query, raw_body, role)
    except ApiError as e:
        return e.status, {"error": str(e)}
    except PermissionError as e:
        return 403, {"error": str(e)}
    except KeyError as e:
        return 404, {"error": str(e)}
    except ValueError as e:
        return 400, {"error": str(e)}
