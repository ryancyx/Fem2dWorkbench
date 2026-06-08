from __future__ import annotations

import json

from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage18_contour_cache_generation_after_solve() -> None:
    bridge = WorkbenchBridge()
    assert bridge.createDefaultProject(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0), bridge.statusText
    assert bridge.solveCurrentProject(4, 2), bridge.statusText

    assert bridge.hasSolution
    assert bridge.contourCacheValid
    assert json.loads(bridge.deformationPreviewJson)
    assert json.loads(bridge.displacementContourJson)
    assert json.loads(bridge.stressContourExactJson)
    assert json.loads(bridge.stressContourSmoothJson)
    assert "云图缓存" in bridge.statusText
