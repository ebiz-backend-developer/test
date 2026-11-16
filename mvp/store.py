"""SQLite data layer: idempotent migrations, connection helper, seed data."""
import os
import sqlite3

SCHEMA_VERSION = 1


def _schema_path():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "schema.sql")


def connect(db_path="school.db"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn):
    """Apply schema.sql idempotently; record schema version in meta."""
    with open(_schema_path(), encoding="utf-8") as fh:
        conn.executescript(fh.read())
    conn.execute(
        "INSERT INTO meta(key, value) VALUES ('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()
    return SCHEMA_VERSION


def rows_to_dicts(rows):
    return [dict(r) for r in rows]


def seed_demo(conn):
    """Insert a small demo dataset (idempotent-ish: skips when students exist)."""
    if conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]:
        return False
    students = [("Amina Diallo", "JSS1"), ("Brian Okoro", "JSS1"),
                ("Cynthia Eze", "JSS2"), ("David Mensah", "JSS2")]
    conn.executemany("INSERT INTO students(full_name, class_name) VALUES (?, ?)",
                     students)
    conn.execute(
        "INSERT INTO applications(student_name, guardian_name, grade_applying, status)"
        " VALUES ('Emeka Nwosu', 'Mrs Nwosu', 'JSS1', 'submitted')")
    conn.execute(
        "INSERT INTO assessments(title, subject, max_score)"
        " VALUES ('Mid-term test', 'Mathematics', 100)")
    conn.execute(
        "INSERT INTO slots(weekday, starts_at, ends_at, class_name, subject, teacher, room)"
        " VALUES ('Mon', '08:00', '09:00', 'JSS1', 'Mathematics', 'Mr Ade', 'R1')")
    conn.execute(
        "INSERT INTO invoices(student_name, term, amount)"
        " VALUES ('Amina Diallo', '2026-T1', 50000)")
    conn.execute(
        "INSERT INTO messages(sender, sender_role, audience, subject, body)"
        " VALUES ('Principal', 'admin', 'all', 'Welcome to Term 1',"
        " 'Classes begin Monday. See your timetable.')")
    conn.commit()
    return True
