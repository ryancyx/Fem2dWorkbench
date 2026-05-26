from __future__ import annotations

from pathlib import Path
import sys


def _use_qt_fallback() -> bool:
    return "pytest" in sys.modules or "_pytest" in sys.modules


if not _use_qt_fallback():
    try:
        from PySide6.QtCore import QObject, Property, Signal, Slot
    except (ImportError, OSError):
        _USE_FALLBACK = True
    else:
        _USE_FALLBACK = False
else:
    _USE_FALLBACK = True

if _USE_FALLBACK:

    class QObject:
        def __init__(self) -> None:
            pass

    class _FallbackSignal:
        def emit(self) -> None:
            pass

    def Signal() -> _FallbackSignal:
        return _FallbackSignal()

    def Slot(*_types: object, **_kwargs: object):
        def decorator(function):
            return function

        return decorator

    def Property(_type: object, notify: object | None = None):
        def decorator(function):
            return property(function)

        return decorator

else:
    from PySide6.QtCore import QObject, Property, Signal, Slot

from core.engineering.engineering_project import EngineeringProject
from services.export_service import (
    export_element_results_csv,
    export_node_displacements_csv,
    export_result_summary_txt,
)
from services.project_factory_service import create_rectangle_plate_project
from services.project_file_service import load_workbench_project, save_workbench_project
from services.result_service import (
    ElementResultRow,
    NodeDisplacementRow,
    ResultSummary,
    build_element_result_rows,
    build_node_displacement_rows,
    build_result_summary,
)
from services.solve_service import WorkbenchSolveResult, solve_workbench_project


