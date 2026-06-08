from __future__ import annotations

import json
from pathlib import Path

from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage18_material_unit_weight_workflow(tmp_path: Path) -> None:
    bridge = WorkbenchBridge()
    assert bridge.newProject(), bridge.statusText

    assert bridge.addMaterial(
        "heavy",
        123_000_000_000.0,
        0.29,
        "#123456",
        54321.0,
    ), bridge.statusText

    material_id = next(option.split("|", 1)[0].strip() for option in bridge.materialOptions if "heavy" in option)
    assert "γ=54321" in bridge.materialRowsPreview

    assert bridge.updateMaterial(
        material_id,
        "heavy",
        123_000_000_000.0,
        0.29,
        "#123456",
        65432.0,
    ), bridge.statusText
    assert "γ=65432" in bridge.materialRowsPreview

    project_path = tmp_path / "material_unit_weight.f2dw.json"
    assert bridge.saveCurrentProject(str(project_path)), bridge.statusText
    saved = json.loads(project_path.read_text(encoding="utf-8"))
    heavy_row = next(row for row in saved["materials"] if row["id"] == material_id)
    assert heavy_row["unit_weight"] == 65432.0

    reloaded = WorkbenchBridge()
    assert reloaded.loadProject(str(project_path)), reloaded.statusText
    heavy_material = next(material for material in reloaded.current_project.materials if material.id == material_id)
    assert heavy_material.unit_weight == 65432.0

    qml_text = (Path(__file__).resolve().parents[2] / "ui" / "qml" / "MainWorkbench.qml").read_text(
        encoding="utf-8",
        errors="ignore",
    )
    assert "materialUnitWeightField" in qml_text
    assert "容重" in qml_text
    assert "N/m³" in qml_text
