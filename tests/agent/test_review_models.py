from __future__ import annotations

import pytest

from agent.review_models import RepairProposal, ReviewResult


def test_review_result_round_trip() -> None:
    result = ReviewResult(
        has_problem=True,
        diagnosis="Insufficient constraints",
        evidence=("Solver failed with a singular matrix",),
        proposals=(
            RepairProposal(
                title="Add uy restraint",
                reason="Remove rigid translation",
                changes={
                    "operation": "add_point_constraint",
                    "target": {"selector": "bottom_left"},
                    "ux": None,
                    "uy": 0.0,
                },
            ),
        ),
    )

    assert ReviewResult.from_dict(result.to_dict()) == result


def test_problem_review_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence"):
        ReviewResult(has_problem=True, diagnosis="Problem", evidence=())
