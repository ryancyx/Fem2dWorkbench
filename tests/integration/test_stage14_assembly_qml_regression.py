from __future__ import annotations

from pathlib import Path


QML = Path(__file__).resolve().parents[2] / "ui" / "qml" / "MainWorkbench.qml"


def test_stage14_legacy_assembly_entries_are_removed_from_qml():
    text = QML.read_text(encoding="utf-8")

    for snippet in (
        "bridge.addInstanceForPart",
        "bridge.instanceOptions",
        "assemblyInstancesJson",
        "drawAssemblyGeometry",
        "drawAssemblyInstance",
        'text: "装配"',
        "装配实例编辑",
    ):
        assert snippet not in text
