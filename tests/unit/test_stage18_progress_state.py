from __future__ import annotations

from core.engineering.mesh_model import MeshElement, MeshModel, MeshNode
import ui.backend.workbench_bridge as bridge_module
from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage18_progress_state_for_mesh_generation_and_solve(monkeypatch) -> None:
    mesh = MeshModel(
        nodes=[
            MeshNode(id=1, x=0.0, y=0.0),
            MeshNode(id=2, x=1.0, y=0.0),
            MeshNode(id=3, x=0.0, y=1.0),
        ],
        elements=[
            MeshElement(id=1, node_ids=[1, 2, 3], source_face_id="f1"),
        ],
        metadata={"mesh_type": "sketch_quality"},
    )

    bridge = WorkbenchBridge()
    assert bridge.createDefaultProject(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0), bridge.statusText

    history: list[tuple[bool, str, str, int, str]] = []
    original_set_busy_state = bridge._set_busy_state

    def recorder(active: bool, title: str, message: str, progress: int, stage: str) -> None:
        history.append((active, title, message, progress, stage))
        original_set_busy_state(active, title, message, progress, stage)

    bridge._set_busy_state = recorder  # type: ignore[method-assign]

    monkeypatch.setattr(bridge_module, "generate_quality_sketch_tri_mesh", lambda *args, **kwargs: mesh)
    assert bridge.generateMesh(0.25, 25.0), bridge.statusText
    assert history
    assert any(item[1] == "正在生成网格" for item in history)
    assert all(0 <= item[3] <= 100 for item in history)
    assert bridge.isBusy is False

    history.clear()
    assert bridge.solveCurrentProject(4, 2), bridge.statusText
    assert any(item[1] == "正在求解" for item in history)
    assert any(item[3] >= 82 for item in history)
    assert bridge.isBusy is False
