"""Admissions module: application intake + review workflow."""
from mvp import store

VALID = ("submitted", "under_review", "admitted", "waitlisted", "rejected")
DECISIONS = ("under_review", "admitted", "waitlisted", "rejected")


def submit(conn, student_name, grade_applying, guardian_name="", notes=""):
    if not student_name or not student_name.strip():
        raise ValueError("student_name is required")
    if not grade_applying or not grade_applying.strip():
        raise ValueError("grade_applying is required")
    cur = conn.execute(
        "INSERT INTO applications(student_name, guardian_name, grade_applying, notes)"
        " VALUES (?, ?, ?, ?)",
        (student_name.strip(), guardian_name.strip(), grade_applying.strip(),
         notes.strip()),
    )
    conn.commit()
    return get(conn, cur.lastrowid)


def get(conn, app_id):
    row = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
    if row is None:
        raise KeyError(f"application {app_id} not found")
    return dict(row)


def list_all(conn, status=None):
    if status:
        if status not in VALID:
            raise ValueError(f"unknown status: {status}")
        cur = conn.execute("SELECT * FROM applications WHERE status = ? ORDER BY id",
                           (status,))
    else:
        cur = conn.execute("SELECT * FROM applications ORDER BY id")
    return [dict(r) for r in cur.fetchall()]


def decide(conn, app_id, decision, notes=""):
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}")
    app = get(conn, app_id)
    if app["status"] in ("admitted", "rejected"):
        raise ValueError(f"application {app_id} already decided ({app['status']})")
    conn.execute(
        "UPDATE applications SET status = ?, notes = ?, decided_at = datetime('now')"
        " WHERE id = ?",
        (decision, notes, app_id),
    )
    conn.commit()
    return get(conn, app_id)
