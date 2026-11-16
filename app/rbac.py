"""Role-based access control matrix for the Design Hub (c1)."""
from __future__ import annotations

# Action -> roles allowed to perform it. Reads are public; every write
# action below requires an authenticated user whose role is listed.
PERMISSIONS: dict[str, tuple[str, ...]] = {
    "scope.write": ("admin", "product_manager"),
    "modules.write": ("admin", "product_manager"),
    "modules.status": ("admin", "product_manager", "developer"),
    "tech.propose": ("admin", "product_manager", "developer"),
    "tech.select": ("admin", "product_manager"),
    "milestones.propose": ("admin", "product_manager"),
    "milestones.approve": ("admin", "stakeholder"),
    "flows.write": ("admin", "designer", "product_manager"),
    "wireframes.write": ("admin", "designer"),
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    "admin": "Full access: manages roles, scope, modules, tech, milestones and design assets.",
    "product_manager": "Owns scope and roadmap: modules, MVP priority, tech selection, milestone proposals.",
    "designer": "Owns UX: user flows, wireframes and flow approvals input.",
    "developer": "Builds modules: updates module status and proposes tech options.",
    "stakeholder": "Approves delivery: reviews and approves/rejects milestones.",
}


def role_permissions(role: str) -> list[str]:
    """Return the sorted action list granted to a role."""
    return sorted(a for a, roles in PERMISSIONS.items() if role in roles)


def can(role: str | None, action: str) -> bool:
    """Return True when the role may perform the action."""
    if role is None:
        return False
    return role in PERMISSIONS.get(action, ())
