from __future__ import annotations

from pathlib import Path


def test_stage18_qml_busy_overlay_regression() -> None:
    qml_text = Path("ui/qml/MainWorkbench.qml").read_text(encoding="utf-8", errors="ignore")

    assert "id: busyOverlay" in qml_text
    assert "ProgressBar" in qml_text
    assert "value: bridge.busyProgress" in qml_text
    assert "visible: bridge.isBusy" in qml_text
    assert "text: bridge.busyTitle" in qml_text
    assert "text: bridge.busyMessage" in qml_text
