"""Planning API: scope (c1), roles (c1), modules/MVP (c2), tech stack (c3),
milestones + approvals (c4). Reads are open to any authenticated actor."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..auth import Actor, audit, current_actor, require_roles
from ..models import MilestoneCreate, ModuleUpdate, TechDecisionCreate
from ..services import planning

router = APIRouter(prefix="/planning", tags=["planning"])


@router.get("/scope")
def scope(actor: Annotated[Actor, Depends(current_actor)]):
    return {"scope": planning.list_scope()}


@router.get("/roles")
def roles(actor: Annotated[Actor, Depends(current_actor)]):
    return {"roles": planning.list_roles()}


@router.get("/modules")
def modules(mvp_only: bool = False, actor: Annotated[Actor, Depends(current_actor)] = None):
    return {"modules": planning.list_modules(mvp_only)}


@router.patch("/modules/{name}")
def update_module(name: str, body: ModuleUpdate,
                  actor: Annotated[Actor, Depends(require_roles("developer"))]):
    if body.status is None and body.priority is None:
        raise HTTPException(400, "nothing to update")
    mod = planning.update_module(name, body.status, body.priority)
    if mod is None:
        raise HTTPException(404, f"module '{name}' not found")
    audit(actor, "planning.module.update", name, f"{body.status or ''} {body.priority or ''}".strip())
    return mod


@router.get("/tech")
def tech(actor: Annotated[Actor, Depends(current_actor)]):
    return {"decisions": planning.list_tech()}


@router.post("/tech", status_code=201)
def propose_tech(body: TechDecisionCreate,
                 actor: Annotated[Actor, Depends(require_roles("developer"))]):
    decision = planning.propose_tech(body.area, body.choice, body.rationale)
    audit(actor, "planning.tech.propose", body.area, body.choice)
    return decision


@router.get("/milestones")
def milestones(actor: Annotated[Actor, Depends(current_actor)]):
    return {"milestones": planning.list_milestones()}


@router.post("/milestones", status_code=201)
def create_milestone(body: MilestoneCreate,
                     actor: Annotated[Actor, Depends(require_roles("admin"))]):
    milestone = planning.create_milestone(body.title, body.description, body.due_date)
    audit(actor, "planning.milestone.create", str(milestone["id"]), body.title)
    return milestone


@router.post("/milestones/{milestone_id}/approve")
def approve_milestone(milestone_id: int, actor: Annotated[Actor, Depends(require_roles("admin"))]):
    milestone, transitioned = planning.approve_milestone(milestone_id, actor.id)
    if milestone is None:
        raise HTTPException(404, "milestone not found")
    if not transitioned:
        raise HTTPException(409, f"milestone is {milestone['status']}, only 'proposed' can be approved")
    audit(actor, "planning.milestone.approve", str(milestone_id), milestone["title"])
    return milestone


@router.post("/milestones/{milestone_id}/complete")
def complete_milestone(milestone_id: int, actor: Annotated[Actor, Depends(require_roles("admin"))]):
    milestone, transitioned = planning.complete_milestone(milestone_id)
    if milestone is None:
        raise HTTPException(404, "milestone not found")
    if not transitioned:
        raise HTTPException(409, f"milestone is {milestone['status']}, only 'approved' can be completed")
    audit(actor, "planning.milestone.complete", str(milestone_id), milestone["title"])
    return milestone
