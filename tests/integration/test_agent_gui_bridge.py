from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.workflow_state import WorkflowStage, WorkflowState, WorkflowStatus
from agent.llm_providers import DeepSeekLLMClient
from core.engineering.geometry import GeometryModel
from services.project_factory_service import (
    create_empty_workbench_project,
    create_rectangle_plate_project,
)
from ui.backend.workbench_bridge import WorkbenchBridge


class RoutedBridgeLLM:
    def __init__(self, *, unconstrained: bool = False) -> None:
        self.unconstrained = unconstrained
        self.schema_titles: list[str] = []

    def request(self, system_prompt: str, user_content: str, schema: dict) -> dict:
        del system_prompt
        title = str(schema.get("title", ""))
        self.schema_titles.append(title)
        content = json.loads(user_content)
        if title == "SimulationPlan":
            constraints = [] if self.unconstrained else [
                {"target": {"selector": "left"}, "ux": 0.0, "uy": 0.0}
            ]
            return {
                "version": 1,
                "geometry": {"type": "rectangle", "width": 2.0, "height": 1.0},
                "material": {
                    "name": "agent_steel",
                    "E": 210e9,
                    "nu": 0.3,
                    "thickness": 0.01,
                    "plane_mode": "stress",
                },
                "pointConstraints": [],
                "edgeConstraints": constraints,
                "pointLoads": [],
                "edgeLoads": [
                    {"target": {"selector": "right"}, "vector": [1000.0, 0.0]}
                ],
                "meshSize": 0.35,
                "requestedResult": "von_mises",
            }
        if title == "GeometryAction":
            geometry = content["geometry"]
            return {
                "action": "create_rectangle",
                "parameters": {
                    "width": geometry["width"],
                    "height": geometry["height"],
                    "originX": geometry.get("originX", 0.0),
                    "originY": geometry.get("originY", 0.0),
                },
            }
        if title == "MaterialActions":
            material = content["material"]
            return {
                "actions": [
                    {
                        "action": "create_material",
                        "name": material["name"],
                        "E": material["E"],
                        "nu": material["nu"],
                    },
                    {
                        "action": "assign_material",
                        "name": material["name"],
                        "thickness": material["thickness"],
                        "plane_mode": material["plane_mode"],
                    },
                ]
            }
        if title == "BCLoadActions":
            rows = content["constraintsAndLoads"]
            return {
                "actions": [
                    *(
                        {"action": "add_point_constraint", **row}
                        for row in rows["pointConstraints"]
                    ),
                    *(
                        {"action": "add_edge_constraint", **row}
                        for row in rows["edgeConstraints"]
                    ),
                    *(
                        {"action": "add_point_load", **row}
                        for row in rows["pointLoads"]
                    ),
                    *(
                        {"action": "add_edge_load", **row}
                        for row in rows["edgeLoads"]
                    ),
                ]
            }
        if title == "ReviewResult":
            return {
                "hasProblem": True,
                "diagnosis": "The model has no displacement restraints.",
                "evidence": ["Tx, Ty and Rz are unconstrained."],
                "proposals": [
                    {
                        "title": "Fully fix the left edge",
                        "reason": "A non-zero edge restraint removes Tx, Ty and Rz.",
                        "changes": {
                            "operation": "add_edge_constraint",
                            "target": {"selector": "left"},
                            "ux": 0.0,
                            "uy": 0.0,
                        },
                    }
                ],
            }
        raise AssertionError(f"Unexpected schema: {title}")


def test_agent_bridge_runs_fake_llm_workflow_and_reuses_result_ui(monkeypatch) -> None:
    pytest.importorskip("gmsh", reason="Agent GUI bridge integration requires gmsh")
    llm = RoutedBridgeLLM()
    monkeypatch.setattr(
        "ui.backend.workbench_bridge.generate_contour_images",
        lambda **_kwargs: {},
    )
    bridge = WorkbenchBridge(llm_client_factory=lambda: llm)

    assert bridge.startAgentWorkflow("Build and solve a rectangle"), bridge.statusText

    assert bridge.agentStatus == "COMPLETED"
    assert bridge.agentStage == "RESULT"
    assert bridge.hasSolution
    assert bridge.hasMesh
    assert bridge.nodeCount > 0
    assert bridge.elementCount > 0
    assert {"SimulationPlan", "GeometryAction", "MaterialActions", "BCLoadActions"}.issubset(
        set(llm.schema_titles)
    )


