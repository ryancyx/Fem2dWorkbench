from __future__ import annotations

import json
from pathlib import Path

from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage18_contour_image_cache_generation_after_solve() -> None:
    bridge = WorkbenchBridge()
    assert bridge.createDefaultProject(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0), bridge.statusText
    assert bridge.solveCurrentProject(4, 2), bridge.statusText

    assert bridge.contourImageCacheValid
    assert bridge.contourImageCacheDir
    assert Path(bridge.contourImageCacheDir).exists()

    image_map = json.loads(bridge.contourImageCacheJson)
    groups = ["deformation_preview", "displacement", "stress_exact", "stress_smooth"]
    variants = [
        "grid_on_deformed_on",
        "grid_on_deformed_off",
        "grid_off_deformed_on",
        "grid_off_deformed_off",
    ]
    assert set(image_map.keys()) >= set(groups)
    assert sum(len(image_map[group]) for group in groups) >= 16

    for group in groups:
        for variant in variants:
            file_path = Path(image_map[group][variant])
            assert file_path.exists(), f"missing image: {group}/{variant}"
            assert file_path.stat().st_size > 0, f"empty image: {group}/{variant}"
