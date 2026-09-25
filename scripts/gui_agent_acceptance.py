from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from ui.backend.workbench_bridge import WorkbenchBridge


PROMPT = (
    "Create a 20 by 10 rectangle at the origin. Use material Steel with E=210000, "
    "nu=0.3, thickness=0.01 and plane stress. Fully fix the left edge and apply a "
    "uniform edge load [100, 0] on the right edge. Use mesh size 2 and request "
    "von Mises stress."
)


def main() -> int:
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    bridge = WorkbenchBridge()
    app.aboutToQuit.connect(bridge.shutdown)
    engine.rootContext().setContextProperty("bridge", bridge)
    qml_path = Path(__file__).resolve().parents[1] / "ui" / "qml" / "MainWorkbench.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    roots = engine.rootObjects()
    if not roots:
        print("[GUI ACCEPTANCE] failed: MainWorkbench.qml did not load", flush=True)
        return 2
    root = roots[0]
    prompt_input = root.findChild(QObject, "agentPromptInput")
    start_button = root.findChild(QObject, "agentStartButton")
    if prompt_input is None or start_button is None:
        print("[GUI ACCEPTANCE] failed: Agent controls were not found", flush=True)
        return 3

    outcome = {"code": 4}

    def finish(code: int, message: str) -> None:
        outcome["code"] = code
        print(message, flush=True)
        QTimer.singleShot(0, app.quit)

    def state_changed() -> None:
        print(
            f"[GUI ACCEPTANCE] status={bridge.agentStatus} stage={bridge.agentStage}",
            flush=True,
        )
        if bridge.agentStatus == "COMPLETED":
            if bridge.hasSolution and bridge.nodeCount > 0 and bridge.elementCount > 0:
                finish(0, "[GUI ACCEPTANCE] success: real Agent result reached existing Result UI")
            return
        elif bridge.agentStatus in {"FAILED", "WAITING_APPROVAL", "WAITING_USER_INPUT"}:
            orchestrator = bridge._agent_orchestrator
            if orchestrator is not None:
                execution = orchestrator.state.execution_result
                if execution is not None:
                    print(
                        "[GUI ACCEPTANCE] execution "
                        f"stage={execution.stage} error_type={execution.error_type} "
                        f"error_message={execution.error_message}",
                        flush=True,
                    )
                review = orchestrator.state.review_result
                if review is not None:
                    print(
                        f"[GUI ACCEPTANCE] review diagnosis={review.diagnosis}",
                        flush=True,
                    )
            finish(6, f"[GUI ACCEPTANCE] stopped: {bridge.statusText}")

    def click_agent_button() -> None:
        prompt_input.setProperty("text", PROMPT)
        print("[GUI ACCEPTANCE] triggering Agent button clicked signal", flush=True)
        start_button.clicked.emit()

    bridge.agentStateChanged.connect(state_changed)
    bridge.resultChanged.connect(state_changed)
    QTimer.singleShot(0, click_agent_button)
    QTimer.singleShot(
        240_000,
        lambda: finish(7, "[GUI ACCEPTANCE] failed: timeout waiting for Agent workflow"),
    )
    app.exec()
    return int(outcome["code"])


if __name__ == "__main__":
    raise SystemExit(main())
