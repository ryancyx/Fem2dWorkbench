from __future__ import annotations

import inspect

import ui.backend.workbench_bridge as bridge_module
from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage18_generate_mesh_async_runs_sync_after_overlay() -> None:
    source = inspect.getsource(WorkbenchBridge.generateMeshAsync)
    assert "_run_generate_mesh_sync_after_overlay" in source
    assert "_start_mesh_worker" not in source


def test_stage18_no_mesh_worker_entry_left_for_gmsh() -> None:
    bridge_source = inspect.getsource(bridge_module.WorkbenchBridge)
    assert "def _start_mesh_worker" not in bridge_source
    assert "def _build_mesh_payload" not in bridge_source
