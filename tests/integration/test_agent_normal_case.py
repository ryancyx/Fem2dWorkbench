from __future__ import annotations

import json
import pytest

from agent.architect_agent import ArchitectAgent
from agent.bc_load_agent import BCLoadAgent
from agent.geometry_agent import GeometryAgent
from agent.material_agent import MaterialAgent
from agent.workflow_orchestrator import WorkflowOrchestrator
from agent.workflow_state import WorkflowStatus
from services.project_factory_service import create_empty_workbench_project


class RoutedFakeLLM:
    def __init__(self, response: dict) -> None:
        self.response = response

    def request(self, system_prompt: str, user_content: str, schema: dict) -> dict:
        title = schema.get("title")
        content = json.loads(user_content)
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
                    {"action": "create_material", "name": material["name"], "E": material["E"], "nu": material["nu"]},
                    {"action": "assign_material", "name": material["name"], "thickness": material["thickness"], "plane_mode": material["plane_mode"]},
                ]
            }
        if title == "BCLoadActions":
            rows = content["constraintsAndLoads"]
            return {
                "actions": [
                    *({"action": "add_point_constraint", **row} for row in rows["pointConstraints"]),
                    *({"action": "add_edge_constraint", **row} for row in rows["edgeConstraints"]),
                    *({"action": "add_point_load", **row} for row in rows["pointLoads"]),
                    *({"action": "add_edge_load", **row} for row in rows["edgeLoads"]),
                ]
            }
        return self.response


@pytest.mark.integration
def test_agent_gmsh_solver_success_path_uses_real_project_state() -> None:
    pytest.importorskip("gmsh", reason="Agent integration requires gmsh backend")
    response = {
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
        "edgeConstraints": [
            {"target": {"selector": "left"}, "ux": 0.0, "uy": 0.0}
        ],
        "pointLoads": [],
        "edgeLoads": [
            {"target": {"selector": "right"}, "vector": [1000.0, 0.0]}
        ],
        "meshSize": 0.35,
        "requestedResult": "von_mises",
    }
    llm = RoutedFakeLLM(response)
    project = create_empty_workbench_project("agent_real_path")
    orchestrator = WorkflowOrchestrator(
        project=project,
        architect_agent=ArchitectAgent(llm),
        geometry_agent=GeometryAgent(llm),
        material_agent=MaterialAgent(llm),
        bc_load_agent=BCLoadAgent(llm),
    )

    state = orchestrator.start("Create and solve a rectangle")

    assert state.status == WorkflowStatus.COMPLETED
    assert state.current_mesh is not None
    assert state.current_mesh.metadata["mesh_type"] == "gmsh_cst"
    assert len(state.current_mesh.nodes) > 0
    assert len(state.current_mesh.elements) > 0
    assert len(project.boundary_conditions) == 1
    assert len(project.loads) == 1
    assert state.execution_result is not None and state.execution_result.success
    assert state.result_data is not None
    assert state.result_data["summary"]["max_displacement"] > 0.0
    assert state.result_data["summary"]["max_von_mises"] > 0.0
