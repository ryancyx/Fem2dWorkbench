from __future__ import annotations

import ui.backend.workbench_bridge as bridge_module
from core.engineering.mesh_model import MeshElement, MeshModel, MeshNode
from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage18_busy_state_fields_and_reset(monkeypatch) -> None:
    mesh = MeshModel(
        nodes=[
            MeshNode(id=1, x=0.0, y=0.0),
            MeshNode(id=2, x=1.0, y=0.0),
            MeshNode(id=3, x=0.0, y=1.0),
        ],
        elements=[MeshElement(id=1, node_ids=[1, 2, 3], source_face_id="f1")],
        metadata={"mesh_type": "sketch_quality"},
    )
    bridge = WorkbenchBridge()
    assert bridge.createDefaultProject(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0), bridge.statusText

    history: list[tuple[bool, str, str, int, bool, str]] = []
    original = bridge._set_busy_state

    def record(active: bool, title: str, message: str, progress: int, stage: str, indeterminate=None) -> None:
        history.append((active, title, message, progress, bool(indeterminate), stage))
        original(active, title, message, progress, stage, indeterminate)

    bridge._set_busy_state = record  # type: ignore[method-assign]
    monkeypatch.setattr(bridge_module, "generate_quality_sketch_tri_mesh", lambda *args, **kwargs: mesh)

    assert bridge.generateMesh(0.25, 25.0), bridge.statusText
    assert history
    assert any(item[1] == "正在生成网格" for item in history)
    assert all(0 <= item[3] <= 100 for item in history)
    assert bridge.isBusy is False
    assert bridge.busyIndeterminate is False
    assert bridge.busyProgress == 0


def test_stage18_busy_state_rejects_reentry() -> None:
    bridge = WorkbenchBridge()
    bridge._begin_busy("正在求解", "准备求解...", "solve", 0, indeterminate=True)
    assert bridge.generateMeshAsync(0.25, 25.0) is False
    assert bridge.solveCurrentModelAsync() is False
    assert "当前任务正在进行" in bridge.statusText
    bridge._finish_busy()
