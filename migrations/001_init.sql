-- 001: initial schema for the Design Hub.
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role_id INTEGER NOT NULL REFERENCES roles(id)
);

CREATE TABLE IF NOT EXISTS scope_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    kind TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    priority TEXT NOT NULL DEFAULT 'P2',
    moscow TEXT NOT NULL DEFAULT 'should',
    mvp INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'planned',
    owner_role TEXT NOT NULL DEFAULT 'product_manager',
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tech_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    layer TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'proposed',
    rationale TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    due_date TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft'
);

CREATE TABLE IF NOT EXISTS flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    persona TEXT NOT NULL,
    device TEXT NOT NULL DEFAULT 'both',
    status TEXT NOT NULL DEFAULT 'draft',
    steps_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS wireframes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    screen TEXT NOT NULL,
    device TEXT NOT NULL DEFAULT 'desktop',
    module_id INTEGER REFERENCES modules(id),
    status TEXT NOT NULL DEFAULT 'draft',
    blocks_json TEXT NOT NULL DEFAULT '[]'
);
