from __future__ import annotations

import json
import inspect
from pathlib import Path

import pytest

from agent.workflow_state import WorkflowStage, WorkflowState, WorkflowStatus
from agent.llm_providers import DeepSeekLLMClient
from agent.workflow_factory import create_agent_workflow
from agent.architect_agent import PLANE_STRAIN_UNSUPPORTED_MESSAGE
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
    observed_stages: list[str] = []
    original_set_stage = bridge._set_agent_running_state

    def record_stage(stage: str) -> None:
        observed_stages.append(stage)
        original_set_stage(stage)

    monkeypatch.setattr(bridge, "_set_agent_running_state", record_stage)

    assert bridge.startAgentWorkflow("Build and solve a rectangle"), bridge.statusText

    assert bridge.agentStatus == "COMPLETED"
    assert bridge.agentStage == "RESULT"
    assert bridge.hasSolution
    assert bridge.hasMesh
    assert bridge.nodeCount > 0
    assert bridge.elementCount > 0
    assert bridge.agentProgress == 1.0
    assert bridge.agentAttemptText == "Attempt 1 / 3"
    assert not bridge.isBusy
    assert observed_stages == [
        "ARCHITECT",
        "GEOMETRY",
        "MATERIAL",
        "BC_LOAD",
        "MESH",
        "SOLVE",
    ]
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
    assert "Tx, Ty and Rz" in bridge.agentEvidence
    assert "Fully fix the left edge" in bridge.agentRepairProposalsText
    assert bridge._agent_orchestrator is not None
    assert bridge._agent_orchestrator.state.execution_result is not None
    assert bridge._agent_orchestrator.state.execution_result.stage == "SOLVE"
    assert bridge.agentProgress == 0.94
    assert bridge.agentAttemptText == "Attempt 1 / 3"

    assert bridge.confirmAgentRepair(0)
    assert bridge.agentStatus == "COMPLETED"
    assert bridge.hasSolution
    assert bridge._agent_orchestrator is not None
    assert bridge._agent_orchestrator.state.simulation_plan.version == 2
    assert bridge.agentProgress == 1.0
    assert bridge.agentAttemptText == "Attempt 2 / 3"


def test_agent_bridge_routes_mock_solver_failure_through_reviewer(monkeypatch) -> None:
    pytest.importorskip("gmsh", reason="Agent GUI bridge integration requires gmsh")
    llm = RoutedBridgeLLM()
    monkeypatch.setattr(
        "ui.backend.workbench_bridge.generate_contour_images",
        lambda **_kwargs: {},
    )

    def workflow_factory(project, **kwargs):
        workflow = create_agent_workflow(project, **kwargs)

        def fail_solver(_model):
            raise RuntimeError("deterministic mock singular solve")

        workflow.solver = fail_solver
        return workflow

    bridge = WorkbenchBridge(
        llm_client_factory=lambda: llm,
        workflow_factory=workflow_factory,
    )
    observed_stages: list[str] = []
    original_set_stage = bridge._set_agent_running_state

    def record_stage(stage: str) -> None:
        observed_stages.append(stage)
        original_set_stage(stage)

    monkeypatch.setattr(bridge, "_set_agent_running_state", record_stage)

    assert bridge.startAgentWorkflow("Build a constrained model then mock solve failure")

    assert "SOLVE" in observed_stages
    assert "REVIEW" in observed_stages
    assert bridge.agentStatus == "WAITING_APPROVAL"
    assert bridge.agentStage == "APPROVAL"
    assert bridge.agentNeedsApproval
    assert bridge.agentDiagnosis
    assert bridge.agentEvidence
    assert bridge.agentRepairProposalsText
    assert bridge._agent_orchestrator is not None
    result = bridge._agent_orchestrator.state.execution_result
    assert result is not None
    assert not result.success
    assert result.stage == "SOLVE"
    assert result.error_message == "deterministic mock singular solve"


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
    assert bridge.agentProgress == 0.10
    assert bridge.agentAttemptText == "Attempt 1 / 3"

    assert bridge.startAgentWorkflow("Keep the model and review it again"), bridge.statusText
    assert bridge.agentStatus == "WAITING_APPROVAL"
    assert bridge._agent_orchestrator is not None
    assert bridge._agent_orchestrator.state.simulation_plan.version == 2
    assert bridge.agentProgress == 0.94
    assert bridge.agentAttemptText == "Attempt 1 / 3"


