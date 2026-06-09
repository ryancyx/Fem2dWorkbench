from __future__ import annotations

try:
    from PySide6.QtCore import QObject, Signal, Slot
except (ImportError, OSError):  # pragma: no cover - exercised only without Qt runtime
    class QObject:
        def __init__(self) -> None:
            pass

    class _FallbackSignal:
        def connect(self, *_args, **_kwargs) -> None:
            return None

        def emit(self, *_args, **_kwargs) -> None:
            return None

    def Signal(*_args, **_kwargs):
        return _FallbackSignal()

    def Slot(*_args, **_kwargs):
        def decorator(function):
            return function

        return decorator


class FunctionWorker(QObject):
    progressChanged = Signal(int, str, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, task) -> None:
        super().__init__()
        self._task = task

    @Slot()
    def run(self) -> None:
        try:
            payload = self._task(self._emit_progress)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(payload)

    def _emit_progress(self, progress: int, message: str, stage: str) -> None:
        self.progressChanged.emit(int(progress), str(message), str(stage))
