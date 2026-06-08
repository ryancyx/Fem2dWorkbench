from __future__ import annotations

import json

import pytest

from core.compiler.project_to_fem import compile_project_to_fem
from core.engineering.engineering_project import EngineeringProject
from ui.backend.workbench_bridge import WorkbenchBridge


def _json_list(text: str) -> list[dict]:
    data = json.loads(text)
    assert isinstance(data, list)
    return data


def _parse_option_id(option_text: str) -> str:
    return str(option_text).split("|", 1)[0].strip()


def _build_rectangle_model(bridge: WorkbenchBridge) -> list[str]:
    for x, y in ((0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)):
        assert bridge.addModelPoint(x, y), bridge.statusText
    point_ids = [point["id"] for point in _json_list(bridge.modelPointsJson)]
    p1, p2, p3, p4 = point_ids
    for start_id, end_id in ((p1, p2), (p2, p3), (p3, p4), (p4, p1)):
        assert bridge.connectModelEdge(start_id, end_id), bridge.statusText
    assert bridge.buildModelFaces(), bridge.statusText
    return point_ids


@pytest.mark.integration
def test_stage18_gravity_solve_workflow() -> None:
    pytest.importorskip("gmsh", reason="gravity workflow uses current mesh backend")

    bridge = WorkbenchBridge()
    assert bridge.newProject(), bridge.statusText
    point_ids = _build_rectangle_model(bridge)

    assert bridge.addMaterial(
        "heavy",
        210_000_000_000.0,
        0.3,
        "#8FB7D8",
        1000.0,
    ), bridge.statusText
    material_id = next(_parse_option_id(option) for option in bridge.materialOptions if "heavy" in option)
    face_id = _json_list(bridge.modelFacesJson)[0]["id"]
    assert bridge.selectGeometryFace(face_id), bridge.statusText
    assert bridge.assignMaterialToSelectedFace(material_id, 0.1), bridge.statusText
    assert bridge.generateMesh(0.25, 25.0), bridge.statusText

    p1, _p2, _p3, p4 = point_ids
    left_edge_id = next(
        row["id"]
        for row in _json_list(bridge.modelEdgesJson)
        if {row["start_point_id"], row["end_point_id"]} == {p1, p4}
    )
    assert bridge.selectGeometryEdge(left_edge_id), bridge.statusText
    assert bridge.addConstraintToSelectedTarget(True, True), bridge.statusText

    assert bridge.setGravityEnabled(True), bridge.statusText
    assert bridge.gravityEnabled
    assert bridge.solveCurrentModel(), bridge.statusText
    assert bridge.hasSolution
    assert bridge.nodeCount > 0
    assert bridge.elementCount > 0

    enabled_project = EngineeringProject(
        name="enabled",
        materials=list(bridge.current_project.materials),
        sections=list(bridge.current_project.sections),
        parts=[bridge._require_active_part()],
        assembly=bridge.current_project.assembly,
        analysis_steps=list(bridge.current_project.analysis_steps),
        loads=list(bridge.current_project.loads),
        boundary_conditions=list(bridge.current_project.boundary_conditions),
        metadata=dict(bridge.current_project.metadata),
    )
    compiled_enabled = compile_project_to_fem(enabled_project, bridge.current_sketch_mesh, bridge._default_step_id())
    total_enabled_fy = sum(load.fy for load in compiled_enabled.fem_model.loads)
    assert total_enabled_fy < 0.0

    disabled_metadata = dict(bridge.current_project.metadata)
    disabled_metadata["gravity_enabled"] = False
    disabled_project = EngineeringProject(
        name="disabled",
        materials=list(bridge.current_project.materials),
        sections=list(bridge.current_project.sections),
        parts=[bridge._require_active_part()],
        assembly=bridge.current_project.assembly,
        analysis_steps=list(bridge.current_project.analysis_steps),
        loads=list(bridge.current_project.loads),
        boundary_conditions=list(bridge.current_project.boundary_conditions),
        metadata=disabled_metadata,
    )
    compiled_disabled = compile_project_to_fem(disabled_project, bridge.current_sketch_mesh, bridge._default_step_id())
    total_disabled_fy = sum(load.fy for load in compiled_disabled.fem_model.loads)
    assert total_disabled_fy == pytest.approx(0.0)