class WorkbenchBridge(QObject):
    statusTextChanged = Signal()
    resultChanged = Signal()
    projectChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.current_project: EngineeringProject | None = None
        self.current_solution: WorkbenchSolveResult | None = None
        self.node_rows: list[NodeDisplacementRow] = []
        self.element_rows: list[ElementResultRow] = []
        self.summary: ResultSummary | None = None
        self.project_path = ""
        self.project_dirty = False
        self._status_text = "就绪"

    @Property(str, notify=statusTextChanged)
    def statusText(self) -> str:
        return self._status_text

    @Property(int, notify=resultChanged)
    def nodeCount(self) -> int:
        return self.summary.node_count if self.summary is not None else 0

    @Property(int, notify=resultChanged)
    def elementCount(self) -> int:
        return self.summary.element_count if self.summary is not None else 0

    @Property(str, notify=resultChanged)
    def maxDisplacement(self) -> str:
        if self.summary is None:
            return ""
        return f"{self.summary.max_displacement:.6e}"

    @Property(str, notify=resultChanged)
    def maxDisplacementNodeId(self) -> str:
        if self.summary is None or self.summary.max_displacement_node_id is None:
            return ""
        return str(self.summary.max_displacement_node_id)

    @Property(str, notify=resultChanged)
    def maxVonMises(self) -> str:
        if self.summary is None:
            return ""
        return f"{self.summary.max_von_mises:.6e}"

    @Property(str, notify=resultChanged)
    def maxVonMisesElementId(self) -> str:
        if self.summary is None or self.summary.max_von_mises_element_id is None:
            return ""
        return str(self.summary.max_von_mises_element_id)

    @Property(int, notify=resultChanged)
    def warningCount(self) -> int:
        return self.summary.warning_count if self.summary is not None else 0

    @Property(str, notify=resultChanged)
    def nodeRowsPreview(self) -> str:
        if not self.node_rows:
            return ""
        lines = ["node_id        x        y           ux           uy        |u|"]
        for row in self.node_rows[:12]:
            lines.append(
                f"{row.node_id:7d} {row.x:8.4g} {row.y:8.4g} "
                f"{row.ux:12.5e} {row.uy:12.5e} {row.u_magnitude:12.5e}"
            )
        return "\n".join(lines)

    @Property(str, notify=resultChanged)
    def elementRowsPreview(self) -> str:
        if not self.element_rows:
            return ""
        lines = ["element_id   nodes        stress_x      stress_y     von_mises"]
        for row in self.element_rows[:12]:
            node_ids = " ".join(str(node_id) for node_id in row.node_ids)
            lines.append(
                f"{row.element_id:10d} {node_ids:11s} "
                f"{row.stress_x:12.5e} {row.stress_y:12.5e} {row.von_mises:12.5e}"
            )
        return "\n".join(lines)

    @Property(bool, notify=resultChanged)
    def hasSolution(self) -> bool:
        return self.current_solution is not None

    @Property(bool, notify=projectChanged)
    def hasProject(self) -> bool:
        return self.current_project is not None

    @Property(str, notify=projectChanged)
    def projectName(self) -> str:
        return self.current_project.name if self.current_project is not None else ""

    @Property(str, notify=projectChanged)
    def projectPath(self) -> str:
        return self.project_path

    @Property(bool, notify=projectChanged)
    def projectDirty(self) -> bool:
        return self.project_dirty

    @Slot(result=bool)
    def newProject(self) -> bool:
        try:
            self.current_project = create_rectangle_plate_project(
                width=2.0,
                height=1.0,
                young_modulus=210e9,
                poisson_ratio=0.3,
                thickness=0.01,
                qy=-1000.0,
                project_name="ui_rectangle_demo",
            )
            self.project_path = ""
            self.project_dirty = True
            self._clear_solution()
            self._set_status_text("新建工程完成")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"新建工程失败: {exc}")
            return False

    @Slot(float, float, float, float, float, float, result=bool)
    def createDefaultProject(
        self,
        width: float,
        height: float,
        young_modulus: float,
        poisson_ratio: float,
        thickness: float,
        qy: float,
    ) -> bool:
        try:
            project_name = self.projectName or "ui_rectangle_demo"
            self.current_project = create_rectangle_plate_project(
                width=width,
                height=height,
                young_modulus=young_modulus,
                poisson_ratio=poisson_ratio,
                thickness=thickness,
                qy=qy,
                project_name=project_name,
            )
            self.project_dirty = True
            self._clear_solution()
            self._set_status_text("工程已创建/更新")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"创建工程失败: {exc}")
            return False

    @Slot(str, result=bool)
    def saveCurrentProject(
        self,
        file_path: str = "outputs/latest/current_project.f2dw.json",
    ) -> bool:
        if self.current_project is None:
            self._set_status_text("没有可保存的工程")
            return False

        try:
            path = save_workbench_project(self.current_project, file_path)
            self.project_path = str(path)
            self.project_dirty = False
            self._set_status_text(f"工程已保存：{path}")
            self.projectChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"保存工程失败: {exc}")
            return False

    @Slot(str, result=bool)
    def loadProject(
        self,
        file_path: str = "outputs/latest/current_project.f2dw.json",
    ) -> bool:
        try:
            path = Path(file_path)
            self.current_project = load_workbench_project(path)
            self.project_path = str(path)
            self.project_dirty = False
            self._clear_solution()
            self._set_status_text(f"工程已打开：{path}")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"打开工程失败: {exc}")
            return False

    @Slot(int, int, result=bool)
    def solveCurrentProject(self, nx: int, ny: int) -> bool:
        if self.current_project is None:
            self._set_status_text("请先创建工程或打开工程")
            return False

        try:
            solution = solve_workbench_project(
                project=self.current_project,
                part_id="part_rectangle",
                step_id="step_static",
                nx=nx,
                ny=ny,
            )
            self.current_solution = solution
            self.node_rows = build_node_displacement_rows(solution)
            self.element_rows = build_element_result_rows(solution)
            self.summary = build_result_summary(solution)
            self._set_status_text(
                f"求解完成：节点 {self.summary.node_count}，单元 {self.summary.element_count}"
            )
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"求解失败: {exc}")
            return False

    @Slot(str, result=bool)
    def exportResults(self, output_dir: str = "outputs/latest") -> bool:
        if self.current_solution is None:
            self._set_status_text("没有可导出的结果")
            return False

        try:
            output_path = Path(output_dir)
            export_node_displacements_csv(
                self.current_solution,
                output_path / "node_displacements.csv",
            )
            export_element_results_csv(
                self.current_solution,
                output_path / "element_results.csv",
            )
            export_result_summary_txt(
                self.current_solution,
                output_path / "summary.txt",
            )
            self._set_status_text(f"结果已导出到 {output_path}")
            return True
        except Exception as exc:
            self._set_status_text(f"导出失败: {exc}")
            return False

    def _clear_solution(self) -> None:
        self.current_solution = None
        self.node_rows = []
        self.element_rows = []
        self.summary = None

    def _set_status_text(self, text: str) -> None:
        if self._status_text == text:
            return
        self._status_text = text
        self.statusTextChanged.emit()
