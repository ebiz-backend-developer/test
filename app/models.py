"""Domain models, validation and error types for the Design Hub."""
from __future__ import annotations

from dataclasses import dataclass, field


class ValidationError(ValueError):
    """Raised when client-supplied data fails domain validation."""


class NotFoundError(LookupError):
    """Raised when a referenced record does not exist."""


class ConflictError(ValueError):
    """Raised when a state transition or uniqueness rule is violated."""


PRIORITIES = ("P0", "P1", "P2", "P3")
MOSCOW = ("must", "should", "could", "wont")
MODULE_STATUSES = ("planned", "in_design", "in_build", "done")
TECH_LAYERS = ("frontend", "backend", "data", "mobile", "infra")
TECH_STATUSES = ("proposed", "selected", "rejected")
MILESTONE_STATUSES = ("draft", "proposed", "approved", "rejected")
SCOPE_KINDS = ("in_scope", "out_of_scope", "assumption")
DEVICES = ("desktop", "mobile", "both")
FLOW_STATUSES = ("draft", "review", "approved")
WIREFRAME_STATUSES = ("draft", "review", "approved")


def _non_empty(value: object, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValidationError(f"{name} must not be empty")
    if len(text) > 200:
        raise ValidationError(f"{name} must be at most 200 characters")
    return text


def _one_of(value: object, name: str, allowed: tuple[str, ...]) -> str:
    if value not in allowed:
        raise ValidationError(f"{name} must be one of {', '.join(allowed)}")
    return str(value)


@dataclass
class Role:
    id: int
    name: str
    description: str
    permissions: list[str] = field(default_factory=list)


@dataclass
class NewModule:
    name: str
    description: str = ""
    priority: str = "P2"
    moscow: str = "should"
    mvp: bool = True
    status: str = "planned"
    owner_role: str = "product_manager"

    def validate(self) -> "NewModule":
        self.name = _non_empty(self.name, "name")
        self.description = str(self.description or "")[:2000]
        self.priority = _one_of(self.priority, "priority", PRIORITIES)
        self.moscow = _one_of(self.moscow, "moscow", MOSCOW)
        self.status = _one_of(self.status, "status", MODULE_STATUSES)
        self.owner_role = _non_empty(self.owner_role, "owner_role")
        self.mvp = bool(self.mvp)
        return self


@dataclass
class NewTechOption:
    layer: str
    name: str
    description: str = ""
    rationale: str = ""

    def validate(self) -> "NewTechOption":
        self.layer = _one_of(self.layer, "layer", TECH_LAYERS)
        self.name = _non_empty(self.name, "name")
        self.description = str(self.description or "")[:2000]
        self.rationale = str(self.rationale or "")[:2000]
        return self


@dataclass
class NewMilestone:
    title: str
    description: str = ""
    due_date: str = ""

    def validate(self) -> "NewMilestone":
        self.title = _non_empty(self.title, "title")
        self.description = str(self.description or "")[:2000]
        self.due_date = str(self.due_date or "")[:20]
        return self


@dataclass
class NewScopeItem:
    title: str
    kind: str = "in_scope"
    detail: str = ""

    def validate(self) -> "NewScopeItem":
        self.title = _non_empty(self.title, "title")
        self.kind = _one_of(self.kind, "kind", SCOPE_KINDS)
        self.detail = str(self.detail or "")[:2000]
        return self


@dataclass
class NewFlow:
    name: str
    persona: str
    device: str = "both"
    steps: list[dict] = field(default_factory=list)

    def validate(self) -> "NewFlow":
        self.name = _non_empty(self.name, "name")
        self.persona = _non_empty(self.persona, "persona")
        self.device = _one_of(self.device, "device", DEVICES)
        if not isinstance(self.steps, list) or not self.steps:
            raise ValidationError("steps must be a non-empty list")
        for i, step in enumerate(self.steps):
            if not isinstance(step, dict):
                raise ValidationError(f"steps[{i}] must be an object")
            if not str(step.get("label", "")).strip():
                raise ValidationError(f"steps[{i}].label must not be empty")
            nxt = step.get("next", [])
            if not isinstance(nxt, list):
                raise ValidationError(f"steps[{i}].next must be a list")
        if len(self.steps) > 40:
            raise ValidationError("steps must have at most 40 entries")
        return self


@dataclass
class NewWireframe:
    title: str
    screen: str
    device: str = "desktop"
    module_id: int | None = None
    blocks: list[dict] = field(default_factory=list)

    def validate(self) -> "NewWireframe":
        self.title = _non_empty(self.title, "title")
        self.screen = _non_empty(self.screen, "screen")
        self.device = _one_of(self.device, "device", DEVICES)
        if self.module_id is not None:
            try:
                self.module_id = int(self.module_id)
            except (TypeError, ValueError):
                raise ValidationError("module_id must be an integer")
        if not isinstance(self.blocks, list) or not self.blocks:
            raise ValidationError("blocks must be a non-empty list")
        for i, block in enumerate(self.blocks):
            if not isinstance(block, dict):
                raise ValidationError(f"blocks[{i}] must be an object")
            if not str(block.get("type", "")).strip():
                raise ValidationError(f"blocks[{i}].type must not be empty")
            if not str(block.get("label", "")).strip():
                raise ValidationError(f"blocks[{i}].label must not be empty")
        if len(self.blocks) > 60:
            raise ValidationError("blocks must have at most 60 entries")
        return self
