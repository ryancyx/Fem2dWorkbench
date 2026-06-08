from __future__ import annotations

from pathlib import Path


def test_stage18_qml_contour_regression() -> None:
    qml_text = (Path(__file__).resolve().parents[2] / "ui" / "qml" / "MainWorkbench.qml").read_text(
        encoding="utf-8",
        errors="ignore",
    )
    assert "displacementContourDialog" in qml_text
    assert "stressContourDialog" in qml_text
    assert "显示位移云图" in qml_text
    assert "显示应力云图" in qml_text
    assert "精确模式" in qml_text
    assert "平滑模式" in qml_text
    assert "导出位移云图数据" in qml_text
    assert "导出应力云图数据" in qml_text
