from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


def _require_non_empty_text(value: str, field_name: str) -> str:
    resolved = str(value).strip()
    if not resolved:
        raise ValueError(f"{field_name} must not be empty")
    return resolved


@dataclass(frozen=True, slots=True)
class RepairProposal:
    title: str
    reason: str
    changes: dict[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", _require_non_empty_text(self.title, "title"))
        object.__setattr__(self, "reason", _require_non_empty_text(self.reason, "reason"))
        if not isinstance(self.changes, dict) or not self.changes:
            raise ValueError("changes must be a non-empty dictionary")
        operation = self.changes.get("operation")
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError("changes.operation must be a non-empty string")
        object.__setattr__(self, "changes", deepcopy(self.changes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "reason": self.reason,
            "changes": deepcopy(self.changes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RepairProposal":
        if not isinstance(data, dict):
            raise ValueError("RepairProposal data must be a dictionary")
        return cls(
            title=str(data.get("title", "")),
            reason=str(data.get("reason", "")),
            changes=deepcopy(data.get("changes", {})),
        )


@dataclass(frozen=True, slots=True)
class ReviewResult:
    has_problem: bool
    diagnosis: str
    evidence: tuple[str, ...] = field(default_factory=tuple)
    proposals: tuple[RepairProposal, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "has_problem", bool(self.has_problem))
        diagnosis = str(self.diagnosis).strip()
        if self.has_problem and not diagnosis:
            raise ValueError("diagnosis must not be empty when has_problem is true")
        object.__setattr__(self, "diagnosis", diagnosis)
        resolved_evidence = tuple(str(item).strip() for item in self.evidence)
        if any(not item for item in resolved_evidence):
            raise ValueError("evidence entries must not be empty")
        object.__setattr__(self, "evidence", resolved_evidence)
        object.__setattr__(self, "proposals", tuple(self.proposals))
        if self.has_problem and not resolved_evidence:
            raise ValueError("evidence must not be empty when has_problem is true")

    def to_dict(self) -> dict[str, Any]:
        return {
            "hasProblem": self.has_problem,
            "diagnosis": self.diagnosis,
            "evidence": list(self.evidence),
            "proposals": [proposal.to_dict() for proposal in self.proposals],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewResult":
        if not isinstance(data, dict):
            raise ValueError("ReviewResult data must be a dictionary")
        raw_proposals = data.get("proposals", [])
        if not isinstance(raw_proposals, list):
            raise ValueError("proposals must be a list")
        raw_evidence = data.get("evidence", [])
        if not isinstance(raw_evidence, list):
            raise ValueError("evidence must be a list")
        return cls(
            has_problem=bool(data.get("hasProblem", data.get("has_problem", False))),
            diagnosis=str(data.get("diagnosis", "")),
            evidence=tuple(str(item) for item in raw_evidence),
            proposals=tuple(RepairProposal.from_dict(item) for item in raw_proposals),
        )
