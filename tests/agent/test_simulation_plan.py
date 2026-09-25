from __future__ import annotations

import pytest

from agent.review_models import RepairProposal
from agent.simulation_plan import SimulationPlan


def test_simulation_plan_round_trip(valid_plan: SimulationPlan) -> None:
    restored = SimulationPlan.from_dict(valid_plan.to_dict())

    assert restored == valid_plan
    assert restored.material["thickness"] == 0.01
    assert restored.material["plane_mode"] == "stress"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("version", 0),
        ("mesh_size", 0.0),
        ("requested_result", "temperature"),
    ],
)
def test_simulation_plan_rejects_invalid_top_level_fields(
    valid_plan: SimulationPlan,
    field: str,
    value: object,
) -> None:
    data = valid_plan.to_dict()
    key = {"mesh_size": "meshSize", "requested_result": "requestedResult"}.get(field, field)
    data[key] = value

    with pytest.raises(ValueError):
        SimulationPlan.from_dict(data)


def test_simulation_plan_rejects_internal_entity_ids(valid_plan: SimulationPlan) -> None:
    data = valid_plan.to_dict()
    data["edgeConstraints"][0]["target"] = {"edge_id": "left"}

    with pytest.raises(ValueError, match="semantic selectors"):
        SimulationPlan.from_dict(data)


def test_apply_repair_creates_new_version_without_mutating_old_plan(
    valid_plan: SimulationPlan,
) -> None:
    proposal = RepairProposal(
        title="Add vertical restraint",
        reason="Remove the remaining rigid translation",
        changes={
            "operation": "add_point_constraint",
            "target": {"selector": "bottom_left"},
            "ux": None,
            "uy": 0.0,
        },
    )

    repaired = valid_plan.applyRepair(proposal)

    assert valid_plan.version == 1
    assert valid_plan.point_constraints == []
    assert repaired.version == 2
    assert repaired.point_constraints == [
        {"target": {"selector": "bottom_left"}, "ux": None, "uy": 0.0}
    ]
