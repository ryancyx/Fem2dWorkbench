from __future__ import annotations

import json
from pathlib import Path

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


def _find_edge_by_point_ids(bridge: WorkbenchBridge, start_point_id: str, end_point_id: str) -> str:
    for edge in _json_list(bridge.modelEdgesJson):
        if edge["start_point_id"] == start_point_id and edge["end_point_id"] == end_point_id:
            return edge["id"]
    raise AssertionError(f"edge {start_point_id}->{end_point_id} not found")


def _build_rectangle_model(bridge: WorkbenchBridge) -> None:
    for x, y in ((0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)):
        assert bridge.addModelPoint(x, y), bridge.statusText
    point_ids = [point["id"] for point in _json_list(bridge.modelPointsJson)]
    p1, p2, p3, p4 = point_ids
    for start_id, end_id in ((p1, p2), (p2, p3), (p3, p4), (p4, p1)):
        assert bridge.connectModelEdge(start_id, end_id), bridge.statusText
    assert bridge.buildModelFaces(), bridge.statusText


@pytest.mark.integration
def test_stage18_solve_generates_contour_cache() -> None:
    pytest.importorskip("gmsh", reason="contour cache integration requires gmsh backend")

    bridge = WorkbenchBridge()
    assert bridge.newProject(), bridge.statusText
    _build_rectangle_model(bridge)

    steel_id = _material_id_by_name(bridge, "steel")
    face_id = _json_list(bridge.modelFacesJson)[0]["id"]
    assert bridge.selectGeometryFace(face_id), bridge.statusText
    assert bridge.assignMaterialToSelectedFace(steel_id, 0.01), bridge.statusText
    assert bridge.generateMesh(0.25, 25.0), bridge.statusText

    points = _json_list(bridge.modelPointsJson)
    p1, p2, p3, p4 = [point["id"] for point in points]
    left_edge_id = _find_edge_by_point_ids(bridge, p4, p1)
    right_edge_id = _find_edge_by_point_ids(bridge, p2, p3)
    assert bridge.selectGeometryEdge(left_edge_id), bridge.statusText
    assert bridge.addConstraintToSelectedTarget(True, True), bridge.statusText
    assert bridge.selectGeometryEdge(right_edge_id), bridge.statusText
    assert bridge.addLoadToSelectedTarget("edge_uniform", 0.0, -1000.0), bridge.statusText

    assert bridge.solveCurrentModel(), bridge.statusText
    assert bridge.hasSolution
    assert bridge.contourCacheValid
    assert bridge.contourImageCacheValid
    assert json.loads(bridge.deformationPreviewJson)
    assert json.loads(bridge.displacementContourJson)
    assert json.loads(bridge.stressContourExactJson)
    assert json.loads(bridge.stressContourSmoothJson)
    assert json.loads(bridge.contourImageCacheJson)
