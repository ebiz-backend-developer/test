"""Attendance module: students + daily marking + summaries."""
from mvp import store

VALID = ("present", "absent", "late", "excused")


def add_student(conn, full_name, class_name):
    if not full_name or not full_name.strip():
        raise ValueError("full_name is required")
    if not class_name or not class_name.strip():
        raise ValueError("class_name is required")
    cur = conn.execute(
        "INSERT OR IGNORE INTO students(full_name, class_name) VALUES (?, ?)",
        (full_name.strip(), class_name.strip()),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM students WHERE full_name = ? AND class_name = ?",
        (full_name.strip(), class_name.strip())).fetchone()
    student = dict(row)
    student["created"] = cur.rowcount == 1
    return student


def list_students(conn, class_name=None):
    if class_name:
        cur = conn.execute("SELECT * FROM students WHERE class_name = ? ORDER BY id",
                           (class_name,))
    else:
        cur = conn.execute("SELECT * FROM students ORDER BY id")
    return [dict(r) for r in cur.fetchall()]


def mark(conn, student_id, class_date, status):
    if status not in VALID:
        raise ValueError(f"status must be one of {VALID}")
    if not class_date or not class_date.strip():
        raise ValueError("class_date is required (YYYY-MM-DD)")
    if conn.execute("SELECT id FROM students WHERE id = ?", (student_id,)).fetchone() is None:
        raise KeyError(f"student {student_id} not found")
    conn.execute(
        "INSERT INTO attendance(student_id, class_date, status) VALUES (?, ?, ?)"
        " ON CONFLICT(student_id, class_date) DO UPDATE SET status = excluded.status",
        (student_id, class_date.strip(), status),
    )
    conn.commit()
    return dict(conn.execute(
        "SELECT a.*, s.full_name, s.class_name FROM attendance a"
        " JOIN students s ON s.id = a.student_id"
        " WHERE a.student_id = ? AND a.class_date = ?",
        (student_id, class_date.strip())).fetchone())


def day_roster(conn, class_date, class_name=None):
    sql = ("SELECT s.id AS student_id, s.full_name, s.class_name,"
           " a.status FROM students s"
           " LEFT JOIN attendance a ON a.student_id = s.id AND a.class_date = ?")
    params = [class_date]
    if class_name:
        sql += " WHERE s.class_name = ?"
        params.append(class_name)
    sql += " ORDER BY s.id"
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def summary(conn, student_id):
    if conn.execute("SELECT id FROM students WHERE id = ?", (student_id,)).fetchone() is None:
        raise KeyError(f"student {student_id} not found")
    counts = {s: 0 for s in VALID}
    for r in conn.execute("SELECT status, COUNT(*) c FROM attendance"
                          " WHERE student_id = ? GROUP BY status", (student_id,)):
        counts[r["status"]] = r["c"]
    total = sum(counts.values())
    present_like = counts["present"] + counts["late"]
    return {"student_id": student_id, "counts": counts, "total": total,
            "attendance_rate": round(present_like / total, 3) if total else 0.0}
