import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from ui.backend.workbench_bridge import WorkbenchBridge


def main() -> int:
    app = QGuiApplication(sys.argv)

    engine = QQmlApplicationEngine()

    bridge = WorkbenchBridge()
    app.aboutToQuit.connect(bridge.shutdown)
    engine.rootContext().setContextProperty("bridge", bridge)

    qml_path = Path(__file__).resolve().parent / "ui" / "qml" / "MainWorkbench.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))

    if not engine.rootObjects():
        return -1

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
