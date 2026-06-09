from __future__ import annotations

import inspect

from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage18_busy_fake_progress_properties_exist() -> None:
    bridge = WorkbenchBridge()
    assert hasattr(bridge, "busyProgressMode")
    assert hasattr(bridge, "busyEstimatedMs")
    assert hasattr(bridge, "busyHoldProgress")


def test_stage18_busy_fake_progress_defaults_and_async_settings() -> None:
    bridge = WorkbenchBridge()
    assert bridge.busyProgressMode == "determinate"
    assert bridge.busyEstimatedMs == 0
    assert 0 <= bridge.busyHoldProgress <= 100

    mesh_source = inspect.getsource(WorkbenchBridge.generateMeshAsync)
    solve_source = inspect.getsource(WorkbenchBridge.solveCurrentModelAsync)

    assert 'progress_mode="fake_determinate"' in mesh_source
    assert 'estimated_ms=1800' in mesh_source
    assert 'hold_progress=85' in mesh_source
    assert 'progress_mode="fake_determinate"' in solve_source
    assert 'estimated_ms=7000' in solve_source
    assert 'hold_progress=97' in solve_source
