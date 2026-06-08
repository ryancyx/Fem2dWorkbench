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


def _build_two_disjoint_rectangles(bridge: WorkbenchBridge) -> list[str]:
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
    point_ids = [point["id"] for point in _json_list(bridge.modelPointsJson)]
    left = point_ids[:4]
    right = point_ids[4:]
    for start_id, end_id in (
        (left[0], left[1]),
        (left[1], left[2]),
        (left[2], left[3]),
        (left[3], left[0]),
        (right[0], right[1]),
        (right[1], right[2]),
        (right[2], right[3]),
        (right[3], right[0]),
    ):
        assert bridge.connectModelEdge(start_id, end_id), bridge.statusText
    assert bridge.buildModelFaces(), bridge.statusText
    return point_ids


@pytest.mark.integration
def test_stage18_multiple_faces_gmsh_solve_uses_face_materials() -> None:
    pytest.importorskip("gmsh", reason="multi-face gmsh integration requires gmsh backend")

    bridge = WorkbenchBridge()
    assert bridge.newProject(), bridge.statusText
    point_ids = _build_two_disjoint_rectangles(bridge)
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
    left_fixed_edge = _edge_id_by_points(bridge, left[3], left[0])
    right_loaded_edge = _edge_id_by_points(bridge, left[1], left[2])
    second_left_fixed_edge = _edge_id_by_points(bridge, right[3], right[0])
    second_right_loaded_edge = _edge_id_by_points(bridge, right[1], right[2])

    assert bridge.selectGeometryEdge(left_fixed_edge), bridge.statusText
    assert bridge.addConstraintToSelectedTarget(True, True), bridge.statusText
    assert bridge.selectGeometryEdge(second_left_fixed_edge), bridge.statusText
    assert bridge.addConstraintToSelectedTarget(True, True), bridge.statusText
    assert bridge.selectGeometryEdge(right_loaded_edge), bridge.statusText
    assert bridge.addLoadToSelectedTarget("edge_uniform", 0.0, -1000.0), bridge.statusText
    assert bridge.selectGeometryEdge(second_right_loaded_edge), bridge.statusText
    assert bridge.addLoadToSelectedTarget("edge_uniform", 0.0, -1000.0), bridge.statusText

    assert bridge.current_sketch_mesh is not None
    part = bridge._require_active_part()
    compiled = compile_workbench_project(
        project=bridge.current_project,
        mesh=bridge.current_sketch_mesh,
        step_id="step_static",
    )
    material_id_by_element_id = {
        element.id: element.material_id for element in compiled.fem_model.elements
    }
    face_material_ids: dict[str, set[int]] = {"f1": set(), "f2": set()}
    for mesh_element in bridge.current_sketch_mesh.elements:
        assert mesh_element.source_face_id in face_material_ids
        face_material_ids[mesh_element.source_face_id].add(material_id_by_element_id[mesh_element.id])
    assert len(face_material_ids["f1"]) == 1
    assert len(face_material_ids["f2"]) == 1
    assert face_material_ids["f1"] != face_material_ids["f2"]
    assert part.geometry.faces[0].section_id != part.geometry.faces[1].section_id

    assert bridge.solveCurrentModel(), bridge.statusText
    assert bridge.hasSolution
    assert bridge.nodeCount > 0
    assert bridge.elementCount > 0
