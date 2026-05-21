from PySide6.QtCore import QObject, Property, Signal, Slot


class QmlBridge(QObject):
    statusTextChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._status_text = "Fem2dWorkbench 已启动：阶段 0 空白工作台"

    @Property(str, notify=statusTextChanged)
    def statusText(self) -> str:
        return self._status_text

    def _set_status_text(self, text: str) -> None:
        if self._status_text == text:
            return
        self._status_text = text
        self.statusTextChanged.emit()

    @Slot()
    def createNewProject(self) -> None:
        self._set_status_text("已点击：新建工程。下一阶段将接入 EngineeringProject 数据模型。")

    @Slot()
    def openProject(self) -> None:
        self._set_status_text("已点击：打开工程。后续将接入 JSON 工程文件系统。")

    @Slot()
    def saveProject(self) -> None:
        self._set_status_text("已点击：保存工程。后续将接入 project_service。")