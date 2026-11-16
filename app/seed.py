"""Seed reference data: roles, permissions, stakeholders, modules, milestones."""
from __future__ import annotations

import json

from . import milestones as ms
from . import modules as mods
from . import rbac
from .store import Store


def seed(store: Store) -> dict:
    db = store.conn
    counts: dict[str, int] = {}
    for name, meta in rbac.ROLES.items():
        db.execute("INSERT OR IGNORE INTO roles (name, title, description) VALUES (?, ?, ?)",
                   (name, meta["title"], meta["description"]))
    counts["roles"] = len(rbac.ROLES)
    for perm, desc in rbac.PERMISSIONS.items():
        db.execute("INSERT OR IGNORE INTO permissions (name, description) VALUES (?, ?)",
                   (perm, desc))
    counts["permissions"] = len(rbac.PERMISSIONS)
    grants = 0
    for role, perms in rbac.ROLE_PERMISSIONS.items():
        for perm in perms:
            db.execute("INSERT OR IGNORE INTO role_permissions (role, permission) VALUES (?, ?)",
                       (role, perm))
            grants += 1
    counts["role_permissions"] = grants
    for st in rbac.STAKEHOLDERS:
        db.execute(
            "INSERT OR IGNORE INTO stakeholders (id, name, role, interest)"
            " VALUES (?, ?, ?, ?)", (st["id"], st["name"], st["role"], st["interest"]))
    counts["stakeholders"] = len(rbac.STAKEHOLDERS)
    for m in mods.MODULES:
        db.execute(
            "INSERT OR IGNORE INTO modules (id, name, description, moscow, priority, depends_on)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (m["id"], m["name"], m["description"], m["moscow"],
             m["priority"], json.dumps(m["depends_on"])))
    counts["modules"] = len(mods.MODULES)
    for m in ms.MILESTONES:
        db.execute(
            "INSERT OR IGNORE INTO milestones (id, title, goal, due_week, status)"
            " VALUES (?, ?, ?, ?, 'draft')",
            (m["id"], m["title"], m["goal"], m["due_week"]))
    counts["milestones"] = len(ms.MILESTONES)
    db.commit()
    return counts


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "schoolms.db"
    store = Store(path)
    print(seed(store))
    store.close()
