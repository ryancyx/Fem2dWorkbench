from __future__ import annotations

import pytest

from ui.backend.workbench_bridge import WorkbenchBridge


def _bootstrap_rectangle_project(bridge: WorkbenchBridge) -> None:
    assert bridge.updateCurrentProjectParameters(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0, 4, 2) is True


def test_instance_options_include_precise_transform_values():
    bridge = WorkbenchBridge()
    assert bridge.newProject() is True
    _bootstrap_rectangle_project(bridge)
    assert bridge.addRectanglePart("part2", 3.0, 1.5) is True
    assert bridge.addInstanceForPart(bridge.activePartId, "part2 instance", 0.0, 0.0) is True

    assert bridge.moveActiveInstance(1.25, -0.75) is True

    assert bridge.activeInstanceTx == pytest.approx(1.25)
    assert bridge.activeInstanceTy == pytest.approx(-0.75)
    assert any("tx=1.250" in option and "ty=-0.750" in option for option in bridge.instanceOptions)


def test_add_instance_requires_selected_part():
    bridge = WorkbenchBridge()
    assert bridge.newProject() is True
    _bootstrap_rectangle_project(bridge)

    assert bridge.addInstanceForPart("", "bad", 0.0, 0.0) is False
    assert "选择零件" in bridge.statusText
