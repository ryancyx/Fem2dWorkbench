from __future__ import annotations

from pathlib import Path


def test_stage18_qml_face_hit_test_regression() -> None:
    qml_path = Path("ui/qml/MainWorkbench.qml")
    text = qml_path.read_text(encoding="utf-8")

    assert "function faceScreenPolygon" in text
    assert "faceRow.point_ids" in text
    assert "function findFaceAt" in text
    assert "var faces = modelFaces()" in text
    assert "faceScreenPolygon(faces[i], pointMap)" in text
    assert "bridge.selectGeometryFace(faceId)" in text

