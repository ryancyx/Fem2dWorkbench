from __future__ import annotations

from pathlib import Path


def test_stage18_qml_professional_contour_regression() -> None:
    qml_text = Path("ui/qml/MainWorkbench.qml").read_text(encoding="utf-8", errors="ignore")

    assert "变形示意图" in qml_text
    assert "位移云图" in qml_text
    assert "应力云图" in qml_text
    assert "deformationPlotDialog" in qml_text
    assert "displacementContourDialog" in qml_text
    assert "stressContourDialog" in qml_text
    assert "精确模式（单元常值）" in qml_text
    assert "平滑模式（节点平均）" in qml_text
    assert "drawColorLegend" in qml_text
    assert "contourColor" in qml_text
    assert "interpolateColor" in qml_text
    assert "导出位移云图数据" in qml_text
    assert "导出应力云图数据" in qml_text