def test_gui_plane_strain_contract_waits_then_uses_architect_revision(monkeypatch) -> None:
    pytest.importorskip("gmsh", reason="Agent GUI capability revision requires gmsh")
    routed = RoutedBridgeLLM()
    architect_modes: list[str] = []
    plan_request_count = 0

    class PlaneModeLLM:
        def request(self, system_prompt: str, user_content: str, schema: dict) -> dict:
            nonlocal plan_request_count
            response = routed.request(system_prompt, user_content, schema)
            if schema.get("title") == "SimulationPlan":
                plan_request_count += 1
                architect_modes.append(json.loads(user_content)["mode"])
                response["material"]["plane_mode"] = (
                    "strain" if plan_request_count == 1 else "stress"
                )
            return response

    monkeypatch.setattr(
        "ui.backend.workbench_bridge.generate_contour_images",
        lambda **_kwargs: {},
    )
    bridge = WorkbenchBridge(llm_client_factory=PlaneModeLLM)

    assert bridge.startAgentWorkflow("Use plane strain")
    assert bridge.agentStatus == "WAITING_USER_INPUT"
    assert bridge.agentStage == "ARCHITECT"
    assert bridge.statusText == PLANE_STRAIN_UNSUPPORTED_MESSAGE
    assert routed.schema_titles == ["SimulationPlan"]
    assert bridge._agent_orchestrator is not None
    assert bridge._agent_orchestrator.state.current_mesh is None

    assert bridge.startAgentWorkflow("Confirm: change to plane stress")
    assert bridge.agentStatus == "COMPLETED"
    assert architect_modes == ["create", "revise"]
    assert bridge._agent_orchestrator.state.simulation_plan.version == 2
    assert bridge._agent_orchestrator.state.simulation_plan.material["plane_mode"] == "stress"

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


def test_agent_progress_mapping_and_failed_state_freeze() -> None:
    bridge = WorkbenchBridge(llm_client_factory=lambda: RoutedBridgeLLM())
    expected = {
        "ARCHITECT": 0.10,
        "GEOMETRY": 0.22,
        "MATERIAL": 0.36,
        "BC_LOAD": 0.50,
        "MESH": 0.65,
        "SOLVE": 0.82,
        "REVIEW": 0.90,
        "APPROVAL": 0.94,
        "RESULT": 1.00,
    }

    assert bridge._agent_progress_for("ARCHITECT", "IDLE", 0.8) == 0.0
    for stage, progress in expected.items():
        assert bridge._agent_progress_for(stage, "RUNNING", 0.0) == progress
    assert bridge._agent_progress_for("MESH", "FAILED", 0.65) == 0.65
    assert bridge._agent_progress_for("RESULT", "COMPLETED", 0.82) == 1.0

    bridge._set_agent_running_state("MESH")
    bridge._handle_agent_worker_failed("expected failure")
    assert bridge.agentStatus == "FAILED"
    assert bridge.agentStage == "MESH"
    assert bridge.agentProgress == 0.65


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
    assert "id: agentProgressTrack" in qml
    assert "id: agentProgressFill" in qml
    assert 'objectName: "agentReviewerDiagnosis"' in qml
    assert 'objectName: "agentReviewerEvidence"' in qml
    assert 'objectName: "agentRepairProposal"' in qml
    assert 'objectName: "agentConfirmButton"' in qml
    assert 'objectName: "agentRejectButton"' in qml
    assert 'bridge.agentStage + " · " + bridge.agentAttemptText' in qml
    assert "agentProgressPopup.displayProgress / 100.0" in qml


