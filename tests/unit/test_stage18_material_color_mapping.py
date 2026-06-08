from __future__ import annotations

import json
from pathlib import Path

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


def _build_two_rectangles(bridge: WorkbenchBridge) -> None:
    for x, y in (
        (0.0, 0.0),
        (2.0, 0.0),
        (2.0, 1.0),
        (0.0, 1.0),
        (3.0, 0.0),
        (4.0, 0.0),
        (4.0, 1.0),
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


def test_stage18_material_color_mapping_per_face_and_qml_usage() -> None:
    bridge = WorkbenchBridge()
    assert bridge.newProject(), bridge.statusText
    _build_two_rectangles(bridge)
    assert bridge.addMaterial("aluminum", 70_000_000_000.0, 0.33, "#A8C5E6"), bridge.statusText

    steel_id = _material_id_by_name(bridge, "steel")
    aluminum_id = _material_id_by_name(bridge, "aluminum")
    assert bridge.selectGeometryFace("f1"), bridge.statusText
    assert bridge.assignMaterialToSelectedFace(steel_id, 0.01), bridge.statusText
    assert bridge.selectGeometryFace("f2"), bridge.statusText
    assert bridge.assignMaterialToSelectedFace(aluminum_id, 0.02), bridge.statusText

    rows = _json_list(bridge.faceMaterialJson)
    rows_by_face = {row["face_id"]: row for row in rows}
    assert rows_by_face["f1"]["material_color"] != rows_by_face["f2"]["material_color"]
    assert rows_by_face["f1"]["material_color"] == "#8FB7D8"
    assert rows_by_face["f2"]["material_color"] == "#A8C5E6"

    qml_text = (Path(__file__).resolve().parents[2] / "ui" / "qml" / "MainWorkbench.qml").read_text(
        encoding="utf-8",
        errors="ignore",
    )
    assert "faceMaterialJson" in qml_text or "faceMaterialRows()" in qml_text
    assert "material_color" in qml_text
    assert "function faceMaterialColor" in qml_text
