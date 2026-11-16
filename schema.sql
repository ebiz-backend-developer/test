-- Schema-as-code migration v1: core modules MVP.
-- Applied idempotently by mvp.store (CREATE TABLE IF NOT EXISTS +
-- meta.schema_version guard). Tables are owned by exactly one module.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- admissions -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    guardian_name TEXT NOT NULL DEFAULT '',
    grade_applying TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'submitted'
        CHECK (status IN ('submitted','under_review','admitted','waitlisted','rejected')),
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    decided_at TEXT
);

-- attendance -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    class_name TEXT NOT NULL,
    UNIQUE (full_name, class_name)
);
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    class_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('present','absent','late','excused')),
    UNIQUE (student_id, class_date)
);

-- grades ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    max_score REAL NOT NULL CHECK (max_score > 0)
);
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id INTEGER NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    student_name TEXT NOT NULL,
    score REAL NOT NULL CHECK (score >= 0),
    UNIQUE (assessment_id, student_name)
);

-- timetable ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    weekday TEXT NOT NULL
        CHECK (weekday IN ('Mon','Tue','Wed','Thu','Fri','Sat')),
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    class_name TEXT NOT NULL,
    subject TEXT NOT NULL,
    teacher TEXT NOT NULL,
    room TEXT NOT NULL,
    CHECK (starts_at < ends_at)
);

-- fees -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    term TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount > 0),
    issued_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    amount REAL NOT NULL CHECK (amount > 0),
    method TEXT NOT NULL DEFAULT 'cash',
    paid_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- communication --------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT NOT NULL,
    sender_role TEXT NOT NULL,
    audience TEXT NOT NULL DEFAULT 'all',
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- milestones (c4 approval workflow) ------------------------------------
CREATE TABLE IF NOT EXISTS milestone_status (
    milestone_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned','approved','in_progress','done')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
