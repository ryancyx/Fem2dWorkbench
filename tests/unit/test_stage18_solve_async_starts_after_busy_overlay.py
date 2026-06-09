from __future__ import annotations

import inspect

from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage18_solve_async_starts_after_busy_overlay() -> None:
    source = inspect.getsource(WorkbenchBridge.solveCurrentModelAsync)

    assert "_begin_busy(" in source
    assert "QTimer.singleShot(80, self._prepare_and_start_solve_worker)" in source
    assert "copy.deepcopy" not in source
    assert "compile_workbench_project" not in source
    assert "solve_workbench_project" not in source
    assert "generate_contour_images" not in source
    assert "json.dumps" not in source
