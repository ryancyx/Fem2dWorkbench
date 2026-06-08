from __future__ import annotations

import json

import pytest

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
    return point_ids


@pytest.mark.integration
def test_stage18_multiple_faces_material_workflow() -> None:
    pytest.importorskip("gmsh", reason="multi-face workflow requires gmsh backend")

    bridge = WorkbenchBridge()
    assert bridge.newProject(), bridge.statusText
    point_ids = _build_two_disjoint_rectangles(bridge)

    assert bridge.buildModelFaces(), bridge.statusText
    assert bridge.modelFaceCount == 2
    assert "2" in bridge.statusText

    assert bridge.addMaterial("aluminum", 70_000_000_000.0, 0.33, "#A8C5E6"), bridge.statusText
    steel_id = _material_id_by_name(bridge, "steel")
    aluminum_id = _material_id_by_name(bridge, "aluminum")

    assert bridge.selectGeometryFace("f1"), bridge.statusText
    assert bridge.assignMaterialToSelectedFace(steel_id, 0.01), bridge.statusText
    assert bridge.selectGeometryFace("f2"), bridge.statusText
    assert bridge.assignMaterialToSelectedFace(aluminum_id, 0.02), bridge.statusText

    face_rows = _json_list(bridge.faceMaterialJson)
    by_face = {row["face_id"]: row for row in face_rows}
    assert by_face["f1"]["material_id"] != by_face["f2"]["material_id"]

    assert bridge.generateMesh(0.25, 25.0), bridge.statusText
    source_face_ids = {row["source_face_id"] for row in _json_list(bridge.meshElementsJson)}
    assert {"f1", "f2"} <= source_face_ids

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

    solve_ok = bridge.solveCurrentModel()
    if solve_ok:
        assert bridge.hasSolution
        assert bridge.nodeCount > 0
        assert bridge.elementCount > 0
    else:
        assert "奇异" in bridge.statusText or "约束" in bridge.statusText or "连接" in bridge.statusText
