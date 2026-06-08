from __future__ import annotations

import json

import pytest

from services.compile_service import compile_workbench_project
from ui.backend.workbench_bridge import WorkbenchBridge


def _json_list(text: str) -> list[dict]:
    data = json.loads(text)
    assert isinstance(data, list)
    return data


def _material_id_by_name(bridge: WorkbenchBridge, material_name: str) -> str:
    for option in bridge.materialOptions:
        material_id, _, label = option.partition("|")
        if material_name in label:
            return material_id.strip()
    raise AssertionError(f"material {material_name!r} not found")


def _edge_id_by_points(bridge: WorkbenchBridge, start_point_id: str, end_point_id: str) -> str:
    for edge in _json_list(bridge.modelEdgesJson):
        if edge["start_point_id"] == start_point_id and edge["end_point_id"] == end_point_id:
            return edge["id"]
    raise AssertionError(f"edge {start_point_id}->{end_point_id} not found")


def _build_two_rectangles(bridge: WorkbenchBridge) -> list[str]:
    for x, y in (
        (0.0, 0.0),
        (2.0, 0.0),
        (2.0, 1.0),
        (0.0, 1.0),
        (3.0, 0.0),
        (4.5, 0.0),
        (4.5, 1.0),
        (3.0, 1.0),
    ):
        assert bridge.addModelPoint(x, y), bridge.statusText
    point_ids = [row["id"] for row in _json_list(bridge.modelPointsJson)]
    for start_id, end_id in (
        (point_ids[0], point_ids[1]),
        (point_ids[1], point_ids[2]),
        (point_ids[2], point_ids[3]),
        (point_ids[3], point_ids[0]),
        (point_ids[4], point_ids[5]),
        (point_ids[5], point_ids[6]),
        (point_ids[6], point_ids[7]),
        (point_ids[7], point_ids[4]),
    ):
        assert bridge.connectModelEdge(start_id, end_id), bridge.statusText
    assert bridge.buildModelFaces(), bridge.statusText
    return point_ids


@pytest.mark.integration
def test_stage18_multiple_faces_material_solve() -> None:
    pytest.importorskip("gmsh", reason="multi-face material solve requires gmsh backend")

    bridge = WorkbenchBridge()
    assert bridge.newProject(), bridge.statusText
    point_ids = _build_two_rectangles(bridge)
    assert bridge.addMaterial("aluminum", 70_000_000_000.0, 0.33, "#A8C5E6"), bridge.statusText

    steel_id = _material_id_by_name(bridge, "steel")
    aluminum_id = _material_id_by_name(bridge, "aluminum")
    assert bridge.selectGeometryFace("f1"), bridge.statusText
    assert bridge.assignMaterialToSelectedFace(steel_id, 0.01), bridge.statusText
    assert bridge.selectGeometryFace("f2"), bridge.statusText
    assert bridge.assignMaterialToSelectedFace(aluminum_id, 0.02), bridge.statusText

    assert bridge.generateMesh(0.25, 25.0), bridge.statusText
    mesh_elements = _json_list(bridge.meshElementsJson)
    assert {"f1", "f2"} <= {row["source_face_id"] for row in mesh_elements}

    left = point_ids[:4]
    right = point_ids[4:]
    assert bridge.selectGeometryEdge(_edge_id_by_points(bridge, left[3], left[0])), bridge.statusText
    assert bridge.addConstraintToSelectedTarget(True, True), bridge.statusText
    assert bridge.selectGeometryEdge(_edge_id_by_points(bridge, right[3], right[0])), bridge.statusText
    assert bridge.addConstraintToSelectedTarget(True, True), bridge.statusText
    assert bridge.selectGeometryEdge(_edge_id_by_points(bridge, left[1], left[2])), bridge.statusText
    assert bridge.addLoadToSelectedTarget("edge_uniform", 0.0, -1000.0), bridge.statusText
    assert bridge.selectGeometryEdge(_edge_id_by_points(bridge, right[1], right[2])), bridge.statusText
    assert bridge.addLoadToSelectedTarget("edge_uniform", 0.0, -1000.0), bridge.statusText

    compiled = compile_workbench_project(
        project=bridge.current_project,
        mesh=bridge.current_sketch_mesh,
        step_id="step_static",
    )
    fem_material_id_by_element_id = {element.id: element.material_id for element in compiled.fem_model.elements}
    face_material_ids: dict[str, set[int]] = {"f1": set(), "f2": set()}
    for element in bridge.current_sketch_mesh.elements:
        face_material_ids[element.source_face_id].add(fem_material_id_by_element_id[element.id])
    assert len(face_material_ids["f1"]) == 1
    assert len(face_material_ids["f2"]) == 1
    assert face_material_ids["f1"] != face_material_ids["f2"]

    assert bridge.solveCurrentModel(), bridge.statusText
    assert bridge.hasSolution
