from __future__ import annotations

import pytest

from ui.backend.workbench_bridge import WorkbenchBridge


def _bootstrap_rectangle_project(bridge: WorkbenchBridge) -> None:
    assert bridge.updateCurrentProjectParameters(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0, 4, 2) is True


def test_assign_material_to_specific_part_without_switching_active_part():
    bridge = WorkbenchBridge()
    assert bridge.newProject() is True
    _bootstrap_rectangle_project(bridge)
    assert bridge.addRectanglePart("part2", 3.0, 1.5) is True
    second_part_id = bridge.activePartId

    assert bridge.addMaterial("aluminum", 70e9, 0.33, "#C0C0C0") is True
    aluminum_id = next(
        option.split("|")[0].strip()
        for option in bridge.materialOptions
        if "aluminum" in option
    )

    assert bridge.assignMaterialToPart("part_rectangle", aluminum_id, 0.02) is True
    assert bridge.activePartId == second_part_id

    assert bridge.setActivePart("part_rectangle") is True
    assert bridge.activePartMaterialId == aluminum_id
    assert bridge.activePartMaterialName == "aluminum"
    assert bridge.activePartThickness == pytest.approx(0.02)

    assert bridge.setActivePart(second_part_id) is True
    assert bridge.activePartMaterialName == "steel"
    assert bridge.activePartThickness == pytest.approx(0.01)


def test_assign_material_to_part_requires_explicit_part_id():
    bridge = WorkbenchBridge()
    assert bridge.newProject() is True
    _bootstrap_rectangle_project(bridge)

    assert bridge.assignMaterialToPart("", "mat_steel", 0.01) is False
    assert "选择目标零件" in bridge.statusText
