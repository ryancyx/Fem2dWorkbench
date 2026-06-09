from __future__ import annotations

import json
from pathlib import Path

from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage18_solve_generates_all_contour_images() -> None:
    bridge = WorkbenchBridge()
    assert bridge.createDefaultProject(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0), bridge.statusText
    assert bridge.solveCurrentProject(4, 2), bridge.statusText

    assert bridge.hasSolution
    assert bridge.contourCacheValid
    assert bridge.contourImageCacheValid

    image_map = json.loads(bridge.contourImageCacheJson)
    for group in ("deformation_preview", "displacement", "stress_exact", "stress_smooth"):
        variants = image_map[group]
        assert set(variants.keys()) == {
            "grid_on_deformed_on",
            "grid_on_deformed_off",
            "grid_off_deformed_on",
            "grid_off_deformed_off",
        }
        for file_path in variants.values():
            path = Path(file_path)
            assert path.exists()
            assert path.stat().st_size > 0
