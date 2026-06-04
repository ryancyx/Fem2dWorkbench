from __future__ import annotations

from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage14_part_material_assembly_workflow(tmp_path):
    bridge = WorkbenchBridge()

    assert bridge.newProject() is True
    assert bridge.updateCurrentProjectParameters(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0, 4, 2) is True
    assert bridge.addEmptySketchPart("sketch_part") is True
    sketch_part_id = bridge.activePartId

    assert bridge.addMaterial("aluminum", 70e9, 0.33, "#C0C0C0") is True
    aluminum_id = next(
        option.split("|")[0].strip()
        for option in bridge.materialOptions
        if "aluminum" in option
    )
    assert bridge.assignMaterialToPart(sketch_part_id, aluminum_id, 0.02) is True

    assert bridge.addInstanceForPart(sketch_part_id, "sketch instance", 0.0, 0.0) is True
    assert bridge.moveActiveInstance(2.0, 1.0) is True
    assert bridge.activeInstancePartId == sketch_part_id
    assert bridge.activeInstanceTx == 2.0
    assert bridge.activeInstanceTy == 1.0

    file_path = tmp_path / "part_material_assembly.f2dw.json"
    assert bridge.saveCurrentProject(str(file_path)) is True

    restored = WorkbenchBridge()
    assert restored.loadProject(str(file_path)) is True
    assert restored.activePartId == sketch_part_id
    assert restored.activePartMaterialName == "aluminum"
    assert restored.activePartThickness == 0.02
    assert restored.activeInstancePartId == sketch_part_id
    assert restored.activeInstanceTx == 2.0
    assert restored.activeInstanceTy == 1.0