def test_agent_bridge_exposes_reviewer_and_confirms_repair(monkeypatch) -> None:
    pytest.importorskip("gmsh", reason="Agent GUI bridge integration requires gmsh")
    llm = RoutedBridgeLLM(unconstrained=True)
    monkeypatch.setattr(
        "ui.backend.workbench_bridge.generate_contour_images",
        lambda **_kwargs: {},
    )
    bridge = WorkbenchBridge(llm_client_factory=lambda: llm)

    assert bridge.startAgentWorkflow("Build an unsupported model for review"), bridge.statusText
    assert bridge.agentStatus == "WAITING_APPROVAL"
    assert bridge.agentNeedsApproval
    assert bridge.agentProposalCount == 1
    assert "no displacement restraints" in bridge.agentDiagnosis

    assert bridge.confirmAgentRepair(0)
    assert bridge.agentStatus == "COMPLETED"
    assert bridge.hasSolution
    assert bridge._agent_orchestrator is not None
    assert bridge._agent_orchestrator.state.simulation_plan.version == 2


def test_agent_bridge_reject_allows_natural_language_revision(monkeypatch) -> None:
    pytest.importorskip("gmsh", reason="Agent GUI bridge integration requires gmsh")
    llm = RoutedBridgeLLM(unconstrained=True)
    monkeypatch.setattr(
        "ui.backend.workbench_bridge.generate_contour_images",
        lambda **_kwargs: {},
    )
    bridge = WorkbenchBridge(llm_client_factory=lambda: llm)

    assert bridge.startAgentWorkflow("Build an unsupported model"), bridge.statusText
    assert bridge.rejectAgentRepair()
    assert bridge.agentStatus == "WAITING_USER_INPUT"
    assert bridge.agentCanRevise

    assert bridge.startAgentWorkflow("Keep the model and review it again"), bridge.statusText
    assert bridge.agentStatus == "WAITING_APPROVAL"
    assert bridge._agent_orchestrator is not None
    assert bridge._agent_orchestrator.state.simulation_plan.version == 2


def test_agent_bridge_warns_without_deleting_manual_definitions() -> None:
    project = create_rectangle_plate_project(
        width=2.0,
        height=1.0,
        young_modulus=210e9,
        poisson_ratio=0.3,
        thickness=0.01,
        qy=-1000.0,
    )
    original_bc_ids = [row.id for row in project.boundary_conditions]
    original_load_ids = [row.id for row in project.loads]
    bridge = WorkbenchBridge(llm_client_factory=lambda: RoutedBridgeLLM())
    bridge.current_project = project
    bridge._capture_agent_geometry_safety_context(project)
    project.parts[0].geometry = GeometryModel.create_rectangle(3.0, 1.0)
    state = WorkflowState(
        user_input="change geometry",
        project=project,
        current_stage=WorkflowStage.ARCHITECT,
        status=WorkflowStatus.WAITING_USER_INPUT,
    )

    bridge._apply_agent_state(state)

    assert "几何拓扑已发生变化" in bridge.agentSafetyWarning
    assert [row.id for row in project.boundary_conditions] == original_bc_ids
    assert [row.id for row in project.loads] == original_load_ids


def test_gui_workflow_entry_reads_runtime_environment_and_builds_deepseek(
    monkeypatch,
) -> None:
    bridge = WorkbenchBridge()
    monkeypatch.setenv("FEM2D_AGENT_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("FEM2D_AGENT_LLM_MODEL", "deepseek-flash")
    monkeypatch.setenv("FEM2D_AGENT_LLM_BASE_URL", "https://api.deepseek.invalid")
    monkeypatch.setenv("FEM2D_AGENT_LLM_API_KEY", "gui-test-secret")

    workflow = bridge._create_agent_workflow(
        create_empty_workbench_project("gui_runtime_config")
    )

    client = workflow.architect_agent.llm
    assert isinstance(client, DeepSeekLLMClient)
    assert client.config.provider == "deepseek"
    assert client.config.model == "deepseek-flash"
    assert client.config.base_url == "https://api.deepseek.invalid"
    assert workflow.geometry_agent.llm is client
    assert workflow.material_agent.llm is client
    assert workflow.bc_load_agent.llm is client
    assert workflow.reviewer_agent.llm is client


def test_main_qml_contains_complete_agent_approval_controls() -> None:
    qml = (
        Path(__file__).resolve().parents[2] / "ui" / "qml" / "MainWorkbench.qml"
    ).read_text(encoding="utf-8")

    assert "bridge.startAgentWorkflow(agentPromptInput.text)" in qml
    assert "bridge.confirmAgentRepair(agentProposalCombo.currentIndex)" in qml
    assert "bridge.rejectAgentRepair()" in qml
    assert "bridge.agentDiagnosis" in qml
    assert "bridge.agentEvidence" in qml
    assert "bridge.agentSafetyWarning" in qml
