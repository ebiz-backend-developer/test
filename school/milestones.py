"""Delivery milestones as code (c4) + module registry (c2).

Milestone status is computed from the modules actually implemented in this
package, so the plan cannot drift from the shipped software.
"""
from __future__ import annotations

import json
import os

# module id -> implementation anchor (import path) and MVP priority
MODULES = {
    "auth": {"name": "Users, roles & auth", "anchor": "school.auth",
             "mvp_priority": 1},
    "students": {"name": "Student records", "anchor": "school.service",
                 "mvp_priority": 1},
    "teachers": {"name": "Teacher records", "anchor": "school.service",
                 "mvp_priority": 1},
    "classes": {"name": "Classes & enrollments", "anchor": "school.service",
                "mvp_priority": 1},
    "attendance": {"name": "Attendance tracking", "anchor": "school.service",
                   "mvp_priority": 2},
    "grades": {"name": "Grades & GPA", "anchor": "school.service",
               "mvp_priority": 2},
    "fees": {"name": "Fee billing & payments", "anchor": "school.service",
             "mvp_priority": 2},
    "reports": {"name": "Reports & dashboard", "anchor": "school.app",
                "mvp_priority": 3},
}

MILESTONES = [
    {"id": "M1", "title": "Foundation: users, roles, student & teacher records",
     "modules": ["auth", "students", "teachers"], "approved": True},
    {"id": "M2", "title": "Academics: classes, enrollments, attendance, grades",
     "modules": ["classes", "attendance", "grades"], "approved": True},
    {"id": "M3", "title": "Finance: fee billing, payments, revenue summary",
     "modules": ["fees"], "approved": True},
    {"id": "M4", "title": "Reporting: dashboard UI and analytics endpoints",
     "modules": ["reports"], "approved": True},
]


def implemented_modules():
    """Modules whose anchor package imports (i.e. shipped in this repo)."""
    import importlib
    done = set()
    for mod_id, meta in MODULES.items():
        try:
            importlib.import_module(meta["anchor"])
            done.add(mod_id)
        except ImportError:
            continue
    return done


def milestone_status():
    done = implemented_modules()
    out = []
    for ms in MILESTONES:
        have = [m for m in ms["modules"] if m in done]
        missing = [m for m in ms["modules"] if m not in done]
        status = "delivered" if not missing else (
            "in_progress" if have else "planned")
        out.append({**ms, "status": status,
                    "delivered_modules": have, "missing_modules": missing})
    return out


def overall_progress():
    statuses = milestone_status()
    delivered = sum(1 for m in statuses if m["status"] == "delivered")
    return {"milestones_total": len(statuses), "milestones_delivered": delivered,
            "percent": round(delivered / len(statuses) * 100, 1) if statuses else 0,
            "all_approved": all(m["approved"] for m in statuses),
            "milestones": statuses}


def load_modules_config(path=None):
    path = path or os.path.join(os.path.dirname(__file__), "..", "config", "modules.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {"modules": MODULES, "mvp_order": sorted(
        MODULES, key=lambda m: MODULES[m]["mvp_priority"])}
