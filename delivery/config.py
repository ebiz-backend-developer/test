"""Static configuration: delivery roles, phases, defaults."""
from __future__ import annotations

import os

DB_PATH = os.environ.get("DELIVERY_DB", "delivery.db")
SERVER_HOST = os.environ.get("DELIVERY_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("DELIVERY_PORT", "8138"))

# c1: delivery governance roles (who may do what lives in service.PERMISSIONS).
ROLES = ("admin", "product_owner", "tech_lead", "developer", "stakeholder")

ROLE_DESCRIPTIONS = {
    "admin": "Full access: users of the plan, scope, modules, architecture, milestones, risks, approvals.",
    "product_owner": "Owns scope, module/MVP priority, acceptance criteria and milestone approval.",
    "tech_lead": "Owns architecture/tech-stack selection and milestone execution status.",
    "developer": "Updates module progress, risks, and acceptance evidence.",
    "stakeholder": "Read-only: views scope, roadmap, risks and approvals.",
}

# c4: delivery phases in timeline order.
PHASE_ORDER = ("discovery", "mvp", "beta", "ga", "scale")

PHASE_DESCRIPTIONS = {
    "discovery": "Scope, roles, architecture selection and milestone approval.",
    "mvp": "Core modules for the first usable school term.",
    "beta": "Pilot schools, hardening, integrations.",
    "ga": "General availability rollout.",
    "scale": "Multi-school scale, mobile, advanced analytics.",
}

# c3: architecture categories that must each have exactly one selected option
# before the stack counts as decided.
ARCH_CATEGORIES = (
    "language",
    "framework",
    "database",
    "auth",
    "hosting",
    "messaging",
)
