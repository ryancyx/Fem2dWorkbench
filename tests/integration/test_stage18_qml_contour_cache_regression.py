from __future__ import annotations

from pathlib import Path


def test_stage18_qml_contour_cache_regression() -> None:
    qml_text = Path("ui/qml/MainWorkbench.qml").read_text(encoding="utf-8", errors="ignore")

    assert "ensureContourCacheAvailable()" in qml_text
    assert "bridge.contourCacheValid" in qml_text
    assert "bridge.deformationPreviewJson" in qml_text
    assert "bridge.displacementContourJson" in qml_text
    assert "bridge.stressContourExactJson" in qml_text
    assert "bridge.stressContourSmoothJson" in qml_text
    assert "deformationPlotDialog.open()" in qml_text
    assert "displacementContourDialog.open()" in qml_text
    assert "stressContourDialog.open()" in qml_text
    assert "build_displacement_contour_data" not in qml_text
    assert "build_stress_contour_data" not in qml_text
