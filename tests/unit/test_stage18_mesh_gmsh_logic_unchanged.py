from __future__ import annotations

import inspect

import ui.backend.workbench_bridge as bridge_module
from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage18_mesh_gmsh_logic_unchanged() -> None:
    bridge_source = inspect.getsource(bridge_module.WorkbenchBridge)
    mesh_source = inspect.getsource(WorkbenchBridge.generateMesh)
    mesh_async_source = inspect.getsource(WorkbenchBridge.generateMeshAsync)

    assert "subprocess" not in bridge_source
    assert "generateQualityMeshForActivePart" in mesh_source
    assert "_run_generate_mesh_sync_after_overlay" in mesh_async_source
    assert "QTimer.singleShot(350" in mesh_async_source
    assert "_launch_worker" not in mesh_async_source
