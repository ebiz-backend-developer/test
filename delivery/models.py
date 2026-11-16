"""Delivery milestones domain models (Task 8).

Pure dataclasses + validation. Persistence lives in delivery.store,
business rules in delivery.service.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone


ROLES = ("admin", "product_owner", "tech_lead", "developer", "stakeholder")

ROLE_DESCRIPTIONS = {
    "admin": "Full access: manage users, scope, modules, architecture, milestones and approvals.",
    "product_owner": "Owns scope, module/MVP priority and milestone approval.",
    "tech_lead": "Owns architecture and tech-stack selection, milestone execution status.",
    "developer": "Updates module/milestone progress, acceptance evidence, risks.",
    "stakeholder": "Read-only: views scope, roadmap, risks and approvals.",
}

PRIORITIES = ("P0", "P1", "P2")
MODULE_STATUSES = ("backlog", "planned", "in_progress", "done")
MILESTONE_STATUSES = ("draft", "planned", "in_progress", "at_risk", "done", "approved")
PHASES = ("discovery", "mvp", "beta", "ga", "scale")
ARCH_STATUSES = ("proposed", "selected", "rejected")
RISK_LEVELS = ("low", "medium", "high")
RISK_STATUSES = ("open", "mitigating", "closed")
CRITERION_STATUSES = ("pending", "met", "failed")
APPROVAL_DECISIONS = ("approved", "rejected", "changes_requested")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Scope:
    vision: str
    in_scope: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    id: int | None = None
    updated_at: str = field(default_factory=_utcnow)

    def validate(self) -> list[str]:
        errors = []
        if not self.vision or not self.vision.strip():
            errors.append("vision is required")
        if not self.in_scope:
            errors.append("in_scope must list at least one item")
        overlap = set(self.in_scope) & set(self.out_of_scope)
        if overlap:
            errors.append(f"items cannot be both in and out of scope: {sorted(overlap)}")
        return errors

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Module:
    name: str
    description: str = ""
    priority: str = "P2"
    mvp: bool = False
    effort_points: int = 1
    status: str = "backlog"
    depends_on: list[str] = field(default_factory=list)
    id: int | None = None
    updated_at: str = field(default_factory=_utcnow)

    def validate(self) -> list[str]:
        errors = []
        if not self.name or not self.name.strip():
            errors.append("name is required")
        if self.priority not in PRIORITIES:
            errors.append(f"priority must be one of {PRIORITIES}")
        if self.status not in MODULE_STATUSES:
            errors.append(f"status must be one of {MODULE_STATUSES}")
        if self.effort_points < 0:
            errors.append("effort_points must be >= 0")
        if self.name in self.depends_on:
            errors.append("module cannot depend on itself")
        return errors

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ArchDecision:
    category: str
    option_name: str
    status: str = "proposed"
    rationale: str = ""
    decided_by: str = ""
    id: int | None = None
    updated_at: str = field(default_factory=_utcnow)

    def validate(self) -> list[str]:
        errors = []
        if not self.category or not self.category.strip():
            errors.append("category is required")
        if not self.option_name or not self.option_name.strip():
            errors.append("option_name is required")
        if self.status not in ARCH_STATUSES:
            errors.append(f"status must be one of {ARCH_STATUSES}")
        if self.status == "selected" and not self.rationale.strip():
            errors.append("rationale is required when selecting a tech-stack option")
        return errors

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Milestone:
    name: str
    phase: str
    description: str = ""
    start_date: str = ""
    end_date: str = ""
    status: str = "draft"
    owner_role: str = "product_owner"
    id: int | None = None
    updated_at: str = field(default_factory=_utcnow)

    def validate(self) -> list[str]:
        errors = []
        if not self.name or not self.name.strip():
            errors.append("name is required")
        if self.phase not in PHASES:
            errors.append(f"phase must be one of {PHASES}")
        if self.status not in MILESTONE_STATUSES:
            errors.append(f"status must be one of {MILESTONE_STATUSES}")
        if self.owner_role not in ROLES:
            errors.append(f"owner_role must be one of {ROLES}")
        for label, value in (("start_date", self.start_date), ("end_date", self.end_date)):
            if value:
                try:
                    date.fromisoformat(value)
                except ValueError:
                    errors.append(f"{label} must be ISO YYYY-MM-DD")
        if self.start_date and self.end_date:
            try:
                if date.fromisoformat(self.end_date) < date.fromisoformat(self.start_date):
                    errors.append("end_date must be on or after start_date")
            except ValueError:
                pass
        return errors

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Risk:
    title: str
    likelihood: str = "medium"
    impact: str = "medium"
    mitigation: str = ""
    status: str = "open"
    milestone_id: int | None = None
    id: int | None = None
    updated_at: str = field(default_factory=_utcnow)

    def validate(self) -> list[str]:
        errors = []
        if not self.title or not self.title.strip():
            errors.append("title is required")
        if self.likelihood not in RISK_LEVELS:
            errors.append(f"likelihood must be one of {RISK_LEVELS}")
        if self.impact not in RISK_LEVELS:
            errors.append(f"impact must be one of {RISK_LEVELS}")
        if self.status not in RISK_STATUSES:
            errors.append(f"status must be one of {RISK_STATUSES}")
        if self.exposure() >= 6 and not self.mitigation.strip():
            errors.append("mitigation is required for high-exposure risks")
        return errors

    def exposure(self) -> int:
        scale = {"low": 1, "medium": 2, "high": 3}
        return scale[self.likelihood] * scale[self.impact]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["exposure"] = self.exposure()
        return d


@dataclass
class AcceptanceCriterion:
    milestone_id: int
    description: str
    verification_method: str = ""
    status: str = "pending"
    id: int | None = None
    updated_at: str = field(default_factory=_utcnow)

    def validate(self) -> list[str]:
        errors = []
        if not self.milestone_id:
            errors.append("milestone_id is required")
        if not self.description or not self.description.strip():
            errors.append("description is required")
        if self.status not in CRITERION_STATUSES:
            errors.append(f"status must be one of {CRITERION_STATUSES}")
        return errors

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Approval:
    milestone_id: int
    approver_role: str
    decision: str
    comment: str = ""
    id: int | None = None
    created_at: str = field(default_factory=_utcnow)

    def validate(self) -> list[str]:
        errors = []
        if not self.milestone_id:
            errors.append("milestone_id is required")
        if self.approver_role not in ROLES:
            errors.append(f"approver_role must be one of {ROLES}")
        if self.decision not in APPROVAL_DECISIONS:
            errors.append(f"decision must be one of {APPROVAL_DECISIONS}")
        if self.decision != "approved" and not self.comment.strip():
            errors.append("comment is required unless approving")
        return errors

    def to_dict(self) -> dict:
        return asdict(self)
