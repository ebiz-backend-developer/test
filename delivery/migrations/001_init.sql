-- 001: delivery-milestones schema (Task 8).
-- Scope, roles, modules, architecture decisions, milestones,
-- risks, acceptance criteria, approvals.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roles (
    name TEXT PRIMARY KEY,
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS scopes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vision TEXT NOT NULL,
    in_scope TEXT NOT NULL DEFAULT '[]',
    out_of_scope TEXT NOT NULL DEFAULT '[]',
    assumptions TEXT NOT NULL DEFAULT '[]',
    constraints_list TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    priority TEXT NOT NULL DEFAULT 'P2'
        CHECK (priority IN ('P0', 'P1', 'P2')),
    mvp INTEGER NOT NULL DEFAULT 0,
    effort_points INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'backlog'
        CHECK (status IN ('backlog', 'planned', 'in_progress', 'done')),
    depends_on TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS arch_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    option_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed'
        CHECK (status IN ('proposed', 'selected', 'rejected')),
    rationale TEXT NOT NULL DEFAULT '',
    decided_by TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    UNIQUE (category, option_name)
);

CREATE TABLE IF NOT EXISTS milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    phase TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    start_date TEXT NOT NULL DEFAULT '',
    end_date TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'planned', 'in_progress', 'at_risk', 'done', 'approved')),
    owner_role TEXT NOT NULL DEFAULT 'product_owner',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS risks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    likelihood TEXT NOT NULL DEFAULT 'medium'
        CHECK (likelihood IN ('low', 'medium', 'high')),
    impact TEXT NOT NULL DEFAULT 'medium'
        CHECK (impact IN ('low', 'medium', 'high')),
    mitigation TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'mitigating', 'closed')),
    milestone_id INTEGER REFERENCES milestones(id),
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS acceptance_criteria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    milestone_id INTEGER NOT NULL REFERENCES milestones(id),
    description TEXT NOT NULL,
    verification_method TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'met', 'failed')),
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    milestone_id INTEGER NOT NULL REFERENCES milestones(id),
    approver_role TEXT NOT NULL,
    decision TEXT NOT NULL
        CHECK (decision IN ('approved', 'rejected', 'changes_requested')),
    comment TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
