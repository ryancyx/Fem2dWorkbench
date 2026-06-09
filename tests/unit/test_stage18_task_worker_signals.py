from __future__ import annotations

from ui.backend.workbench_tasks import FunctionWorker


def test_stage18_task_worker_runs_successfully() -> None:
    payloads: list[object] = []
    progresses: list[tuple[int, str, str]] = []

    worker = FunctionWorker(lambda progress: _task_success(progress))
    worker.progressChanged.connect(lambda value, message, stage: progresses.append((value, message, stage)))
    worker.finished.connect(lambda payload: payloads.append(payload))
    worker.run()

    assert progresses
    assert payloads == [{"ok": True}]


def test_stage18_task_worker_emits_failure() -> None:
    errors: list[str] = []
    worker = FunctionWorker(lambda progress: (_ for _ in ()).throw(ValueError("boom")))
    worker.failed.connect(lambda message: errors.append(message))
    worker.run()
    assert errors == ["boom"]


def _task_success(progress) -> dict[str, bool]:
    progress(25, "working", "mesh")
    progress(100, "done", "done")
    return {"ok": True}
