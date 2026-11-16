"""Domain models: lightweight dataclasses over store rows."""
from __future__ import annotations

import json
from dataclasses import dataclass, field


def _roles(raw: str) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except ValueError:
        return []
    return list(value) if isinstance(value, list) else []


@dataclass
class WorkflowStep:
    position: int
    module: str
    title: str
    detail: str = ""
    allowed_roles: list[str] = field(default_factory=list)
    required_action: str = ""
    gate: str = ""

    @classmethod
    def from_row(cls, row: dict) -> "WorkflowStep":
        return cls(
            position=row["position"],
            module=row.get("module", ""),
            title=row["title"],
            detail=row.get("detail", ""),
            allowed_roles=_roles(row.get("allowed_roles", "[]")),
            required_action=row.get("required_action", ""),
            gate=row.get("gate", ""),
        )


@dataclass
class Workflow:
    code: str
    role: str
    title: str
    description: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
