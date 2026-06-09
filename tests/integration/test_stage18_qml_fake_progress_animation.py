from __future__ import annotations

from pathlib import Path


def test_stage18_qml_fake_progress_animation() -> None:
    qml_text = Path("ui/qml/MainWorkbench.qml").read_text(encoding="utf-8", errors="ignore")

    assert "function fakeProgressAt(elapsedMs, estimatedMs, holdProgress)" in qml_text
    assert "Date.now()" in qml_text
    assert "bridge.busyEstimatedMs" in qml_text
    assert "bridge.busyHoldProgress" in qml_text
    assert "id: fakeProgressTimer" in qml_text
    assert "interval: 16" in qml_text
    assert "value: busyOverlay.busyVisualProgress" in qml_text
    assert "bridge.busyProgressMode === \"fake_determinate\"" in qml_text
