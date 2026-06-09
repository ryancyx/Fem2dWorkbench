from __future__ import annotations

import ui.backend.workbench_bridge as bridge_module
from ui.backend.workbench_bridge import WorkbenchBridge


class _FakeSignal:
    def __init__(self) -> None:
        self._callbacks = []

    def connect(self, callback) -> None:
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs) -> None:
        for callback in list(self._callbacks):
            callback(*args, **kwargs)


class _FakeThread:
    def __init__(self) -> None:
        self.started = _FakeSignal()
        self.quit_called = False
        self.wait_called = False
        self.deleted = False

    def start(self) -> None:
        return None

    def quit(self) -> None:
        self.quit_called = True

    def wait(self, _timeout: int = 0) -> None:
        self.wait_called = True

    def deleteLater(self) -> None:
        self.deleted = True


class _FakeWorker:
    def __init__(self, task) -> None:
        self._task = task
        self.progressChanged = _FakeSignal()
        self.finished = _FakeSignal()
        self.failed = _FakeSignal()
        self.deleted = False

    def moveToThread(self, _thread) -> None:
        return None

    def run(self) -> None:
        payload = self._task(lambda *_args: None)
        self.finished.emit(payload)

    def deleteLater(self) -> None:
        self.deleted = True


def test_stage18_worker_lifetime_cleanup(monkeypatch) -> None:
    bridge = WorkbenchBridge()
    fake_thread = _FakeThread()

    monkeypatch.setattr(bridge_module, "_USE_FALLBACK", False)
    monkeypatch.setattr(bridge_module, "QThread", lambda: fake_thread)
    monkeypatch.setattr(bridge_module, "FunctionWorker", _FakeWorker)

    results: list[object] = []
    bridge._launch_worker(lambda progress: {"ok": True}, success_handler=lambda payload: results.append(payload), failure_prefix="solve")

    assert bridge._active_thread is fake_thread
    assert bridge._active_worker is not None

    fake_thread.started.emit()

    assert results == [{"ok": True}]
    assert bridge._active_thread is None
    assert bridge._active_worker is None
    assert fake_thread.quit_called
    assert fake_thread.wait_called
    assert fake_thread.deleted
