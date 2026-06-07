from __future__ import annotations

from pathlib import Path


QML = Path(__file__).resolve().parents[2] / "ui" / "qml" / "MainWorkbench.qml"


def test_stage15_qml_contains_constraint_and_load_visual_helpers():
    text = QML.read_text(encoding="utf-8")

    for snippet in (
        "function materialFillColor",
        "function drawArrowToTarget",
        "function drawDistributedLoadOnEdge",
        "function drawBoundaryLayer",
        "function drawLoadLayer",
        "当前目标",
        "添加约束",
        "添加集中力",
        "添加均布载荷",
    ):
        assert snippet in text