def test_agent_progress_visuals_copy_existing_bar_without_refactoring_it() -> None:
    qml = (
        Path(__file__).resolve().parents[2] / "ui" / "qml" / "MainWorkbench.qml"
    ).read_text(encoding="utf-8")

    assert "id: determinateProgressTrack" in qml
    assert "id: determinateProgressFill" in qml
    assert 'Layout.preferredHeight: 6' in qml
    agent_track = qml[qml.index("id: agentProgressTrack"):qml.index("id: agentProgressFill")]
    agent_fill = qml[qml.index("id: agentProgressFill"):qml.index("Behavior on width", qml.index("id: agentProgressFill"))]
    assert "radius: 3" in agent_track
    assert "radius: 3" in agent_fill
    assert qml.count('color: "#E2E8F0"') >= 3
    assert qml.count('GradientStop { position: 0.0; color: "#7FA6D8" }') >= 2
    assert qml.count('GradientStop { position: 0.55; color: "#8FB3DD" }') >= 2
    assert qml.count('GradientStop { position: 1.0; color: "#B8D0EA" }') >= 2
    assert qml.count("duration: 120") >= 2
    assert qml.count("easing.type: Easing.OutCubic") >= 2
    assert qml.count("duration: 1150") >= 2
    assert qml.count("easing.type: Easing.InOutSine") >= 2
    launcher = qml[qml.index("id: agentDialog"):qml.index("id: agentProgressPopup")]
    assert "Timer" not in launcher
    popup = qml[qml.index("id: agentProgressPopup"):qml.index("id: materialEditorDialog")]
    assert "width: Math.min(400, root.width - 32)" in popup
    assert "? Math.min(620, root.height - 48)" in popup
    assert ": Math.min(190, root.height - 48)" in popup
    assert "background: Item" in popup
    assert 'radius: 12' in popup
    assert "id: agentProgressPredictionTimer" in popup
    assert "interval: 16" in popup
    assert "fraction = Math.min(0.94" in popup
    assert "targetProgress = Math.min(targetProgress, range[1] - 0.05)" in popup
    assert 'bridge.agentStatus === "WAITING_APPROVAL"' in popup
    assert 'bridge.agentStatus === "WAITING_USER_INPUT"' in popup
    assert 'bridge.agentStatus === "COMPLETED"' in popup


def test_agent_runtime_uses_worker_and_keeps_existing_busy_progress_separate() -> None:
    launch_source = inspect.getsource(WorkbenchBridge._launch_agent_task)
    start_source = inspect.getsource(WorkbenchBridge.startAgentWorkflow)
    approval_source = inspect.getsource(WorkbenchBridge.confirmAgentRepair)
    apply_source = inspect.getsource(WorkbenchBridge._apply_agent_workflow_payload)

    assert "_launch_worker" in launch_source
    assert "QTimer.singleShot" not in launch_source
    assert "_begin_busy" not in start_source
    assert "_begin_busy" not in approval_source
    assert "_apply_solve_payload" not in apply_source
    assert "_apply_agent_solution_payload" in apply_source


def test_gui_agent_factory_installs_isolated_gmsh_adapter() -> None:
    bridge = WorkbenchBridge(llm_client_factory=lambda: RoutedBridgeLLM())

    workflow = bridge._create_agent_workflow(
        create_empty_workbench_project("isolated_gmsh_adapter")
    )

    wrapped_mesh_generator = workflow.mesh_generator
    assert "observed_mesh_generator" == wrapped_mesh_generator.__name__
    closure_values = [cell.cell_contents for cell in wrapped_mesh_generator.__closure__ or ()]
    assert any(
        getattr(value, "__name__", "") == "generate_agent_mesh_isolated"
        for value in closure_values
    )
