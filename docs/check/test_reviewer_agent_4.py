from __future__ import annotations

import json

import pytest

from agent.execution_result import ExecutionResult
from agent.geometry_agent import GeometryAgent
from agent.llm_client import StructuredOutputError
from agent.reviewer_agent import REVIEW_RESULT_SCHEMA, ReviewerAgent
from agent.simulation_plan import SimulationPlan
from core.engineering.load_definition import LoadDefinition


def _proposal(operation: str, **changes):
    return {
        "title": f"Repair {operation}",
        "reason": "The supplied project evidence requires this minimal plan repair.",
        "changes": {"operation": operation, **changes},
    }


def _problem_response(diagnosis: str, evidence: list[str], proposal: dict):
    return {
        "hasProblem": True,
        "diagnosis": diagnosis,
        "evidence": evidence,
        "proposals": [proposal],
    }


def _failed_execution(message: str = "SingularMatrix") -> ExecutionResult:
    return ExecutionResult.failed(
        "SOLVE",
        RuntimeError(message),
        solve_result={"mesh": {"exists": True, "nodeCount": 8, "elementCount": 6}},
    )


def test_reviewer_case_1_no_displacement_constraints_uses_full_context(
    empty_project,
    valid_plan,
) -> None:
    from conftest import FakeLLMClient

    data = valid_plan.to_dict()
    data["edgeConstraints"] = []
    plan = SimulationPlan.from_dict(data)
    response = _problem_response(
        "The model retains all three two-dimensional rigid-body modes: Tx, Ty, and Rz.",
        [
            "The plan and project contain no displacement constraints.",
            "A fully fixed left edge removes Tx, Ty, and the in-plane Rz rotation.",
            "SOLVE reported SingularMatrix.",
        ],
        _proposal(
            "add_edge_constraint",
            target={"selector": "left"},
            ux=0.0,
            uy=0.0,
        ),
    )
    llm = FakeLLMClient(response)
    reviewer = ReviewerAgent(llm)

    result = reviewer.review(plan, empty_project, _failed_execution())

    assert result.has_problem
    assert result.proposals[0].changes == {
        "operation": "add_edge_constraint",
        "target": {"selector": "left"},
        "ux": 0.0,
        "uy": 0.0,
    }
    assert all(mode in result.diagnosis for mode in ("Tx", "Ty", "Rz"))
    assert llm.requests[0][2] == REVIEW_RESULT_SCHEMA
    context = json.loads(llm.requests[0][1])
    assert set(context) == {"simulationPlan", "projectSnapshot", "executionResult"}
    assert context["simulationPlan"]["edgeConstraints"] == []
    assert context["projectSnapshot"]["boundaryConditions"] == []
    assert context["executionResult"]["errorMessage"] == "SingularMatrix"
    assert context["executionResult"]["diagnostics"]["mesh"]["nodeCount"] == 8


def test_reviewer_case_2_ux_only_links_singular_failure_to_missing_uy(
    empty_project,
    valid_plan,
) -> None:
    from conftest import FakeLLMClient

    data = valid_plan.to_dict()
    data["edgeConstraints"] = [
        {"target": {"selector": "left"}, "ux": 0.0, "uy": None}
    ]
    plan = SimulationPlan.from_dict(data)
    response = _problem_response(
        "The remaining Ty rigid-body mode explains the singular solve.",
        ["The left edge fixes ux only.", "No plan constraint fixes uy.", "SOLVE reported SingularMatrix."],
        _proposal(
            "update_edge_constraint",
            target={"selector": "left"},
            ux=0.0,
            uy=0.0,
        ),
    )

    result = ReviewerAgent(FakeLLMClient(response)).review(
        plan, empty_project, _failed_execution()
    )

    assert result.proposals[0].changes["uy"] == 0.0
    assert "Ty" in result.diagnosis


def test_reviewer_case_3_missing_material_is_not_misdiagnosed(
    empty_project,
    valid_plan,
) -> None:
    from conftest import FakeLLMClient

    response = _problem_response(
        "The planned material is absent and no Section assigns it to the model.",
        ["The project snapshot has no matching material.", "The project snapshot has no assigned part Section."],
        _proposal("update_material", E=valid_plan.material["E"]),
    )

    result = ReviewerAgent(FakeLLMClient(response)).review(
        valid_plan,
        empty_project,
        ExecutionResult.failed("MATERIAL", ValueError("material assignment failed")),
    )

    assert "material" in result.diagnosis.lower()
    assert all("load" not in row.lower() for row in result.evidence)


def test_reviewer_case_4_reports_missing_geometry_target(
    empty_project,
    valid_plan,
) -> None:
    from conftest import FakeLLMClient

    GeometryAgent(FakeLLMClient({})).create_rectangle(100.0, 50.0, empty_project)
    empty_project.add_load(
        LoadDefinition(
            id="invalid_load",
            name="invalid",
            step_id=empty_project.analysis_steps[0].id,
            target_type="geometry_edge",
            target_id="missing_edge",
            load_type="edge_uniform",
            qx=100.0,
            qy=0.0,
        )
    )
    response = _problem_response(
        "A load references a geometry edge that does not exist in the current model.",
        ["Load invalid_load targets missing_edge.", "No current geometry edge has that ID."],
        _proposal(
            "update_edge_load",
            target={"selector": "right"},
            vector=[100.0, 0.0],
        ),
    )

    result = ReviewerAgent(FakeLLMClient(response)).review(
        valid_plan,
        empty_project,
        ExecutionResult.failed("BC_LOAD", ValueError("unknown geometry edge")),
    )

    assert result.has_problem
    assert "does not exist" in result.diagnosis


def test_reviewer_case_5_normal_model_proposes_no_repair(
    empty_project,
    valid_plan,
    fake_llm,
) -> None:
    from agent.bc_load_agent import BCLoadAgent
    from agent.material_agent import MaterialAgent
    from conftest import FakeLLMClient

    GeometryAgent(fake_llm).create(valid_plan, empty_project)
    MaterialAgent(fake_llm).apply(valid_plan, empty_project)
    BCLoadAgent(fake_llm).apply(valid_plan, empty_project)
    response = {
        "hasProblem": False,
        "diagnosis": "The model and successful execution are consistent with the plan.",
        "evidence": ["Geometry, material, restraints, loads, mesh, and solve are present."],
        "proposals": [],
    }
    snapshot = empty_project.to_dict()

    result = ReviewerAgent(FakeLLMClient(response)).review(
        valid_plan,
        empty_project,
        ExecutionResult.succeeded(
            "SOLVE",
            {"mesh": {"exists": True, "nodeCount": 12, "elementCount": 10}},
        ),
    )

    assert result.has_problem is False
    assert result.proposals == ()
    assert empty_project.to_dict() == snapshot


def test_reviewer_rejects_non_executable_or_internal_id_proposals(
    empty_project,
    valid_plan,
) -> None:
    from conftest import FakeLLMClient

    response = _problem_response(
        "A target should change.",
        ["The current target is invalid."],
        _proposal(
            "add_point_constraint",
            target={"point_id": "p1"},
            ux=0.0,
            uy=0.0,
        ),
    )

    with pytest.raises(
        StructuredOutputError,
        match="internal entity IDs|Invalid fields|selector or coordinate",
    ):
        ReviewerAgent(FakeLLMClient(response)).review(
            valid_plan,
            empty_project,
            _failed_execution(),
        )
