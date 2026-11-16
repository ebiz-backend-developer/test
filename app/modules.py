"""Core modules and MVP prioritization (criterion c2)."""
from __future__ import annotations

MOSCOW_ORDER = {"must": 0, "should": 1, "could": 2, "wont": 3}

MODULES = [
    {"id": "admissions", "name": "Admissions", "moscow": "must", "priority": 0,
     "depends_on": [],
     "description": "Applications, review pipeline, acceptance."},
    {"id": "users-roles", "name": "Users & Roles", "moscow": "must", "priority": 0,
     "depends_on": [],
     "description": "Accounts, roles, RBAC enforcement."},
    {"id": "attendance", "name": "Attendance", "moscow": "must", "priority": 0,
     "depends_on": ["users-roles"],
     "description": "Session attendance capture and records."},
    {"id": "grades", "name": "Grades", "moscow": "must", "priority": 1,
     "depends_on": ["attendance"],
     "description": "Gradebook entry, publishing, report cards."},
    {"id": "timetable", "name": "Timetable", "moscow": "should", "priority": 1,
     "depends_on": ["users-roles"],
     "description": "Class schedules for students and teachers."},
    {"id": "fees", "name": "Fees", "moscow": "should", "priority": 1,
     "depends_on": ["admissions"],
     "description": "Invoicing and payment tracking."},
    {"id": "communication", "name": "Communication", "moscow": "could", "priority": 2,
     "depends_on": ["users-roles"],
     "description": "Announcements and parent messaging."},
    {"id": "dashboard", "name": "Dashboard", "moscow": "could", "priority": 2,
     "depends_on": ["attendance", "grades", "fees"],
     "description": "Role-based overview screens."},
]

MVP_PRIORITIES = {0, 1}


def mvp_modules(modules: list[dict] | None = None) -> list[dict]:
    """Return MVP modules (priority 0/1) in dependency-aware order."""
    mods = modules if modules is not None else MODULES
    chosen = [m for m in mods if m["priority"] in MVP_PRIORITIES]
    return order_by_dependency(chosen)


def order_by_dependency(modules: list[dict]) -> list[dict]:
    """Topological order by depends_on (stable by priority then id)."""
    by_id = {m["id"]: m for m in modules}
    ordered: list[dict] = []
    visiting: set[str] = set()

    def visit(mod: dict) -> None:
        if mod["id"] in visiting:
            raise ValueError(f"dependency cycle at '{mod['id']}'")
        if any(o["id"] == mod["id"] for o in ordered):
            return
        visiting.add(mod["id"])
        for dep in sorted(mod.get("depends_on", [])):
            if dep in by_id:
                visit(by_id[dep])
        visiting.remove(mod["id"])
        ordered.append(mod)

    for mod in sorted(modules, key=lambda m: (m["priority"], MOSCOW_ORDER.get(m["moscow"], 9), m["id"])):
        visit(mod)
    return ordered


def set_priority(modules: list[dict], module_id: str, priority: int) -> dict:
    if priority not in (0, 1, 2):
        raise ValueError("priority must be 0, 1, or 2")
    for mod in modules:
        if mod["id"] == module_id:
            mod["priority"] = priority
            return mod
    raise ValueError(f"unknown module '{module_id}'")
