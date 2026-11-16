"""Plan router: exposes scope/roles/modules/milestones (c1..c4) as live API data."""

from __future__ import annotations

from fastapi import APIRouter

from ..plan import ARCHITECTURE, DELIVERY_MILESTONES, MODULES, MVP_PRIORITY, ROLES, SCOPE

router = APIRouter(prefix="/plan", tags=["plan"])


@router.get("/scope")
def scope():
    """c1: product scope (in/out of scope, assumptions)."""
    return SCOPE


@router.get("/roles")
def roles():
    """c1: user roles and their permission matrix."""
    return ROLES


@router.get("/modules")
def modules():
    """c2: core modules with MVP/phase prioritisation."""
    return {"modules": MODULES, "mvp": MVP_PRIORITY}


@router.get("/architecture")
def architecture():
    """c3: architecture style and selected tech stack."""
    return ARCHITECTURE


@router.get("/milestones")
def milestones():
    """c4: delivery milestones and acceptance criteria."""
    return {"milestones": DELIVERY_MILESTONES}


@router.get("")
def full_plan():
    return {
        "scope": SCOPE,
        "roles": ROLES,
        "modules": MODULES,
        "mvp": MVP_PRIORITY,
        "architecture": ARCHITECTURE,
        "milestones": DELIVERY_MILESTONES,
    }
