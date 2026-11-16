"""Grades module: assessments, scores, per-student averages."""
from mvp import store


def create_assessment(conn, title, subject, max_score):
    if not title or not title.strip():
        raise ValueError("title is required")
    if not subject or not subject.strip():
        raise ValueError("subject is required")
    max_score = float(max_score)
    if max_score <= 0:
        raise ValueError("max_score must be > 0")
    cur = conn.execute(
        "INSERT INTO assessments(title, subject, max_score) VALUES (?, ?, ?)",
        (title.strip(), subject.strip(), max_score),
    )
    conn.commit()
    return get_assessment(conn, cur.lastrowid)


def get_assessment(conn, assessment_id):
    row = conn.execute("SELECT * FROM assessments WHERE id = ?",
                       (assessment_id,)).fetchone()
    if row is None:
        raise KeyError(f"assessment {assessment_id} not found")
    return dict(row)


def list_assessments(conn):
    return [dict(r) for r in
            conn.execute("SELECT * FROM assessments ORDER BY id").fetchall()]


def record_score(conn, assessment_id, student_name, score):
    a = get_assessment(conn, assessment_id)
    if not student_name or not student_name.strip():
        raise ValueError("student_name is required")
    score = float(score)
    if score < 0 or score > a["max_score"]:
        raise ValueError(f"score must be between 0 and {a['max_score']}")
    conn.execute(
        "INSERT INTO scores(assessment_id, student_name, score) VALUES (?, ?, ?)"
        " ON CONFLICT(assessment_id, student_name) DO UPDATE SET score = excluded.score",
        (assessment_id, student_name.strip(), score),
    )
    conn.commit()
    return dict(conn.execute("SELECT * FROM scores WHERE assessment_id = ?"
                             " AND student_name = ?",
                             (assessment_id, student_name.strip())).fetchone())


def scores_for(conn, assessment_id):
    get_assessment(conn, assessment_id)
    return [dict(r) for r in conn.execute(
        "SELECT * FROM scores WHERE assessment_id = ? ORDER BY student_name",
        (assessment_id,)).fetchall()]


def student_average(conn, student_name):
    rows = conn.execute(
        "SELECT s.score, a.max_score FROM scores s"
        " JOIN assessments a ON a.id = s.assessment_id"
        " WHERE s.student_name = ?", (student_name,)).fetchall()
    rows = list(rows)
    if not rows:
        return {"student_name": student_name, "assessments": 0, "average_pct": 0.0}
    pct = sum(r["score"] / r["max_score"] for r in rows) / len(rows) * 100
    return {"student_name": student_name, "assessments": len(rows),
            "average_pct": round(pct, 2)}
