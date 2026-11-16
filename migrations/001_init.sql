-- 001: Task 3 requirements & roles schema.
-- Stakeholders, scope, roles, workflows (+instances), modules,
-- tech options, milestones (+approvals), users, audit.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roles (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    responsibilities TEXT NOT NULL DEFAULT '',
    modules_used TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role TEXT NOT NULL REFERENCES roles(code),
    action TEXT NOT NULL,
    PRIMARY KEY (role, action)
);

CREATE TABLE IF NOT EXISTS stakeholders (
    code TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    interest TEXT NOT NULL DEFAULT '',
    primary_role TEXT NOT NULL REFERENCES roles(code),
    journey_ref TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS scope_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK (kind IN ('in_scope', 'out_of_scope', 'assumption', 'constraint')),
    title TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS workflows (
    code TEXT PRIMARY KEY,
    role TEXT NOT NULL REFERENCES roles(code),
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS workflow_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_code TEXT NOT NULL REFERENCES workflows(code),
    position INTEGER NOT NULL,
    module TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    allowed_roles TEXT NOT NULL DEFAULT '[]',
    required_action TEXT NOT NULL DEFAULT '',
    gate TEXT NOT NULL DEFAULT '',
    UNIQUE (workflow_code, position)
);

CREATE TABLE IF NOT EXISTS workflow_instances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_code TEXT NOT NULL REFERENCES workflows(code),
    actor TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'completed', 'cancelled')),
    current_position INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id INTEGER NOT NULL REFERENCES workflow_instances(id),
    actor TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT '',
    from_position INTEGER NOT NULL,
    to_position INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS modules (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    contains_text TEXT NOT NULL DEFAULT '',
    priority TEXT NOT NULL DEFAULT 'P2' CHECK (priority IN ('P0', 'P1', 'P2')),
    phase TEXT NOT NULL DEFAULT 'Phase 3',
    status TEXT NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned', 'in_progress', 'done')),
    position INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tech_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'proposed'
        CHECK (status IN ('proposed', 'selected', 'rejected')),
    rationale TEXT NOT NULL DEFAULT '',
    proposed_by TEXT NOT NULL DEFAULT '',
    UNIQUE (category, name)
);

CREATE TABLE IF NOT EXISTS milestones (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    goal TEXT NOT NULL DEFAULT '',
    exit_criteria TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'proposed'
        CHECK (status IN ('proposed', 'approved', 'in_progress', 'done', 'rejected')),
    proposed_by TEXT NOT NULL DEFAULT '',
    approved_by TEXT NOT NULL DEFAULT '',
    approved_at TEXT NOT NULL DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    milestone_code TEXT NOT NULL REFERENCES milestones(code),
    actor TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT '',
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL REFERENCES roles(code),
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    entity_id TEXT NOT NULL DEFAULT '',
    before_json TEXT NOT NULL DEFAULT '',
    after_json TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
