from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import uuid


def _use_qt_fallback() -> bool:
    return "pytest" in sys.modules or "_pytest" in sys.modules


if not _use_qt_fallback():
    try:
        from PySide6.QtCore import QCoreApplication, QObject, Property, QThread, QTimer, Signal, Slot
    except (ImportError, OSError):
        _USE_FALLBACK = True
    else:
        _USE_FALLBACK = False
else:
    _USE_FALLBACK = True

if _USE_FALLBACK:

    class QCoreApplication:
        @staticmethod
        def processEvents() -> None:
            return None

    class QObject:
        def __init__(self) -> None:
            pass

    class QThread:
        def __init__(self) -> None:
            pass

        def start(self) -> None:
            return None

        def quit(self) -> None:
            return None

        def wait(self, _timeout: int | None = None) -> None:
            return None

        def deleteLater(self) -> None:
            return None

    class QTimer:
        @staticmethod
        def singleShot(_ms: int, callback) -> None:
            callback()

    class _FallbackSignal:
        def connect(self, *_args: object, **_kwargs: object) -> None:
            pass

        def emit(self, *_args: object, **_kwargs: object) -> None:
            pass

    def Signal(*_args: object, **_kwargs: object) -> _FallbackSignal:
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
    from PySide6.QtCore import QCoreApplication, QObject, Property, QThread, QTimer, Signal, Slot

from core.engineering.boundary_condition_definition import BoundaryConditionDefinition
from core.engineering.engineering_project import EngineeringProject
from core.engineering.load_definition import LoadDefinition
from core.engineering.mesh_model import MeshModel
from core.meshing.quality_sketch_mesher import generate_quality_sketch_tri_mesh
from core.meshing.sketch_polygon_mesher import generate_sketch_tri_mesh
from core.solver.solver_api import solve_static_linear
from services.assembly_edit_service import (
    add_instance,
    delete_instance,
    ensure_default_instance,
    list_instances,
    move_instance,
    rename_instance,
    set_active_instance,
)
from services.compile_service import compile_workbench_project
from services.contour_cache_service import (
    build_contour_image_cache_json,
    cleanup_old_cache_dirs,
    clear_contour_cache_dir,
    create_contour_cache_dir,
    generate_contour_images,
)
from services.export_service import (
    export_deformation_plot_data_json,
    export_displacement_contour_data_json,
    export_element_results_csv,
    export_node_displacements_csv,
    export_result_summary_txt,
    export_stress_contour_data_json,
    export_von_mises_contour_data_json,
)
from services.face_material_service import assign_material_to_face, get_part_face_material_rows
from services.material_manager_service import (
    add_material,
    assign_material_to_part,
    delete_material,
    get_part_material_info,
    list_materials,
    list_sections,
    update_material,
)
from services.mesh_quality_service import build_mesh_quality_summary
from services.part_edit_service import (
    add_rectangle_part,
    delete_part,
    get_active_part_id,
    list_parts,
    rename_part,
    set_active_part,
)
from services.project_factory_service import create_rectangle_plate_project
from services.project_file_service import load_workbench_project, save_workbench_project
from services.project_parameter_service import (
    WorkbenchProjectParameters,
    apply_workbench_project_parameters,
    extract_workbench_project_parameters,
)
from services.result_service import (
    ElementResultRow,
    NodeDisplacementRow,
    ResultSummary,
    build_deformation_plot_data,
    build_displacement_contour_data,
    build_element_result_rows,
    build_node_displacement_rows,
    build_result_summary,
    build_stress_contour_data,
)
from services.result_query_service import format_result_query_text, query_result_at_point
from services.solve_service import WorkbenchSolveResult, solve_workbench_project
from services.sketch_geometry_service import (
    add_sketch_edge,
    add_sketch_point,
    build_geometry_diagnostics_text,
    build_faces_from_edges,
    can_build_closed_faces,
    clear_sketch_geometry,
    create_empty_sketch_geometry,
    delete_sketch_edge,
    delete_sketch_point,
    get_sketch_edges,
    get_sketch_faces,
    get_sketch_points,
    move_sketch_point,
)
from ui.backend.workbench_tasks import FunctionWorker


class WorkbenchBridge(QObject):
    statusTextChanged = Signal()
    resultChanged = Signal()
    projectChanged = Signal()
    projectParametersChanged = Signal()
    busyStateChanged = Signal()
    partsChanged = Signal()
    instancesChanged = Signal()
    sketchChanged = Signal()
    sketchMeshChanged = Signal()
    partEditChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.current_project: EngineeringProject | None = None
        self.current_solution: WorkbenchSolveResult | None = None
        self.current_sketch_mesh: MeshModel | None = None
        self.node_rows: list[NodeDisplacementRow] = []
        self.element_rows: list[ElementResultRow] = []
        self.summary: ResultSummary | None = None
        self.project_path = ""
        self.project_dirty = False
        self._status_text = "就绪"
        self.project_width = 2.0
        self.project_height = 1.0
        self.project_young_modulus = 210e9
        self.project_poisson_ratio = 0.3
        self.project_thickness = 0.01
        self.project_edge_qy = -1000.0
        self.project_mesh_nx = 4
        self.project_mesh_ny = 2
        self.active_part_id = ""
        self.active_part_name = ""
        self.part_count = 0
        self.part_options: list[str] = []
        self.active_instance_id = ""
        self.active_instance_name = ""
        self.active_instance_part_id = ""
        self.active_instance_tx = 0.0
        self.active_instance_ty = 0.0
        self.instance_count = 0
        self.instance_options: list[str] = []
        self.sketch_point_count = 0
        self.sketch_edge_count = 0
        self.sketch_face_count = 0
        self.sketch_points_preview = ""
        self.sketch_edges_preview = ""
        self.sketch_can_build_face = False
        self.sketch_has_face = False
        self.selected_sketch_point_id = ""
        self.selected_sketch_edge_id = ""
        self.selected_sketch_face_id = ""
        self.sketch_fixed_edge_id = ""
        self.sketch_load_edge_id = ""
        self.sketch_load_qx = 0.0
        self.sketch_load_qy = -1000.0
        self.sketch_points_json = "[]"
        self.sketch_edges_json = "[]"
        self.sketch_faces_json = "[]"
        self.has_sketch_mesh = False
        self.sketch_mesh_node_count = 0
        self.sketch_mesh_element_count = 0
        self.sketch_mesh_nodes_json = "[]"
        self.sketch_mesh_elements_json = "[]"
        self.sketch_mesh_status_text = "暂无草图网格"
        self.part_edit_mode = False
        self.part_edit_tool = "选择"
        self.edge_start_point_id = ""
        self.geometry_target_type = ""
        self.geometry_target_id = ""
        self.sketch_node_rows_preview = ""
        self.sketch_edge_rows_preview = ""
        self.geometry_diagnostics_text = ""
        self.material_options: list[str] = []
        self.material_count = 0
        self.active_part_material_id = ""
        self.active_part_material_name = ""
        self.active_part_material_color = "#8FB7D8"
        self.active_part_thickness = 0.01
        self.material_rows_preview = ""
        self.section_rows_preview = ""
        self.face_material_rows_preview = ""
        self.active_part_face_material_json = "[]"
        self.mesh_target_size = 0.25
        self.mesh_max_area = 0.0
        self.mesh_min_angle = 25.0
        self.mesh_quality_summary_text = ""
        self.mesh_min_angle_value = ""
        self.mesh_degenerate_element_count = 0
        self.current_mesh_type = "none"
        self.boundary_condition_rows_preview = ""
        self.load_rows_preview = ""
        self.boundary_conditions_json = "[]"
        self.loads_json = "[]"
        self.edge_load_start_t = 0.0
        self.edge_load_end_t = 1.0
        self.edge_load_has_custom_range = False
        self.edge_load_segment_selection_mode = False
        self.edge_load_segment_edge_id = ""
        self.edge_load_segment_first_t = -1.0
        self.result_query_x = 0.0
        self.result_query_y = 0.0
        self.result_query_text = ""
        self.node_rows_json = "[]"
        self.element_rows_json = "[]"
        self.deformation_preview_json = "{}"
        self.deformation_plot_json = "{}"
        self.displacement_contour_json = "{}"
        self.stress_contour_json = "{}"
        self.stress_contour_exact_json = "{}"
        self.stress_contour_smooth_json = "{}"
        self.contour_cache_valid = False
        self.contour_cache_summary_text = ""
        self.contour_image_cache_valid = False
        self.contour_image_cache_dir = ""
        self.contour_image_cache_json = "{}"
        self.is_busy = False
        self.busy_title = ""
        self.busy_message = ""
        self.busy_progress = 0
        self.busy_indeterminate = False
        self.busy_stage = ""
        self.selected_geometry_type = ""
        self.selected_geometry_id = ""
        self._session_cache_id = uuid.uuid4().hex
        self._active_thread: QThread | None = None
        self._active_worker: FunctionWorker | None = None
        cleanup_old_cache_dirs()

    @Property(bool, notify=partEditChanged)
    def partEditMode(self) -> bool:
        return self.part_edit_mode

    @Property(str, notify=partEditChanged)
    def partEditTool(self) -> str:
        return self.part_edit_tool

    @Property(str, notify=partEditChanged)
    def edgeStartPointId(self) -> str:
        return self.edge_start_point_id

    @Property(str, notify=partEditChanged)
    def geometryTargetType(self) -> str:
        return self.geometry_target_type

    @Property(str, notify=partEditChanged)
    def geometryTargetId(self) -> str:
        return self.geometry_target_id

    @Property(str, notify=partEditChanged)
    def selectedTargetType(self) -> str:
        return self.geometry_target_type

    @Property(str, notify=partEditChanged)
    def selectedTargetId(self) -> str:
        return self.geometry_target_id

    @Property(str, notify=sketchChanged)
    def selectedGeometryType(self) -> str:
        return self.selected_geometry_type

    @Property(str, notify=sketchChanged)
    def selectedGeometryId(self) -> str:
        return self.selected_geometry_id

    @Property(str, notify=sketchChanged)
    def selectedFaceId(self) -> str:
        return self.selected_sketch_face_id

    @Property(str, notify=partEditChanged)
    def sketchNodeRowsPreview(self) -> str:
        return self.sketch_node_rows_preview

    @Property(str, notify=partEditChanged)
    def sketchEdgeRowsPreview(self) -> str:
        return self.sketch_edge_rows_preview

    @Property(str, notify=partEditChanged)
    def geometryDiagnosticsText(self) -> str:
        return self.geometry_diagnostics_text

    @Property(list, notify=projectChanged)
    def materialOptions(self) -> list[str]:
        return list(self.material_options)

    @Property(int, notify=projectChanged)
    def materialCount(self) -> int:
        return self.material_count

    @Property(str, notify=projectChanged)
    def activePartMaterialId(self) -> str:
        return self.active_part_material_id

    @Property(str, notify=projectChanged)
    def activePartMaterialName(self) -> str:
        return self.active_part_material_name

    @Property(str, notify=projectChanged)
    def activePartMaterialColor(self) -> str:
        return self.active_part_material_color

    @Property(float, notify=projectChanged)
    def activePartThickness(self) -> float:
        return self.active_part_thickness

    @Property(str, notify=projectChanged)
    def materialRowsPreview(self) -> str:
        return self.material_rows_preview

    @Property(str, notify=projectChanged)
    def sectionRowsPreview(self) -> str:
        return self.section_rows_preview

    @Property(str, notify=projectChanged)
    def faceMaterialRowsPreview(self) -> str:
        return self.face_material_rows_preview

    @Property(str, notify=projectChanged)
    def activePartFaceMaterialJson(self) -> str:
        return self.active_part_face_material_json

    @Property(str, notify=projectChanged)
    def faceMaterialJson(self) -> str:
        return self.active_part_face_material_json

    @Property(bool, notify=projectChanged)
    def gravityEnabled(self) -> bool:
        if self.current_project is None:
            return False
        return bool(self.current_project.metadata.get("gravity_enabled", False))

    @Property(float, notify=sketchMeshChanged)
    def meshTargetSize(self) -> float:
        return self.mesh_target_size

    @Property(float, notify=sketchMeshChanged)
    def meshMaxArea(self) -> float:
        return self.mesh_max_area

    @Property(float, notify=sketchMeshChanged)
    def meshMinAngle(self) -> float:
        return self.mesh_min_angle

    @Property(str, notify=sketchMeshChanged)
    def meshQualitySummaryText(self) -> str:
        return self.mesh_quality_summary_text

    @Property(str, notify=sketchMeshChanged)
    def meshMinAngleValue(self) -> str:
        return self.mesh_min_angle_value

    @Property(int, notify=sketchMeshChanged)
    def meshDegenerateElementCount(self) -> int:
        return self.mesh_degenerate_element_count

    @Property(str, notify=sketchMeshChanged)
    def currentMeshType(self) -> str:
        return self.current_mesh_type

    @Property(str, notify=projectChanged)
    def boundaryConditionRowsPreview(self) -> str:
        return self.boundary_condition_rows_preview

    @Property(str, notify=projectChanged)
    def loadRowsPreview(self) -> str:
        return self.load_rows_preview

    @Property(str, notify=projectChanged)
    def boundaryConditionsJson(self) -> str:
        return self.boundary_conditions_json

    @Property(str, notify=projectChanged)
    def loadsJson(self) -> str:
        return self.loads_json

    @Property(float, notify=projectChanged)
    def edgeLoadStartT(self) -> float:
        return self.edge_load_start_t

    @Property(float, notify=projectChanged)
    def edgeLoadEndT(self) -> float:
        return self.edge_load_end_t

    @Property(bool, notify=projectChanged)
    def hasEdgeLoadSegment(self) -> bool:
        return self.edge_load_has_custom_range

    @Property(bool, notify=projectChanged)
    def edgeLoadSegmentSelectionMode(self) -> bool:
        return self.edge_load_segment_selection_mode

    @Property(str, notify=projectChanged)
    def edgeLoadSegmentSelectionEdgeId(self) -> str:
        return self.edge_load_segment_edge_id

    @Property(bool, notify=projectChanged)
    def edgeLoadSegmentHasFirstPoint(self) -> bool:
        return self.edge_load_segment_first_t >= 0.0

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

    @Property(float, notify=resultChanged)
    def resultQueryX(self) -> float:
        return self.result_query_x

    @Property(float, notify=resultChanged)
    def resultQueryY(self) -> float:
        return self.result_query_y

    @Property(str, notify=resultChanged)
    def resultQueryText(self) -> str:
        return self.result_query_text

    @Property(str, notify=resultChanged)
    def nodeRowsJson(self) -> str:
        return self.node_rows_json

    @Property(str, notify=resultChanged)
    def elementRowsJson(self) -> str:
        return self.element_rows_json

    @Property(str, notify=resultChanged)
    def deformationPreviewJson(self) -> str:
        return self.deformation_preview_json

    @Property(str, notify=resultChanged)
    def deformationPlotJson(self) -> str:
        return self.deformation_plot_json

    @Property(str, notify=resultChanged)
    def displacementContourJson(self) -> str:
        return self.displacement_contour_json

    @Property(str, notify=resultChanged)
    def stressContourJson(self) -> str:
        return self.stress_contour_json

    @Property(str, notify=resultChanged)
    def stressContourExactJson(self) -> str:
        return self.stress_contour_exact_json

    @Property(str, notify=resultChanged)
    def stressContourSmoothJson(self) -> str:
        return self.stress_contour_smooth_json

    @Property(bool, notify=resultChanged)
    def contourCacheValid(self) -> bool:
        return self.contour_cache_valid

    @Property(str, notify=resultChanged)
    def contourCacheSummaryText(self) -> str:
        return self.contour_cache_summary_text

    @Property(bool, notify=resultChanged)
    def contourImageCacheValid(self) -> bool:
        return self.contour_image_cache_valid

    @Property(str, notify=resultChanged)
    def contourImageCacheDir(self) -> str:
        return self.contour_image_cache_dir

    @Property(str, notify=resultChanged)
    def contourImageCacheJson(self) -> str:
        return self.contour_image_cache_json

    @Property(bool, notify=busyStateChanged)
    def isBusy(self) -> bool:
        return self.is_busy

    @Property(str, notify=busyStateChanged)
    def busyTitle(self) -> str:
        return self.busy_title

    @Property(str, notify=busyStateChanged)
    def busyMessage(self) -> str:
        return self.busy_message

    @Property(int, notify=busyStateChanged)
    def busyProgress(self) -> int:
        return self.busy_progress

    @Property(bool, notify=busyStateChanged)
    def busyIndeterminate(self) -> bool:
        return self.busy_indeterminate

    @Property(str, notify=busyStateChanged)
    def busyStage(self) -> str:
        return self.busy_stage

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

    @Property(float, notify=projectParametersChanged)
    def projectWidth(self) -> float:
        return self.project_width

    @Property(float, notify=projectParametersChanged)
    def projectHeight(self) -> float:
        return self.project_height

    @Property(float, notify=projectParametersChanged)
    def projectYoungModulus(self) -> float:
        return self.project_young_modulus

    @Property(float, notify=projectParametersChanged)
    def projectPoissonRatio(self) -> float:
        return self.project_poisson_ratio

    @Property(float, notify=projectParametersChanged)
    def projectThickness(self) -> float:
        return self.project_thickness

    @Property(float, notify=projectParametersChanged)
    def projectEdgeQy(self) -> float:
        return self.project_edge_qy

    @Property(int, notify=projectParametersChanged)
    def projectMeshNx(self) -> int:
        return self.project_mesh_nx

    @Property(int, notify=projectParametersChanged)
    def projectMeshNy(self) -> int:
        return self.project_mesh_ny

    @Property(str, notify=partsChanged)
    def activePartId(self) -> str:
        return self.active_part_id

    @Property(str, notify=partsChanged)
    def activePartName(self) -> str:
        return self.active_part_name

    @Property(int, notify=partsChanged)
    def partCount(self) -> int:
        return self.part_count

    @Property(list, notify=partsChanged)
    def partOptions(self) -> list[str]:
        return list(self.part_options)

    @Property(str, notify=instancesChanged)
    def activeInstanceId(self) -> str:
        return self.active_instance_id

    @Property(str, notify=instancesChanged)
    def activeInstanceName(self) -> str:
        return self.active_instance_name

    @Property(str, notify=instancesChanged)
    def activeInstancePartId(self) -> str:
        return self.active_instance_part_id

    @Property(float, notify=instancesChanged)
    def activeInstanceTx(self) -> float:
        return self.active_instance_tx

    @Property(float, notify=instancesChanged)
    def activeInstanceTy(self) -> float:
        return self.active_instance_ty

    @Property(int, notify=instancesChanged)
    def instanceCount(self) -> int:
        return self.instance_count

    @Property(list, notify=instancesChanged)
    def instanceOptions(self) -> list[str]:
        return list(self.instance_options)

    @Property(int, notify=sketchChanged)
    def sketchPointCount(self) -> int:
        return self.sketch_point_count

    @Property(int, notify=sketchChanged)
    def sketchEdgeCount(self) -> int:
        return self.sketch_edge_count

    @Property(int, notify=sketchChanged)
    def sketchFaceCount(self) -> int:
        return self.sketch_face_count

    @Property(str, notify=sketchChanged)
    def sketchPointsPreview(self) -> str:
        return self.sketch_points_preview

    @Property(str, notify=sketchChanged)
    def sketchEdgesPreview(self) -> str:
        return self.sketch_edges_preview

    @Property(bool, notify=sketchChanged)
    def sketchCanBuildFace(self) -> bool:
        return self.sketch_can_build_face

    @Property(bool, notify=sketchChanged)
    def sketchHasFace(self) -> bool:
        return self.sketch_has_face

    @Property(str, notify=sketchChanged)
    def selectedSketchPointId(self) -> str:
        return self.selected_sketch_point_id

    @Property(str, notify=sketchChanged)
    def selectedSketchEdgeId(self) -> str:
        return self.selected_sketch_edge_id

    @Property(str, notify=sketchChanged)
    def sketchFixedEdgeId(self) -> str:
        return self.sketch_fixed_edge_id

    @Property(str, notify=sketchChanged)
    def sketchLoadEdgeId(self) -> str:
        return self.sketch_load_edge_id

    @Property(float, notify=sketchChanged)
    def sketchLoadQx(self) -> float:
        return self.sketch_load_qx

    @Property(float, notify=sketchChanged)
    def sketchLoadQy(self) -> float:
        return self.sketch_load_qy

    @Property(str, notify=sketchChanged)
    def sketchPointsJson(self) -> str:
        return self.sketch_points_json

    @Property(str, notify=sketchChanged)
    def sketchEdgesJson(self) -> str:
        return self.sketch_edges_json

    @Property(str, notify=sketchChanged)
    def sketchFacesJson(self) -> str:
        return self.sketch_faces_json

    @Property(str, notify=sketchChanged)
    def modelPointsJson(self) -> str:
        return self.sketch_points_json

    @Property(str, notify=sketchChanged)
    def modelEdgesJson(self) -> str:
        return self.sketch_edges_json

    @Property(str, notify=sketchChanged)
    def modelFacesJson(self) -> str:
        return self.sketch_faces_json

    @Property(int, notify=sketchChanged)
    def modelPointCount(self) -> int:
        return self.sketch_point_count

    @Property(int, notify=sketchChanged)
    def modelEdgeCount(self) -> int:
        return self.sketch_edge_count

    @Property(int, notify=sketchChanged)
    def modelFaceCount(self) -> int:
        return self.sketch_face_count

    @Property(bool, notify=sketchMeshChanged)
    def hasSketchMesh(self) -> bool:
        return self.has_sketch_mesh

    @Property(int, notify=sketchMeshChanged)
    def sketchMeshNodeCount(self) -> int:
        return self.sketch_mesh_node_count

    @Property(int, notify=sketchMeshChanged)
    def sketchMeshElementCount(self) -> int:
        return self.sketch_mesh_element_count

    @Property(str, notify=sketchMeshChanged)
    def sketchMeshNodesJson(self) -> str:
        return self.sketch_mesh_nodes_json

    @Property(str, notify=sketchMeshChanged)
    def sketchMeshElementsJson(self) -> str:
        return self.sketch_mesh_elements_json

    @Property(bool, notify=sketchMeshChanged)
    def hasMesh(self) -> bool:
        return self.has_sketch_mesh

    @Property(str, notify=sketchMeshChanged)
    def meshNodesJson(self) -> str:
        return self.sketch_mesh_nodes_json

    @Property(str, notify=sketchMeshChanged)
    def meshElementsJson(self) -> str:
        return self.sketch_mesh_elements_json

    @Property(str, notify=sketchMeshChanged)
    def sketchMeshStatusText(self) -> str:
        return self.sketch_mesh_status_text

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
                project_name="single_model_project",
                mesh_nx=4,
                mesh_ny=2,
            )
            self.project_path = ""
            self.project_dirty = True
            self._sync_instances_from_project()
            self._sync_parts_from_project()
            if self.active_part_id:
                part = self.current_project.get_part_by_id(self.active_part_id)
                if part is not None:
                    part.name = "二维模型"
                    part.geometry = create_empty_sketch_geometry()
            self.current_project.loads = []
            self.current_project.boundary_conditions = []
            self._reset_sketch_boundary_load_state(reset_load_values=True)
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_instances_from_project()
            self._sync_parts_from_project()
            self._sync_parameter_cache_from_project()
            self._sync_sketch_from_active_part()
            self._sync_material_state_from_project()
            self._sync_boundary_load_state_from_project()
            self._set_status_text("新建空白模型完成")
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
                mesh_nx=self.project_mesh_nx,
                mesh_ny=self.project_mesh_ny,
            )
            self.project_dirty = True
            self._reset_sketch_boundary_load_state(reset_load_values=True)
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_instances_from_project()
            self._sync_parts_from_project()
            self._sync_parameter_cache_from_project()
            self._sync_sketch_from_active_part()
            self._sync_material_state_from_project()
            self._sync_boundary_load_state_from_project()
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
            self._reset_sketch_boundary_load_state(reset_load_values=True)
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_instances_from_project()
            self._sync_parts_from_project()
            self._sync_parameter_cache_from_project()
            self._sync_sketch_from_active_part()
            self._sync_material_state_from_project()
            self._sync_boundary_load_state_from_project()
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

        self._begin_busy("正在求解", "准备求解", "solve_prepare", 0)
        try:
            active_part_id = self.active_instance_part_id or self.active_part_id or get_active_part_id(self.current_project)
            if not active_part_id:
                self._set_status_text("没有活动零件")
                return False
            part = self.current_project.get_part_by_id(active_part_id)
            if part is None:
                self._set_status_text(f"活动零件不存在：{active_part_id}")
                return False
            edge_ids = {edge.id for edge in part.geometry.edges}
            if not {"bottom", "right", "top", "left"}.issubset(edge_ids):
                self._set_status_text("自定义草图求解将在后续阶段支持")
                return False
            self.current_project.metadata["mesh_nx"] = nx
            self.current_project.metadata["mesh_ny"] = ny
            self.project_mesh_nx = nx
            self.project_mesh_ny = ny
            self.projectParametersChanged.emit()
            self._update_busy(15, "编译工程模型", "solve_compile")
            solution = solve_workbench_project(
                project=self.current_project,
                part_id=active_part_id,
                step_id="step_static",
                nx=nx,
                ny=ny,
            )
            self._update_busy(75, "计算节点位移和单元应力", "solve_post")
            self.current_solution = solution
            self.node_rows = build_node_displacement_rows(solution)
            self.element_rows = build_element_result_rows(solution)
            self.summary = build_result_summary(solution)
            self._store_solution_rows(progress_callback=self._update_busy)
            self._update_busy(100, "求解完成", "solve_done")
            gravity_suffix = " | self_weight" if self.gravityEnabled else ""
            if self.contour_image_cache_valid:
                self._set_status_text(
                    f"求解完成，云图数据和图片缓存已生成{gravity_suffix}：实例 {self.active_instance_name} / 零件 {active_part_id}，节点 {self.summary.node_count}，单元 {self.summary.element_count}"
                )
            else:
                self._set_status_text(
                    f"求解成功，但云图图片缓存生成失败{gravity_suffix}：实例 {self.active_instance_name} / 零件 {active_part_id}，节点 {self.summary.node_count}，单元 {self.summary.element_count}"
                )
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._clear_solution()
            self.resultChanged.emit()
            self._set_status_text(f"求解失败: {exc}")
            return False
        finally:
            self._finish_busy()

    @Slot(str, result=bool)
    def setActivePart(self, part_id: str) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False

        try:
            matching_instance = None
            for instance in self.current_project.assembly.instances:
                if instance.part_id == part_id:
                    matching_instance = instance
                    break
            if matching_instance is None:
                add_instance(
                    self.current_project,
                    part_id=part_id,
                    name="实例 " + str(len(self.current_project.assembly.instances) + 1),
                    make_active=True,
                )
            else:
                set_active_instance(self.current_project, matching_instance.id)
            set_active_part(self.current_project, part_id)
            self.project_dirty = True
            self._reset_sketch_boundary_load_state(reset_load_values=True)
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_instances_from_project()
            self._sync_parts_from_project()
            self._sync_parameter_cache_from_project()
            self._sync_sketch_from_active_part()
            self._sync_material_state_from_project()
            self._sync_boundary_load_state_from_project()
            self._set_status_text(f"已切换活动零件：{self.active_part_name}")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"切换活动零件失败: {exc}")
            return False

    @Slot(str, float, float, result=bool)
    def addRectanglePart(self, name: str, width: float, height: float) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False

        try:
            add_rectangle_part(
                self.current_project,
                name=name,
                width=width,
                height=height,
                make_active=True,
            )
            new_part_id = get_active_part_id(self.current_project)
            add_instance(
                self.current_project,
                part_id=new_part_id,
                name=name or "实例 " + str(len(self.current_project.assembly.instances) + 1),
                make_active=True,
            )
            self.project_dirty = True
            self._reset_sketch_boundary_load_state(reset_load_values=True)
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_instances_from_project()
            self._sync_parts_from_project()
            self._sync_parameter_cache_from_project()
            self._sync_sketch_from_active_part()
            self._sync_material_state_from_project()
            self._sync_boundary_load_state_from_project()
            self._set_status_text(f"已新增矩形零件：{self.active_part_name}")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"新增矩形零件失败: {exc}")
            return False

    @Slot(str, result=bool)
    def renameActivePart(self, new_name: str) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        if not self.active_part_id:
            self._set_status_text("没有活动零件")
            return False

        try:
            rename_part(self.current_project, self.active_part_id, new_name)
            self.project_dirty = True
            self._sync_parts_from_project()
            self._set_status_text("已重命名活动零件")
            self.projectChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"重命名活动零件失败: {exc}")
            return False

    @Slot(result=bool)
    def deleteActivePart(self) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        if not self.active_part_id:
            self._set_status_text("没有活动零件")
            return False

        try:
            delete_part(self.current_project, self.active_part_id)
            self.project_dirty = True
            self._reset_sketch_boundary_load_state(reset_load_values=True)
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_instances_from_project()
            self._sync_parts_from_project()
            self._sync_parameter_cache_from_project()
            self._sync_sketch_from_active_part()
            self._sync_material_state_from_project()
            self._sync_boundary_load_state_from_project()
            self._set_status_text("已删除活动零件")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"删除活动零件失败: {exc}")
            return False

    @Slot(str, result=bool)
    def setActiveInstance(self, instance_id: str) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False

        try:
            set_active_instance(self.current_project, instance_id)
            self.project_dirty = True
            self._reset_sketch_boundary_load_state(reset_load_values=True)
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_instances_from_project()
            self._sync_parts_from_project()
            self._sync_parameter_cache_from_project()
            self._sync_sketch_from_active_part()
            self._sync_material_state_from_project()
            self._sync_boundary_load_state_from_project()
            self._set_status_text(f"已切换活动实例：{self.active_instance_name}")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"切换活动实例失败: {exc}")
            return False

    @Slot(str, str, float, float, result=bool)
    def addInstanceForPart(
        self,
        part_id: str,
        name: str,
        tx: float,
        ty: float,
    ) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False

        try:
            add_instance(
                self.current_project,
                part_id=part_id,
                name=name,
                tx=tx,
                ty=ty,
                make_active=True,
            )
            self.project_dirty = True
            self._reset_sketch_boundary_load_state(reset_load_values=True)
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_instances_from_project()
            self._sync_parts_from_project()
            self._sync_parameter_cache_from_project()
            self._sync_sketch_from_active_part()
            self._sync_material_state_from_project()
            self._sync_boundary_load_state_from_project()
            self._set_status_text(f"已新增装配实例：{self.active_instance_name}")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"新增装配实例失败: {exc}")
            return False

    @Slot(str, result=bool)
    def renameActiveInstance(self, new_name: str) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        if not self.active_instance_id:
            self._set_status_text("没有活动实例")
            return False

        try:
            rename_instance(self.current_project, self.active_instance_id, new_name)
            self.project_dirty = True
            self._sync_instances_from_project()
            self._set_status_text("已重命名活动实例")
            self.projectChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"重命名活动实例失败: {exc}")
            return False

    @Slot(float, float, result=bool)
    def moveActiveInstance(self, tx: float, ty: float) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        if not self.active_instance_id:
            self._set_status_text("没有活动实例")
            return False

        try:
            move_instance(self.current_project, self.active_instance_id, tx, ty)
            self.project_dirty = True
            self._sync_instances_from_project()
            self._set_status_text(f"已移动活动实例：({tx:.3g}, {ty:.3g})")
            self.projectChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"移动活动实例失败: {exc}")
            return False

    @Slot(result=bool)
    def deleteActiveInstance(self) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        if not self.active_instance_id:
            self._set_status_text("没有活动实例")
            return False

        try:
            delete_instance(self.current_project, self.active_instance_id)
            self.project_dirty = True
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_instances_from_project()
            self._sync_parts_from_project()
            self._sync_parameter_cache_from_project()
            self._sync_sketch_from_active_part()
            self._sync_material_state_from_project()
            self._sync_boundary_load_state_from_project()
            self._set_status_text("已删除活动实例")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"删除活动实例失败: {exc}")
            return False

    @Slot(float, float, float, float, float, float, int, int, result=bool)
    def updateCurrentProjectParameters(
        self,
        width: float,
        height: float,
        young_modulus: float,
        poisson_ratio: float,
        thickness: float,
        qy: float,
        mesh_nx: int,
        mesh_ny: int,
    ) -> bool:
        try:
            params = WorkbenchProjectParameters(
                width=width,
                height=height,
                young_modulus=young_modulus,
                poisson_ratio=poisson_ratio,
                thickness=thickness,
                qy=qy,
                mesh_nx=mesh_nx,
                mesh_ny=mesh_ny,
            )
            if self.current_project is None:
                self.current_project = create_rectangle_plate_project(
                    width=params.width,
                    height=params.height,
                    young_modulus=params.young_modulus,
                    poisson_ratio=params.poisson_ratio,
                    thickness=params.thickness,
                    qy=params.qy,
                    project_name="ui_rectangle_demo",
                    mesh_nx=params.mesh_nx,
                    mesh_ny=params.mesh_ny,
                )
            else:
                apply_workbench_project_parameters(
                    self.current_project,
                    params,
                    self.active_part_id or None,
                )

            self.project_dirty = True
            self._reset_sketch_boundary_load_state(reset_load_values=True)
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_instances_from_project()
            self._sync_parts_from_project()
            self._sync_parameter_cache_from_project()
            self._sync_sketch_from_active_part()
            self._sync_material_state_from_project()
            self._sync_boundary_load_state_from_project()
            self._set_status_text("工程参数已更新")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"更新工程参数失败: {exc}")
            return False

    @Slot(result=bool)
    def enterPartEditMode(self) -> bool:
        self.part_edit_mode = True
        self.part_edit_tool = "选择"
        self.partEditChanged.emit()
        self._set_status_text("已进入零件编辑模式")
        return True

    @Slot(result=bool)
    def exitPartEditMode(self) -> bool:
        self.part_edit_mode = False
        self.part_edit_tool = "选择"
        self.edge_start_point_id = ""
        self.partEditChanged.emit()
        self._set_status_text("已退出零件编辑模式")
        return True

    @Slot(str, result=bool)
    def setPartEditTool(self, tool: str) -> bool:
        tool = str(tool).strip()
        if tool not in {"选择", "添加节点", "连接边", "移动节点", "删除"}:
            self._set_status_text(f"不支持的编辑工具: {tool}")
            return False
        self.part_edit_tool = tool
        if tool != "连接边":
            self.edge_start_point_id = ""
        self.partEditChanged.emit()
        self._set_status_text(f"已切换编辑工具：{tool}")
        return True

    @Slot(str, result=bool)
    def setModelTool(self, tool: str) -> bool:
        return self.setPartEditTool(tool)

    @Slot(result=bool)
    def startEdgeFromSelectedPoint(self) -> bool:
        if not self.selected_sketch_point_id:
            self._set_status_text("请先选择起点")
            return False
        self.edge_start_point_id = self.selected_sketch_point_id
        self.partEditChanged.emit()
        self._set_status_text(f"已设置连边起点：{self.edge_start_point_id}")
        return True

    @Slot(str, result=bool)
    def connectEdgeToPoint(self, point_id: str) -> bool:
        point_id = str(point_id).strip()
        if not self.edge_start_point_id:
            self._set_status_text("请先设置连边起点")
            return False
        start_point_id = self.edge_start_point_id
        self.edge_start_point_id = ""
        self.partEditChanged.emit()
        if not point_id:
            self._set_status_text("终点不能为空")
            return False
        if point_id == start_point_id:
            self._set_status_text("连边终点不能与起点相同")
            return False
        return self.addSketchEdge(start_point_id, point_id)

    @Slot(result=bool)
    def clearEdgeStartPoint(self) -> bool:
        self.edge_start_point_id = ""
        self.partEditChanged.emit()
        self._set_status_text("已清除连边起点")
        return True

    @Slot(float, float, result=bool)
    def addSketchPointFromViewport(self, x: float, y: float) -> bool:
        try:
            self._ensure_single_model_part()
            return self.addSketchPoint(x, y)
        except Exception as exc:
            self._set_status_text(f"视口新增模型点失败: {exc}")
            return False

    @Slot(float, float, result=bool)
    def addModelPointFromViewport(self, x: float, y: float) -> bool:
        return self.addSketchPointFromViewport(x, y)

    @Slot(float, float, result=bool)
    def addModelPoint(self, x: float, y: float) -> bool:
        try:
            self._ensure_single_model_part()
            return self.addSketchPoint(x, y)
        except Exception as exc:
            self._set_status_text(f"新增模型点失败: {exc}")
            return False

    @Slot(float, float, result=bool)
    def updateSelectedSketchPoint(self, x: float, y: float) -> bool:
        if not self.selected_sketch_point_id:
            self._set_status_text("请先选择草图点")
            return False
        return self.moveSketchPoint(self.selected_sketch_point_id, x, y)

    @Slot(result=bool)
    def deleteSelectedSketchEntity(self) -> bool:
        if self.selected_sketch_point_id:
            return self.deleteSketchPoint(self.selected_sketch_point_id)
        if self.selected_sketch_edge_id:
            return self.deleteSketchEdge(self.selected_sketch_edge_id)
        self._set_status_text("请先选择要删除的节点或边")
        return False

    @Slot(str, float, float, str, result=bool)
    @Slot(str, float, float, str, float, result=bool)
    def addMaterial(
        self,
        name: str,
        young_modulus: float,
        poisson_ratio: float,
        color: str,
        unit_weight: float = 0.0,
    ) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        try:
            add_material(self.current_project, name, young_modulus, poisson_ratio, color, unit_weight)
            self.project_dirty = True
            self._sync_material_state_from_project()
            self._set_status_text("已新增材料")
            self.projectChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"新增材料失败: {exc}")
            return False

    @Slot(str, str, float, float, str, result=bool)
    @Slot(str, str, float, float, str, float, result=bool)
    def updateMaterial(
        self,
        material_id: str,
        name: str,
        young_modulus: float,
        poisson_ratio: float,
        color: str,
        unit_weight: float = 0.0,
    ) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        try:
            update_material(
                self.current_project,
                material_id,
                name,
                young_modulus,
                poisson_ratio,
                color,
                unit_weight,
            )
            self.project_dirty = True
            self._clear_solution()
            self._sync_material_state_from_project()
            self._set_status_text("已更新材料")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"更新材料失败: {exc}")
            return False

    @Slot(str, result=bool)
    def deleteMaterial(self, material_id: str) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        try:
            delete_material(self.current_project, material_id)
            self.project_dirty = True
            self._clear_solution()
            self._sync_material_state_from_project()
            self._set_status_text("已删除材料")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"删除材料失败: {exc}")
            return False

    @Slot(str, float, result=bool)
    def assignMaterialToActivePart(self, material_id: str, thickness: float) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        if not self.active_part_id:
            self._set_status_text("没有活动零件")
            return False
        try:
            assign_material_to_part(self.current_project, self.active_part_id, material_id, thickness)
            self.project_dirty = True
            self._clear_solution()
            self._sync_material_state_from_project()
            self._sync_parameter_cache_from_project()
            self._set_status_text("已应用材料到当前零件")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"应用材料失败: {exc}")
            return False

    @Slot(str, float, result=bool)
    def assignMaterialToSelectedFace(self, material_id: str, thickness: float) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        if not self.active_part_id:
            self._set_status_text("没有活动模型")
            return False
        if not self.selected_sketch_face_id:
            self._set_status_text("请先选择闭合面")
            return False
        try:
            assign_material_to_face(
                self.current_project,
                self.active_part_id,
                self.selected_sketch_face_id,
                material_id,
                thickness,
            )
            self.project_dirty = True
            self._clear_solution()
            self._sync_material_state_from_project()
            self._sync_parameter_cache_from_project()
            self._set_status_text(f"已应用材料到闭合面 {self.selected_sketch_face_id}")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"应用闭合面材料失败: {exc}")
            return False

    @Slot(str, float, result=bool)
    def assignMaterialToAllFaces(self, material_id: str, thickness: float) -> bool:
        return self.assignMaterialToActivePart(material_id, thickness)

    @Slot(float, float, float, result=bool)
    def generateQualityMeshForActivePart(
        self,
        target_size: float,
        max_area: float,
        min_angle: float,
    ) -> bool:
        return self._generate_quality_mesh_for_active_part(
            target_size,
            max_area,
            min_angle,
            manage_busy=True,
        )

    def _generate_quality_mesh_for_active_part(
        self,
        target_size: float,
        max_area: float,
        min_angle: float,
        manage_busy: bool,
    ) -> bool:
        if manage_busy:
            self._begin_busy("正在生成网格", "准备生成网格", "mesh_prepare", 0)
        try:
            self._update_busy(10, "检查几何和闭合面", "mesh_geometry")
            part = self._require_active_part()
            self._update_busy(20, "检查材料和网格参数", "mesh_parameters")
            resolved_max_area = max_area if max_area > 0.0 else None
            self._update_busy(30, "调用 Gmsh 生成三角网格", "mesh_generate")
            print("[MESH] before gmsh", flush=True)
            mesh = generate_quality_sketch_tri_mesh(
                part.geometry,
                target_size=target_size,
                max_area=resolved_max_area,
                min_angle=min_angle,
            )
            print("[MESH] after gmsh", flush=True)
            self._update_busy(70, "读取 Gmsh 网格结果", "mesh_readback")
            self.current_sketch_mesh = mesh
            self.mesh_target_size = float(target_size)
            self.mesh_max_area = float(max_area)
            self.mesh_min_angle = float(min_angle)
            self.current_mesh_type = str(mesh.metadata.get("mesh_type", "sketch_quality"))
            self._clear_solution()
            self.resultChanged.emit()
            self._update_busy(85, "建立几何边界映射", "mesh_mapping")
            self._update_busy(95, "计算网格质量", "mesh_quality")
            self._sync_sketch_mesh_from_current_mesh()
            self._update_busy(100, "网格生成完成", "mesh_done")
            self._set_status_text(
                f"高质量网格生成成功：节点 {self.sketch_mesh_node_count}，单元 {self.sketch_mesh_element_count}"
            )
            return True
        except Exception as exc:
            self._clear_sketch_mesh(emit_signal=True)
            self._set_status_text(f"生成高质量网格失败: {exc}")
            return False
        finally:
            if manage_busy:
                self._finish_busy()

    @Slot(result=bool)
    def clearCurrentMesh(self) -> bool:
        self._clear_sketch_mesh(emit_signal=True)
        self._clear_solution()
        self.resultChanged.emit()
        self._set_status_text("已清除当前网格")
        return True

    @Slot(result=bool)
    def clearMesh(self) -> bool:
        return self.clearCurrentMesh()

    @Slot(float, float, result=bool)
    def generateMesh(self, target_size: float, min_angle: float) -> bool:
        return self.generateQualityMeshForActivePart(target_size, 0.0, min_angle)

    @Slot(float, float, result=bool)
    def generateMeshAsync(self, target_size: float, min_angle: float) -> bool:
        if self.is_busy:
            self._set_status_text("当前任务正在进行，请稍候。")
            return False
        self._begin_busy("正在生成网格", "准备生成网格...", "mesh", 0, indeterminate=True)
        QTimer.singleShot(0, lambda: self._run_generate_mesh_sync_after_overlay(float(target_size), float(min_angle)))
        return True

    @Slot(str, result=bool)
    def selectGeometryPoint(self, point_id: str) -> bool:
        try:
            if not self.selectSketchPoint(point_id):
                return False
            self.selected_sketch_face_id = ""
            self.geometry_target_type = "point" if point_id else ""
            self.geometry_target_id = str(point_id).strip()
            self.selected_geometry_type = "point" if point_id else ""
            self.selected_geometry_id = str(point_id).strip()
            self.partEditChanged.emit()
            self.sketchChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"选择几何点失败: {exc}")
            return False

    @Slot(str, result=bool)
    def selectGeometryEdge(self, edge_id: str) -> bool:
        try:
            if not self.selectSketchEdge(edge_id):
                return False
            self.selected_sketch_face_id = ""
            self.geometry_target_type = "edge" if edge_id else ""
            self.geometry_target_id = str(edge_id).strip()
            self.selected_geometry_type = "edge" if edge_id else ""
            self.selected_geometry_id = str(edge_id).strip()
            if edge_id and self.edge_load_segment_edge_id and self.edge_load_segment_edge_id != edge_id:
                self._clear_edge_load_segment_range(emit_signal=False)
            self.partEditChanged.emit()
            self.sketchChanged.emit()
            self.projectChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"选择几何边失败: {exc}")
            return False

    @Slot(bool, bool, result=bool)
    def addFixedConstraintToSelectedTarget(self, ux_fixed: bool, uy_fixed: bool) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        if self.geometry_target_type not in {"point", "edge"} or not self.geometry_target_id:
            self._set_status_text("请先选择点或边作为约束目标")
            return False
        if not ux_fixed and not uy_fixed:
            self._set_status_text("至少需要固定一个方向")
            return False
        try:
            step_id = self._default_step_id()
            next_id = self._next_definition_id("bc", [bc.id for bc in self.current_project.boundary_conditions])
            self.current_project.add_boundary_condition(
                BoundaryConditionDefinition(
                    id=next_id,
                    name=f"约束_{self.geometry_target_id}",
                    step_id=step_id,
                    target_type="geometry_point" if self.geometry_target_type == "point" else "geometry_edge",
                    target_id=self.geometry_target_id,
                    ux_fixed=ux_fixed,
                    uy_fixed=uy_fixed,
                )
            )
            self.project_dirty = True
            self._clear_solution()
            self._sync_boundary_load_state_from_project()
            self._set_status_text("已添加约束")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"添加约束失败: {exc}")
            return False

    @Slot(bool, bool, result=bool)
    def addConstraintToSelectedTarget(self, ux_fixed: bool, uy_fixed: bool) -> bool:
        return self.addFixedConstraintToSelectedTarget(ux_fixed, uy_fixed)

    @Slot(result=bool)
    def clearConstraints(self) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        self.current_project.boundary_conditions = []
        self.project_dirty = True
        self._clear_solution()
        self._sync_boundary_load_state_from_project()
        self._set_status_text("已清除全部约束")
        self.projectChanged.emit()
        self.resultChanged.emit()
        return True

    @Slot(str, result=bool)
    def deleteBoundaryCondition(self, boundary_condition_id: str) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        rows = [bc for bc in self.current_project.boundary_conditions if bc.id != boundary_condition_id]
        if len(rows) == len(self.current_project.boundary_conditions):
            self._set_status_text(f"约束不存在：{boundary_condition_id}")
            return False
        self.current_project.boundary_conditions = rows
        self.project_dirty = True
        self._clear_solution()
        self._sync_boundary_load_state_from_project()
        self._set_status_text("已删除约束")
        self.projectChanged.emit()
        self.resultChanged.emit()
        return True

    @Slot(str, float, float, result=bool)
    def addLoadToSelectedTarget(self, load_type: str, fx_or_qx: float, fy_or_qy: float) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        if self.geometry_target_type not in {"point", "edge"} or not self.geometry_target_id:
            self._set_status_text("请先选择点或边作为载荷目标")
            return False
        if load_type == "nodal_concentrated" and self.geometry_target_type != "point":
            self._set_status_text("集中力只能作用于几何点")
            return False
        if load_type == "edge_uniform" and self.geometry_target_type != "edge":
            self._set_status_text("边均布载荷只能作用于几何边")
            return False
        try:
            step_id = self._default_step_id()
            next_id = self._next_definition_id("load", [load.id for load in self.current_project.loads])
            target_type = "geometry_point" if self.geometry_target_type == "point" else "geometry_edge"
            start_t = 0.0
            end_t = 1.0
            if load_type == "edge_uniform" and self.geometry_target_type == "edge" and self.edge_load_has_custom_range:
                start_t = self.edge_load_start_t
                end_t = self.edge_load_end_t
            self.current_project.add_load(
                LoadDefinition(
                    id=next_id,
                    name=f"载荷_{self.geometry_target_id}",
                    step_id=step_id,
                    target_type=target_type,
                    target_id=self.geometry_target_id,
                    load_type=load_type,
                    qx=float(fx_or_qx),
                    qy=float(fy_or_qy),
                    start_t=start_t,
                    end_t=end_t,
                )
            )
            self.project_dirty = True
            self._clear_solution()
            self._sync_boundary_load_state_from_project()
            self._set_status_text("已添加载荷")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"添加载荷失败: {exc}")
            return False

    @Slot(result=bool)
    def useFullEdgeLoadRange(self) -> bool:
        self._clear_edge_load_segment_range(emit_signal=True)
        self._set_status_text("已设置为整条边均布载荷")
        return True

    @Slot(float, float, result=bool)
    def setSelectedEdgeLoadSegmentRange(self, start_t: float, end_t: float) -> bool:
        if self.geometry_target_type != "edge" or not self.geometry_target_id:
            self._set_status_text("请先选择一条几何边")
            return False
        try:
            start = float(min(start_t, end_t))
            end = float(max(start_t, end_t))
            if start < 0.0 or end > 1.0:
                raise ValueError("start_t/end_t 必须位于 [0, 1]")
            if end - start <= 1.0e-9:
                raise ValueError("载荷区间长度过短")
            self.edge_load_segment_edge_id = self.geometry_target_id
            self.edge_load_start_t = start
            self.edge_load_end_t = end
            self.edge_load_has_custom_range = True
            self.edge_load_segment_selection_mode = False
            self.edge_load_segment_first_t = -1.0
            self.projectChanged.emit()
            self._set_status_text(
                f"已设置局部载荷区间: {self.geometry_target_id} [{start:.4f}, {end:.4f}]"
            )
            return True
        except Exception as exc:
            self._set_status_text(f"设置载荷区间失败: {exc}")
            return False

    @Slot(result=bool)
    def beginEdgeLoadSegmentSelection(self) -> bool:
        if self.geometry_target_type != "edge" or not self.geometry_target_id:
            self._set_status_text("请先选择一条几何边")
            return False
        self.edge_load_segment_selection_mode = True
        self.edge_load_segment_edge_id = self.geometry_target_id
        self.edge_load_segment_first_t = -1.0
        self.projectChanged.emit()
        self._set_status_text("已进入局部载荷区间选择模式")
        return True

    @Slot(result=bool)
    def cancelEdgeLoadSegmentSelection(self) -> bool:
        self.edge_load_segment_selection_mode = False
        self.edge_load_segment_edge_id = ""
        self.edge_load_segment_first_t = -1.0
        self.projectChanged.emit()
        self._set_status_text("已取消局部载荷区间选择")
        return True

    @Slot(str, float, float, result=bool)
    def captureEdgeLoadSegmentSelectionPoint(self, edge_id: str, x: float, y: float) -> bool:
        if not self.edge_load_segment_selection_mode:
            self._set_status_text("当前未进入局部载荷区间选择模式")
            return False
        try:
            edge_id = str(edge_id).strip()
            projected_t = self._project_point_to_edge_parameter(edge_id, float(x), float(y))
            if not self.edge_load_segment_edge_id:
                self.edge_load_segment_edge_id = edge_id
            if self.edge_load_segment_edge_id != edge_id:
                raise ValueError("第二次点击必须仍在同一条边上")
            if self.edge_load_segment_first_t < 0.0:
                self.edge_load_segment_first_t = projected_t
                self.selectGeometryEdge(edge_id)
                self.projectChanged.emit()
                self._set_status_text(f"已记录区间起点: {edge_id} t={projected_t:.4f}")
                return True
            return self.setSelectedEdgeLoadSegmentRange(self.edge_load_segment_first_t, projected_t)
        except Exception as exc:
            self._set_status_text(f"点击设置载荷区间失败: {exc}")
            return False

    @Slot(result=bool)
    def clearLoads(self) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        self.current_project.loads = []
        self.project_dirty = True
        self._clear_solution()
        self._sync_boundary_load_state_from_project()
        self._set_status_text("已清除全部载荷")
        self.projectChanged.emit()
        self.resultChanged.emit()
        return True

    @Slot(bool, result=bool)
    def setGravityEnabled(self, enabled: bool) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        self.current_project.metadata["gravity_enabled"] = bool(enabled)
        self.current_project.metadata.setdefault("gravity_direction_x", 0.0)
        self.current_project.metadata.setdefault("gravity_direction_y", -1.0)
        self.project_dirty = True
        self._clear_solution()
        self._sync_boundary_load_state_from_project()
        self._set_status_text("已启用自重求解" if enabled else "已关闭自重求解")
        self.projectChanged.emit()
        self.resultChanged.emit()
        return True

    @Slot(str, result=bool)
    def deleteLoad(self, load_id: str) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        rows = [load for load in self.current_project.loads if load.id != load_id]
        if len(rows) == len(self.current_project.loads):
            self._set_status_text(f"载荷不存在：{load_id}")
            return False
        self.current_project.loads = rows
        self.project_dirty = True
        self._clear_solution()
        self._sync_boundary_load_state_from_project()
        self._set_status_text("已删除载荷")
        self.projectChanged.emit()
        self.resultChanged.emit()
        return True

    @Slot(result=bool)
    def solveCurrentModel(self) -> bool:
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        self._begin_busy("正在求解", "准备求解", "solve_prepare", 0)
        try:
            self._update_busy(5, "检查几何、材料、网格、约束和载荷", "solve_validate")
            part = self._require_active_part()
            edge_ids = {edge.id for edge in part.geometry.edges}
            if {"bottom", "right", "top", "left"}.issubset(edge_ids):
                return self.solveCurrentProject(self.project_mesh_nx, self.project_mesh_ny)

            if not part.geometry.faces:
                self._set_status_text("求解失败: 当前草图尚未生成闭合面")
                return False
            if not self.current_project.boundary_conditions:
                self._set_status_text("求解失败: 当前模型缺少约束")
                return False
            if not self.current_project.loads and not self.gravityEnabled:
                self._set_status_text("求解失败: 当前模型缺少载荷")
                return False
            if self.current_sketch_mesh is None or self.current_mesh_type != "sketch_quality":
                self._update_busy(10, "生成求解所需网格", "solve_mesh")
                if not self._generate_quality_mesh_for_active_part(
                    self.mesh_target_size,
                    self.mesh_max_area,
                    self.mesh_min_angle,
                    manage_busy=False,
                ):
                    return False

            step_id = self._default_step_id()
            self._update_busy(15, "编译工程模型", "solve_compile")
            temp_project = EngineeringProject(
                name=f"{self.current_project.name}_active_model",
                materials=list(self.current_project.materials),
                sections=list(self.current_project.sections),
                parts=[part],
                assembly=self.current_project.assembly,
                analysis_steps=list(self.current_project.analysis_steps),
                loads=list(self.current_project.loads),
                boundary_conditions=list(self.current_project.boundary_conditions),
                metadata=dict(self.current_project.metadata),
            )
            compiled_bundle = compile_workbench_project(
                project=temp_project,
                mesh=self.current_sketch_mesh,
                step_id=step_id,
            )
            self._update_busy(30, "组装有限元方程", "solve_assemble")
            self._update_busy(45, "施加边界条件", "solve_boundary")
            self._update_busy(60, "求解线性方程组", "solve_linear")
            solver_result = solve_static_linear(compiled_bundle.fem_model)
            self._update_busy(75, "计算节点位移和单元应力", "solve_post")
            solution = WorkbenchSolveResult(
                project=temp_project,
                mesh=self.current_sketch_mesh,
                compiled_bundle=compiled_bundle,
                solver_result=solver_result,
                warnings=list(compiled_bundle.warnings),
            )
            self.current_solution = solution
            self.node_rows = build_node_displacement_rows(solution)
            self.element_rows = build_element_result_rows(solution)
            self.summary = build_result_summary(solution)
            self._store_solution_rows(progress_callback=self._update_busy)
            self._update_busy(100, "求解完成", "solve_done")
            if self.contour_image_cache_valid:
                self._set_status_text(
                    f"求解完成，云图数据和图片缓存已生成：当前模型节点 {self.summary.node_count}，单元 {self.summary.element_count}"
                )
            else:
                self._set_status_text(
                    f"求解成功，但云图图片缓存生成失败：当前模型节点 {self.summary.node_count}，单元 {self.summary.element_count}"
                )
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._clear_solution()
            self.resultChanged.emit()
            self._set_status_text(f"求解失败: {exc}")
            return False
        finally:
            self._finish_busy()

    @Slot(result=bool)
    def solveCurrentModelAsync(self) -> bool:
        if self.is_busy:
            self._set_status_text("当前任务正在进行，请稍候。")
            return False
        if self.current_project is None:
            self._set_status_text("请先新建或打开工程")
            return False
        self._begin_busy("正在求解", "准备求解...", "solve", 0, indeterminate=True)
        QTimer.singleShot(0, self._prepare_and_start_solve_worker)
        return True

    @Slot(result=bool)
    def clearResults(self) -> bool:
        self._clear_solution()
        self.resultChanged.emit()
        self._set_status_text("已清除结果")
        return True

    @Slot(float, float, result=bool)
    def queryResultAtPoint(self, x: float, y: float) -> bool:
        if self.current_solution is None or not self.node_rows:
            self._set_status_text("请先完成求解，再查询结果")
            return False
        try:
            x = float(x)
            y = float(y)
            nearest = min(self.node_rows, key=lambda row: (row.x - x) ** 2 + (row.y - y) ** 2)
            self.result_query_x = x
            self.result_query_y = y
            self.result_query_text = (
                f"查询点 ({x:.6g}, {y:.6g})\n"
                f"最近节点: {nearest.node_id}\n"
                f"ux = {nearest.ux:.6e}\n"
                f"uy = {nearest.uy:.6e}\n"
                f"|u| = {nearest.u_magnitude:.6e}"
            )
            self.resultChanged.emit()
            self._set_status_text("已更新结果查询")
            return True
        except Exception as exc:
            self._set_status_text(f"结果查询失败: {exc}")
            return False

    @Slot(result=bool)
    def createEmptySketchForActivePart(self) -> bool:
        try:
            part = self._require_active_part()
            part.geometry = create_empty_sketch_geometry()
            self.current_project.loads = []
            self.current_project.boundary_conditions = []
            self._reset_sketch_boundary_load_state(reset_load_values=True)
            self.selected_sketch_point_id = ""
            self.edge_start_point_id = ""
            self.project_dirty = True
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_sketch_from_active_part()
            self._sync_boundary_load_state_from_project()
            self._set_status_text("已为活动零件创建空草图")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"创建空草图失败: {exc}")
            return False

    @Slot(float, float, result=bool)
    def addSketchPoint(self, x: float, y: float) -> bool:
        try:
            part = self._require_active_part()
            add_sketch_point(part.geometry, x, y)
            self.project_dirty = True
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_sketch_from_active_part()
            self._set_status_text("已新增草图点")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"新增草图点失败: {exc}")
            return False

    @Slot(str, float, float, result=bool)
    def moveSketchPoint(self, point_id: str, x: float, y: float) -> bool:
        try:
            part = self._require_active_part()
            move_sketch_point(part.geometry, point_id, x, y)
            self.project_dirty = True
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_sketch_from_active_part()
            self._set_status_text("已移动草图点")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"移动草图点失败: {exc}")
            return False

    @Slot(str, result=bool)
    def deleteSketchPoint(self, point_id: str) -> bool:
        try:
            part = self._require_active_part()
            delete_sketch_point(part.geometry, point_id)
            if self.selected_sketch_point_id == point_id:
                self.selected_sketch_point_id = ""
            self.project_dirty = True
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_sketch_from_active_part()
            self._set_status_text("已删除草图点")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"删除草图点失败: {exc}")
            return False

    @Slot(str, str, result=bool)
    def addSketchEdge(self, start_point_id: str, end_point_id: str) -> bool:
        try:
            part = self._require_active_part()
            add_sketch_edge(part.geometry, start_point_id.strip(), end_point_id.strip())
            self.project_dirty = True
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_sketch_from_active_part()
            self._set_status_text("已新增草图边")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"新增草图边失败: {exc}")
            return False

    @Slot(str, str, result=bool)
    def connectModelEdge(self, start_point_id: str, end_point_id: str) -> bool:
        try:
            self._ensure_single_model_part()
            return self.addSketchEdge(start_point_id, end_point_id)
        except Exception as exc:
            self._set_status_text(f"连接模型边失败: {exc}")
            return False


    @Slot(str, result=bool)
    def deleteSketchEdge(self, edge_id: str) -> bool:
        try:
            part = self._require_active_part()
            delete_sketch_edge(part.geometry, edge_id.strip())
            self.project_dirty = True
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_sketch_from_active_part()
            self._set_status_text("已删除草图边")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"删除草图边失败: {exc}")
            return False

    @Slot(result=bool)
    def buildSketchFace(self) -> bool:
        try:
            part = self._require_active_part()
            if self.edge_start_point_id:
                self.edge_start_point_id = ""
                self.partEditChanged.emit()
            build_faces_from_edges(part.geometry)
            normalization_stats = getattr(part.geometry, "_normalization_stats", {}) or {}
            split_edge_count = int(normalization_stats.get("split_edge_count", 0) or 0)
            self.project_dirty = True
            self.clearSelection()
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_sketch_from_active_part()
            self._sync_material_state_from_project()
            if split_edge_count > 0:
                self._set_status_text(
                    f"已自动拆分 {split_edge_count} 条边，生成 {len(part.geometry.faces)} 个闭合面。"
                )
            else:
                self._set_status_text(f"已生成 {len(part.geometry.faces)} 个闭合面")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._sync_sketch_from_active_part()
            self._set_status_text(f"生成闭合面失败: {exc}")
            return False

    @Slot(result=bool)
    def buildModelFaces(self) -> bool:
        try:
            self._ensure_single_model_part()
            return self.buildSketchFace()
        except Exception as exc:
            self._set_status_text(f"生成模型闭合面失败: {exc}")
            return False

    @Slot(result=bool)
    def clearSketch(self) -> bool:
        try:
            part = self._require_active_part()
            clear_sketch_geometry(part.geometry)
            self.selected_sketch_point_id = ""
            self._reset_sketch_boundary_load_state(reset_load_values=True)
            self.project_dirty = True
            self._clear_solution()
            self._clear_sketch_mesh(emit_signal=True)
            self._sync_sketch_from_active_part()
            self._set_status_text("已清空草图")
            self.projectChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"清空草图失败: {exc}")
            return False

    @Slot(result=bool)
    def clearModelGeometry(self) -> bool:
        try:
            self._ensure_single_model_part()
            return self.clearSketch()
        except Exception as exc:
            self._set_status_text(f"清空模型几何失败: {exc}")
            return False


    @Slot(str, result=bool)
    def selectSketchPoint(self, point_id: str) -> bool:
        try:
            part = self._require_active_part()
            if point_id and not any(point.id == point_id for point in part.geometry.points):
                raise ValueError(f"Unknown sketch point id: {point_id}")
            self.selected_sketch_point_id = point_id
            self._set_status_text(f"已选择草图点：{point_id}" if point_id else "已清除草图点选择")
            self.sketchChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"选择草图点失败: {exc}")
            return False

    @Slot(str, result=bool)
    def selectSketchEdge(self, edge_id: str) -> bool:
        try:
            part = self._require_active_part()
            edge_id = str(edge_id).strip()
            if edge_id and not any(edge.id == edge_id for edge in part.geometry.edges):
                raise ValueError(f"Unknown sketch edge id: {edge_id}")
            self.selected_sketch_edge_id = edge_id
            if edge_id:
                self._set_status_text(f"已选择草图边：{edge_id}")
            else:
                self._set_status_text("已清除草图边选择")
            self.sketchChanged.emit()
            return True
        except Exception as exc:
            self._set_status_text(f"选择草图边失败: {exc}")
            return False

    @Slot(str, result=bool)
    def selectGeometryFace(self, face_id: str) -> bool:
        try:
            part = self._require_active_part()
            face_id = str(face_id).strip()
            if face_id and not any(face.id == face_id for face in part.geometry.faces):
                raise ValueError(f"Unknown face id: {face_id}")
            self.selected_sketch_face_id = face_id
            self.selected_sketch_point_id = ""
            self.selected_sketch_edge_id = ""
            self.selected_geometry_type = "face" if face_id else ""
            self.selected_geometry_id = face_id
            self.geometry_target_type = ""
            self.geometry_target_id = ""
            self.sketchChanged.emit()
            self.partEditChanged.emit()
            self._set_status_text(f"已选择闭合面：{face_id}" if face_id else "已清除闭合面选择")
            return True
        except Exception as exc:
            self._set_status_text(f"选择闭合面失败: {exc}")
            return False

    @Slot(result=bool)
    def clearSelection(self) -> bool:
        self.selected_sketch_point_id = ""
        self.selected_sketch_edge_id = ""
        self.selected_sketch_face_id = ""
        self.selected_geometry_type = ""
        self.selected_geometry_id = ""
        self.geometry_target_type = ""
        self.geometry_target_id = ""
        self.edge_start_point_id = ""
        self.sketchChanged.emit()
        self.partEditChanged.emit()
        return True


    @Slot(result=bool)
    def setSelectedSketchEdgeAsFixed(self) -> bool:
        if not self.selected_sketch_edge_id:
            self._set_status_text("请先选择草图边")
            return False
        self.sketch_fixed_edge_id = self.selected_sketch_edge_id
        self._set_status_text(f"已设置固定边：{self.sketch_fixed_edge_id}")
        self.sketchChanged.emit()
        return True

    @Slot(result=bool)
    def setSelectedSketchEdgeAsLoad(self) -> bool:
        if not self.selected_sketch_edge_id:
            self._set_status_text("请先选择草图边")
            return False
        self.sketch_load_edge_id = self.selected_sketch_edge_id
        self._set_status_text(f"已设置载荷边：{self.sketch_load_edge_id}")
        self.sketchChanged.emit()
        return True

    @Slot(float, float, result=bool)
    def setSketchLoadValues(self, qx: float, qy: float) -> bool:
        self.sketch_load_qx = float(qx)
        self.sketch_load_qy = float(qy)
        self._set_status_text("已更新草图载荷")
        self.sketchChanged.emit()
        return True

    @Slot(result=bool)
    def clearSketchBoundaryLoadSelection(self) -> bool:
        self._reset_sketch_boundary_load_state(reset_load_values=True)
        self._set_status_text("已清除草图边界/载荷设置")
        self.sketchChanged.emit()
        return True

    @Slot(result=bool)
    def generateSketchMeshForActivePart(self) -> bool:
        try:
            part = self._require_active_part()
            mesh = generate_sketch_tri_mesh(part.geometry)
            self.current_sketch_mesh = mesh
            self.current_mesh_type = "sketch_ear_clip"
            self._sync_sketch_mesh_from_current_mesh()
            self._set_status_text(
                f"草图网格生成成功：节点 {self.sketch_mesh_node_count}，单元 {self.sketch_mesh_element_count}"
            )
            return True
        except Exception as exc:
            self._clear_sketch_mesh(emit_signal=True)
            self._set_status_text(f"生成草图网格失败: {exc}")
            return False

    @Slot(result=bool)
    def clearSketchMesh(self) -> bool:
        self._clear_sketch_mesh(emit_signal=True)
        self._set_status_text("已清除草图网格")
        return True

    @Slot(str, str, float, float, result=bool)
    def solveSketchProject(
        self,
        fixed_edge_id: str,
        load_edge_id: str,
        qx: float,
        qy: float,
    ) -> bool:
        if self.current_project is None:
            self._set_status_text("请先创建工程或打开工程")
            return False

        self._begin_busy("正在求解", "准备求解", "solve_prepare", 0)
        fixed_edge_id = str(fixed_edge_id).strip() or self.sketch_fixed_edge_id
        load_edge_id = str(load_edge_id).strip() or self.sketch_load_edge_id
        if not fixed_edge_id:
            self._set_status_text("草图求解失败: 固定边 ID 不能为空")
            return False
        if not load_edge_id:
            self._set_status_text("草图求解失败: 载荷边 ID 不能为空")
            return False

        try:
            part = self._require_active_part()
            geometry_edge_ids = {edge.id for edge in part.geometry.edges}
            if fixed_edge_id not in geometry_edge_ids:
                self._set_status_text(f"草图求解失败: 固定边不存在：{fixed_edge_id}")
                return False
            if load_edge_id not in geometry_edge_ids:
                self._set_status_text(f"草图求解失败: 载荷边不存在：{load_edge_id}")
                return False
            if not part.geometry.faces:
                self._set_status_text("草图求解失败: 请先生成闭合二维面")
                return False
            if qx == 0.0 and qy == 0.0:
                self._set_status_text("草图求解失败: 载荷 qx/qy 不能同时为 0")
                return False

            self.sketch_fixed_edge_id = fixed_edge_id
            self.sketch_load_edge_id = load_edge_id
            self.sketch_load_qx = float(qx)
            self.sketch_load_qy = float(qy)

            if self.current_sketch_mesh is None:
                mesh = generate_sketch_tri_mesh(part.geometry)
                self.current_sketch_mesh = mesh
                self._sync_sketch_mesh_from_current_mesh()
            else:
                mesh = self.current_sketch_mesh

            step_id = "step_static"
            if self.current_project.get_analysis_step_by_id(step_id) is None:
                if not self.current_project.analysis_steps:
                    raise ValueError("当前工程没有可用分析步")
                step_id = self.current_project.analysis_steps[0].id

            sketch_project = EngineeringProject(
                name=f"{self.current_project.name}_sketch_solve",
                materials=list(self.current_project.materials),
                sections=list(self.current_project.sections),
                parts=[part],
                analysis_steps=list(self.current_project.analysis_steps),
                loads=[
                    LoadDefinition(
                        id="sketch_edge_load",
                        name="草图边均布载荷",
                        step_id=step_id,
                        target_type="geometry_edge",
                        target_id=load_edge_id,
                        load_type="edge_uniform",
                        qx=qx,
                        qy=qy,
                    )
                ],
                boundary_conditions=[
                    BoundaryConditionDefinition(
                        id="sketch_fixed_edge",
                        name="草图边固定约束",
                        step_id=step_id,
                        target_type="geometry_edge",
                        target_id=fixed_edge_id,
                        ux_fixed=True,
                        uy_fixed=True,
                    )
                ],
                metadata=dict(self.current_project.metadata),
            )

            compiled_bundle = compile_workbench_project(
                project=sketch_project,
                mesh=mesh,
                step_id=step_id,
            )
            self._update_busy(60, "求解线性方程组", "solve_linear")
            solver_result = solve_static_linear(compiled_bundle.fem_model)

            solution = WorkbenchSolveResult(
                project=sketch_project,
                mesh=mesh,
                compiled_bundle=compiled_bundle,
                solver_result=solver_result,
                warnings=list(compiled_bundle.warnings),
            )
            self.current_solution = solution
            self.node_rows = build_node_displacement_rows(solution)
            self.element_rows = build_element_result_rows(solution)
            self.summary = build_result_summary(solution)
            self._store_solution_rows(progress_callback=self._update_busy)
            self._update_busy(100, "求解完成", "solve_done")
            if self.contour_image_cache_valid:
                self._set_status_text(
                    f"草图求解完成，云图数据和图片缓存已生成：固定边 {fixed_edge_id}，载荷边 {load_edge_id}，"
                    f"节点 {self.summary.node_count}，单元 {self.summary.element_count}"
                )
            else:
                self._set_status_text(
                    f"草图求解成功，但云图图片缓存生成失败：固定边 {fixed_edge_id}，载荷边 {load_edge_id}，"
                    f"节点 {self.summary.node_count}，单元 {self.summary.element_count}"
                )
            self.sketchChanged.emit()
            self.resultChanged.emit()
            return True
        except Exception as exc:
            self._clear_solution()
            self.resultChanged.emit()
            self._set_status_text(f"草图求解失败: {exc}")
            return False
        finally:
            self._finish_busy()

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
            export_deformation_plot_data_json(
                self.current_solution,
                output_path / "deformation_plot_data.json",
            )
            export_displacement_contour_data_json(
                self.current_solution,
                output_path / "displacement_contour_data.json",
            )
            export_stress_contour_data_json(
                self.current_solution,
                output_path / "stress_contour_data.json",
            )
            self._set_status_text(f"结果已导出到 {output_path}")
            return True
        except Exception as exc:
            self._set_status_text(f"导出失败: {exc}")
            return False

    @Slot(str, result=bool)
    def exportNodeResults(self, output_dir: str = "outputs/latest") -> bool:
        if self.current_solution is None:
            self._set_status_text("请先求解后再导出节点结果")
            return False

        try:
            output_path = Path(output_dir)
            export_node_displacements_csv(
                self.current_solution,
                output_path / "node_displacements.csv",
            )
            self._set_status_text(f"节点结果已导出到 {output_path}")
            return True
        except Exception as exc:
            self._set_status_text(f"导出节点结果失败: {exc}")
            return False

    @Slot(str, result=bool)
    def exportElementResults(self, output_dir: str = "outputs/latest") -> bool:
        if self.current_solution is None:
            self._set_status_text("请先求解后再导出单元结果")
            return False

        try:
            output_path = Path(output_dir)
            export_element_results_csv(
                self.current_solution,
                output_path / "element_results.csv",
            )
            self._set_status_text(f"单元结果已导出到 {output_path}")
            return True
        except Exception as exc:
            self._set_status_text(f"导出单元结果失败: {exc}")
            return False

    @Slot(str, result=bool)
    def exportDisplacementContourData(self, output_dir: str = "outputs/latest") -> bool:
        if not self.contour_cache_valid or self.displacement_contour_json in ("", "{}"):
            self._set_status_text("云图缓存已失效，请重新求解后再导出位移云图数据")
            return False

        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            (output_path / "displacement_contour_data.json").write_text(
                self.displacement_contour_json,
                encoding="utf-8",
            )
            self._set_status_text(f"位移云图数据已导出到 {output_path}")
            return True
        except Exception as exc:
            self._set_status_text(f"导出位移云图数据失败: {exc}")
            return False

    @Slot(str, result=bool)
    def exportStressContourData(self, output_dir: str = "outputs/latest") -> bool:
        if not self.contour_cache_valid or self.stress_contour_json in ("", "{}"):
            self._set_status_text("云图缓存已失效，请重新求解后再导出应力云图数据")
            return False

        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            (output_path / "stress_contour_data.json").write_text(
                self.stress_contour_json,
                encoding="utf-8",
            )
            self._set_status_text(f"应力云图数据已导出到 {output_path}")
            return True
        except Exception as exc:
            self._set_status_text(f"导出应力云图数据失败: {exc}")
            return False

    @Slot(str, result=bool)
    def exportContourData(self, output_dir: str = "outputs/latest") -> bool:
        if not self.exportDisplacementContourData(output_dir):
            return False
        return self.exportStressContourData(output_dir)

    def _require_active_part(self):
        if self.current_project is None:
            raise ValueError("请先新建或打开工程")
        active_part_id = self.active_part_id or get_active_part_id(self.current_project)
        part = self.current_project.get_part_by_id(active_part_id)
        if part is None:
            raise ValueError(f"Unknown active part id: {active_part_id}")
        return part

    def _ensure_single_model_part(self):
        if self.current_project is None:
            if not self.newProject():
                raise ValueError("无法新建空白模型")
        part = self._require_active_part()
        if part.name != "二维模型":
            part.name = "二维模型"
        return part

    def _process_ui_events(self) -> None:
        try:
            QCoreApplication.processEvents()
        except Exception:
            return None

    def _run_generate_mesh_sync_after_overlay(self, target_size: float, min_angle: float) -> None:
        print("[MESH] start", flush=True)
        if self.current_project is None:
            self._finish_busy()
            self._set_status_text("请先新建或打开工程")
            return
        try:
            ok = self._generate_quality_mesh_for_active_part(
                target_size,
                0.0,
                min_angle,
                manage_busy=False,
            )
            if ok:
                self._set_status_text(
                    f"网格生成完成：{self.sketch_mesh_node_count} 节点 / {self.sketch_mesh_element_count} 单元"
                )
        finally:
            print("[MESH] finished", flush=True)
            self._finish_busy()

    def _prepare_and_start_solve_worker(self) -> None:
        print("[SOLVE] start", flush=True)
        if self.current_project is None:
            self._finish_busy()
            self._set_status_text("请先新建或打开工程")
            return
        try:
            part = self._require_active_part()
            edge_ids = {edge.id for edge in part.geometry.edges}
            requires_gmsh_mesh = not {"bottom", "right", "top", "left"}.issubset(edge_ids)
            if requires_gmsh_mesh and (self.current_sketch_mesh is None or self.current_mesh_type != "sketch_quality"):
                self._update_busy(10, "生成求解所需网格", "solve_mesh", indeterminate=True)
                mesh_ok = self._generate_quality_mesh_for_active_part(
                    self.mesh_target_size,
                    self.mesh_max_area,
                    self.mesh_min_angle,
                    manage_busy=False,
                )
                if not mesh_ok:
                    self._finish_busy()
                    return
        except Exception as exc:
            self._finish_busy()
            self._set_status_text(f"求解失败: {exc}")
            return
        self._start_solve_worker()

    def _start_solve_worker(self) -> None:
        if self.current_project is None:
            self._finish_busy()
            self._set_status_text("请先新建或打开工程")
            return
        try:
            project_snapshot = copy.deepcopy(self.current_project)
            active_part_id = self.active_part_id or get_active_part_id(self.current_project)
            session_cache_dir = create_contour_cache_dir(self._session_cache_id)
            mesh_snapshot = copy.deepcopy(self.current_sketch_mesh)
        except Exception as exc:
            self._finish_busy()
            self._set_status_text(f"求解失败: {exc}")
            return

        def task(progress_callback):
            return self._build_solve_payload(
                project_snapshot=project_snapshot,
                active_part_id=active_part_id,
                mesh_snapshot=mesh_snapshot,
                session_cache_dir=session_cache_dir,
                progress_callback=progress_callback,
            )

        self._launch_worker(
            task,
            success_handler=self._apply_solve_payload,
            failure_prefix="求解失败",
        )

    def _launch_worker(self, task, *, success_handler, failure_prefix: str) -> None:
        if _USE_FALLBACK:
            try:
                payload = task(self._handle_worker_progress)
            except Exception as exc:
                self._handle_worker_failed(f"{failure_prefix}: {exc}")
                return
            success_handler(payload)
            return

        self._cleanup_worker()
        thread = QThread()
        worker = FunctionWorker(task)
        worker.moveToThread(thread)
        worker.progressChanged.connect(self._handle_worker_progress)
        worker.finished.connect(success_handler)
        worker.failed.connect(lambda message: self._handle_worker_failed(f"{failure_prefix}: {message}"))
        worker.finished.connect(self._on_worker_finished_cleanup)
        worker.failed.connect(self._on_worker_failed_cleanup)
        thread.started.connect(worker.run)
        self._active_thread = thread
        self._active_worker = worker
        thread.start()

    def _cleanup_worker(self) -> None:
        worker = self._active_worker
        thread = self._active_thread
        self._active_worker = None
        self._active_thread = None
        if worker is not None and hasattr(worker, "deleteLater"):
            try:
                worker.deleteLater()
            except Exception:
                pass
        if thread is None:
            return
        try:
            thread.quit()
            thread.wait(2000)
            thread.deleteLater()
        except Exception:
            return

    def _on_worker_finished_cleanup(self, _payload=None) -> None:
        worker = self._active_worker
        thread = self._active_thread
        if worker is not None and hasattr(worker, "deleteLater"):
            worker.deleteLater()
        if thread is not None:
            thread.quit()
            thread.wait(2000)
            thread.deleteLater()
        self._active_worker = None
        self._active_thread = None

    def _on_worker_failed_cleanup(self, _message=None) -> None:
        self._on_worker_finished_cleanup()

    def _handle_worker_progress(self, progress: int, message: str, stage: str) -> None:
        self._update_busy(progress, message, stage, indeterminate=False)

    def _handle_worker_failed(self, message: str) -> None:
        self._cleanup_worker()
        self._clear_solution()
        self.resultChanged.emit()
        self._finish_busy()
        self._set_status_text(message)

    def _apply_solve_payload(self, payload: dict[str, object]) -> None:
        self._cleanup_worker()
        self.current_solution = payload["solution"]  # type: ignore[assignment]
        self.current_sketch_mesh = payload["mesh"]  # type: ignore[assignment]
        self.node_rows = list(payload["node_rows"])  # type: ignore[arg-type]
        self.element_rows = list(payload["element_rows"])  # type: ignore[arg-type]
        self.summary = payload["summary"]  # type: ignore[assignment]
        self.node_rows_json = str(payload["node_rows_json"])
        self.element_rows_json = str(payload["element_rows_json"])
        self.deformation_preview_json = str(payload["deformation_preview_json"])
        self.deformation_plot_json = self.deformation_preview_json
        self.displacement_contour_json = str(payload["displacement_contour_json"])
        self.stress_contour_json = str(payload["stress_contour_json"])
        self.stress_contour_exact_json = str(payload["stress_contour_exact_json"])
        self.stress_contour_smooth_json = str(payload["stress_contour_smooth_json"])
        self.contour_cache_valid = True
        self.contour_cache_summary_text = "云图数据缓存有效"
        self.contour_image_cache_dir = str(payload["contour_image_cache_dir"])
        self.contour_image_cache_json = str(payload["contour_image_cache_json"])
        self.contour_image_cache_valid = bool(payload["contour_image_cache_valid"])
        self._sync_sketch_mesh_from_current_mesh()
        self._finish_busy()
        if self.contour_image_cache_valid:
            self._set_status_text("求解完成，云图数据和图片缓存已生成。")
        else:
            self._set_status_text("求解成功，但云图图片缓存生成失败，可尝试重新生成。")
        self.resultChanged.emit()

    def _build_solve_payload(
        self,
        *,
        project_snapshot: EngineeringProject,
        active_part_id: str,
        mesh_snapshot: MeshModel | None,
        session_cache_dir: Path,
        progress_callback,
    ) -> dict[str, object]:
        part = project_snapshot.get_part_by_id(active_part_id)
        if part is None:
            raise ValueError(f"活动零件不存在：{active_part_id}")
        print("[SOLVE] worker start", flush=True)
        progress_callback(5, "检查几何、材料、网格、约束和载荷", "solve_validate")
        edge_ids = {edge.id for edge in part.geometry.edges}
        if {"bottom", "right", "top", "left"}.issubset(edge_ids):
            progress_callback(15, "编译工程模型", "solve_compile")
            progress_callback(30, "组装有限元方程", "solve_assemble")
            progress_callback(50, "求解线性方程组", "solve_linear")
            solution = solve_workbench_project(
                project=project_snapshot,
                part_id=active_part_id,
                step_id="step_static",
                nx=self.project_mesh_nx,
                ny=self.project_mesh_ny,
            )
            mesh = solution.mesh
        else:
            if not part.geometry.faces:
                raise ValueError("当前草图尚未生成闭合面")
            if not project_snapshot.boundary_conditions:
                raise ValueError("当前模型缺少约束")
            if not project_snapshot.loads and not bool(project_snapshot.metadata.get("gravity_enabled", False)):
                raise ValueError("当前模型缺少载荷")
            if mesh_snapshot is None:
                raise ValueError("求解失败: 缺少预生成网格")
            progress_callback(15, "编译工程模型", "solve_compile")
            mesh = mesh_snapshot
            step_id = self._default_step_id_for_project(project_snapshot)
            temp_project = EngineeringProject(
                name=f"{project_snapshot.name}_active_model",
                materials=list(project_snapshot.materials),
                sections=list(project_snapshot.sections),
                parts=[part],
                assembly=project_snapshot.assembly,
                analysis_steps=list(project_snapshot.analysis_steps),
                loads=list(project_snapshot.loads),
                boundary_conditions=list(project_snapshot.boundary_conditions),
                metadata=dict(project_snapshot.metadata),
            )
            compiled_bundle = compile_workbench_project(project=temp_project, mesh=mesh, step_id=step_id)
            progress_callback(30, "组装有限元方程", "solve_assemble")
            progress_callback(50, "求解线性方程组", "solve_linear")
            solver_result = solve_static_linear(compiled_bundle.fem_model)
            solution = WorkbenchSolveResult(
                project=temp_project,
                mesh=mesh,
                compiled_bundle=compiled_bundle,
                solver_result=solver_result,
                warnings=list(compiled_bundle.warnings),
            )

        progress_callback(65, "计算节点位移和单元应力", "solve_post")
        node_rows = build_node_displacement_rows(solution)
        element_rows = build_element_result_rows(solution)
        summary = build_result_summary(solution)
        cache_payload = self._build_solution_cache_payload(solution, node_rows, element_rows, progress_callback)
        print("[CONTOUR] start image cache", flush=True)
        progress_callback(92, "预渲染变形示意图图片", "contour_image_deformation")
        image_warning = ""
        image_map: dict[str, dict[str, str]] = {}
        image_cache_valid = False
        clear_contour_cache_dir(session_cache_dir)
        session_cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            progress_callback(95, "预渲染位移云图图片组合", "contour_image_displacement")
            progress_callback(98, "预渲染应力云图图片组合", "contour_image_stress")
            image_map = generate_contour_images(
                output_dir=session_cache_dir,
                deformation_data=cache_payload["deformation_data"],
                displacement_data=cache_payload["displacement_data"],
                stress_exact_data=cache_payload["stress_exact_data"],
                stress_smooth_data=cache_payload["stress_smooth_data"],
            )
            image_cache_valid = True
        except Exception as exc:
            image_warning = str(exc)
            image_map = {}
            image_cache_valid = False
        print("[CONTOUR] finish image cache", flush=True)
        progress_callback(100, "求解完成", "solve_done")
        print("[SOLVE] worker finished", flush=True)
        return {
            "solution": solution,
            "mesh": mesh,
            "node_rows": node_rows,
            "element_rows": element_rows,
            "summary": summary,
            "node_rows_json": cache_payload["node_rows_json"],
            "element_rows_json": cache_payload["element_rows_json"],
            "deformation_preview_json": cache_payload["deformation_preview_json"],
            "displacement_contour_json": cache_payload["displacement_contour_json"],
            "stress_contour_json": cache_payload["stress_contour_json"],
            "stress_contour_exact_json": cache_payload["stress_contour_exact_json"],
            "stress_contour_smooth_json": cache_payload["stress_contour_smooth_json"],
            "contour_image_cache_dir": str(session_cache_dir),
            "contour_image_cache_json": build_contour_image_cache_json(image_map),
            "contour_image_cache_valid": image_cache_valid,
            "contour_image_warning": image_warning,
        }

    def _build_solution_cache_payload(self, solution, node_rows, element_rows, progress_callback=None) -> dict[str, object]:
        node_rows_json = json.dumps([row.to_dict() for row in node_rows], ensure_ascii=False)
        element_rows_json = json.dumps([row.to_dict() for row in element_rows], ensure_ascii=False)
        if progress_callback is not None:
            progress_callback(72, "生成变形示意图数据", "contour_deformation")
        deformation_data = build_deformation_plot_data(solution)
        if progress_callback is not None:
            progress_callback(78, "生成位移云图数据", "contour_displacement")
        displacement_data = build_displacement_contour_data(solution)
        if progress_callback is not None:
            progress_callback(84, "生成应力云图精确模式数据", "contour_stress_exact")
        stress_data = build_stress_contour_data(solution)
        stress_exact_data = {
            "plot_type": "stress_contour_exact",
            "title": "Von Mises 应力云图",
            "mode_label": "精确模式（单元常值）",
            "scalar_label": str(stress_data.get("scalar_label", "Von Mises")),
            "unit_label": str(stress_data.get("unit_label", "Pa")),
            "elements": [
                {
                    "id": row["id"],
                    "node_ids": list(row["node_ids"]),
                    "source_face_id": row.get("source_face_id"),
                    "von_mises": row["element_von_mises"],
                }
                for row in stress_data.get("elements", [])
            ],
            "nodes": list(displacement_data.get("nodes", [])),
            "min_von_mises": float(stress_data.get("min_von_mises", 0.0) or 0.0),
            "max_von_mises": float(stress_data.get("max_von_mises", 0.0) or 0.0),
            "default_scale_factor": float(displacement_data.get("default_scale_factor", 1.0) or 1.0),
        }
        if progress_callback is not None:
            progress_callback(88, "生成应力云图平滑模式数据", "contour_stress_smooth")
        stress_smooth_data = {
            "plot_type": "stress_contour_smooth",
            "title": "Von Mises 应力云图",
            "mode_label": "平滑模式（节点平均）",
            "scalar_label": str(stress_data.get("scalar_label", "Von Mises")),
            "unit_label": str(stress_data.get("unit_label", "Pa")),
            "nodes": [
                {
                    **node,
                    "ux": next((row.ux for row in node_rows if row.node_id == int(node["id"])), 0.0),
                    "uy": next((row.uy for row in node_rows if row.node_id == int(node["id"])), 0.0),
                }
                for node in stress_data.get("nodes", [])
            ],
            "elements": [
                {
                    "id": row["id"],
                    "node_ids": list(row["node_ids"]),
                    "source_face_id": row.get("source_face_id"),
                    "nodal_smoothed_von_mises": list(row["nodal_smoothed_von_mises"]),
                }
                for row in stress_data.get("elements", [])
            ],
            "min_von_mises": float(stress_data.get("min_smoothed_von_mises", 0.0) or 0.0),
            "max_von_mises": float(stress_data.get("max_smoothed_von_mises", 0.0) or 0.0),
            "default_scale_factor": float(displacement_data.get("default_scale_factor", 1.0) or 1.0),
        }
        return {
            "node_rows_json": node_rows_json,
            "element_rows_json": element_rows_json,
            "deformation_data": deformation_data,
            "displacement_data": displacement_data,
            "stress_data": stress_data,
            "stress_exact_data": stress_exact_data,
            "stress_smooth_data": stress_smooth_data,
            "deformation_preview_json": json.dumps(deformation_data, ensure_ascii=False),
            "displacement_contour_json": json.dumps(displacement_data, ensure_ascii=False),
            "stress_contour_json": json.dumps(stress_data, ensure_ascii=False),
            "stress_contour_exact_json": json.dumps(stress_exact_data, ensure_ascii=False),
            "stress_contour_smooth_json": json.dumps(stress_smooth_data, ensure_ascii=False),
        }

    def _default_step_id_for_project(self, project: EngineeringProject) -> str:
        step_id = "step_static"
        if project.get_analysis_step_by_id(step_id) is not None:
            return step_id
        if not project.analysis_steps:
            raise ValueError("当前工程没有可用分析步")
        return project.analysis_steps[0].id

    def _set_busy_state(
        self,
        active: bool,
        title: str,
        message: str,
        progress: int,
        stage: str,
        indeterminate: bool | None = None,
    ) -> None:
        self.is_busy = bool(active)
        self.busy_title = str(title)
        self.busy_message = str(message)
        self.busy_progress = max(0, min(100, int(progress)))
        self.busy_stage = str(stage)
        if indeterminate is None:
            self.busy_indeterminate = bool(active) and self.busy_progress <= 0
        else:
            self.busy_indeterminate = bool(indeterminate)
        self.busyStateChanged.emit()
        self._process_ui_events()

    def _invoke_set_busy_state(
        self,
        active: bool,
        title: str,
        message: str,
        progress: int,
        stage: str,
        indeterminate: bool | None = None,
    ) -> None:
        try:
            self._set_busy_state(active, title, message, progress, stage, indeterminate)
        except TypeError:
            self._set_busy_state(active, title, message, progress, stage)

    def _begin_busy(
        self,
        title: str,
        message: str,
        stage: str,
        progress: int = 0,
        *,
        indeterminate: bool = False,
    ) -> None:
        self._invoke_set_busy_state(True, title, message, progress, stage, indeterminate)

    def _update_busy(
        self,
        progress: int,
        message: str,
        stage: str,
        *,
        indeterminate: bool | None = None,
    ) -> None:
        self._invoke_set_busy_state(True, self.busy_title, message, progress, stage, indeterminate)

    def _finish_busy(self) -> None:
        self._invoke_set_busy_state(False, "", "", 0, "idle", False)

    def _clear_solution(self) -> None:
        self.current_solution = None
        self.node_rows = []
        self.element_rows = []
        self.summary = None
        self.result_query_x = 0.0
        self.result_query_y = 0.0
        self.result_query_text = ""
        self.node_rows_json = "[]"
        self.element_rows_json = "[]"
        self.deformation_preview_json = "{}"
        self.deformation_plot_json = "{}"
        self.displacement_contour_json = "{}"
        self.stress_contour_json = "{}"
        self.stress_contour_exact_json = "{}"
        self.stress_contour_smooth_json = "{}"
        self.contour_cache_valid = False
        self.contour_cache_summary_text = ""
        self.clear_contour_image_cache()

    def _store_solution_rows(self, progress_callback=None) -> None:
        if self.current_solution is None:
            self.deformation_preview_json = "{}"
            self.deformation_plot_json = "{}"
            self.displacement_contour_json = "{}"
            self.stress_contour_json = "{}"
            self.stress_contour_exact_json = "{}"
            self.stress_contour_smooth_json = "{}"
            self.contour_cache_valid = False
            self.contour_cache_summary_text = ""
            return
        cache_payload = self._build_solution_cache_payload(
            self.current_solution,
            self.node_rows,
            self.element_rows,
            progress_callback,
        )
        self.node_rows_json = str(cache_payload["node_rows_json"])
        self.element_rows_json = str(cache_payload["element_rows_json"])
        self.deformation_preview_json = str(cache_payload["deformation_preview_json"])
        self.deformation_plot_json = self.deformation_preview_json
        self.displacement_contour_json = str(cache_payload["displacement_contour_json"])
        self.stress_contour_json = str(cache_payload["stress_contour_json"])
        self.stress_contour_exact_json = str(cache_payload["stress_contour_exact_json"])
        self.stress_contour_smooth_json = str(cache_payload["stress_contour_smooth_json"])
        self.contour_cache_valid = True
        self.contour_cache_summary_text = "云图数据缓存有效"
        self._generate_contour_image_cache(progress_callback=progress_callback)

    def _generate_contour_image_cache(self, progress_callback=None) -> None:
        if self.current_solution is None or not self.contour_cache_valid:
            self.clear_contour_image_cache()
            return
        cache_payload = self._build_solution_cache_payload(
            self.current_solution,
            self.node_rows,
            self.element_rows,
            None,
        )
        cache_dir = create_contour_cache_dir(self._session_cache_id)
        clear_contour_cache_dir(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        if progress_callback is not None:
            progress_callback(92, "预渲染变形示意图图片", "contour_image_deformation")
        try:
            if progress_callback is not None:
                progress_callback(95, "预渲染位移云图图片组合", "contour_image_displacement")
            if progress_callback is not None:
                progress_callback(98, "预渲染应力云图图片组合", "contour_image_stress")
            image_map = generate_contour_images(
                output_dir=cache_dir,
                deformation_data=cache_payload["deformation_data"],  # type: ignore[arg-type]
                displacement_data=cache_payload["displacement_data"],  # type: ignore[arg-type]
                stress_exact_data=cache_payload["stress_exact_data"],  # type: ignore[arg-type]
                stress_smooth_data=cache_payload["stress_smooth_data"],  # type: ignore[arg-type]
            )
        except Exception:
            self.clear_contour_image_cache()
            return
        self.contour_image_cache_dir = str(cache_dir)
        self.contour_image_cache_json = build_contour_image_cache_json(image_map)
        self.contour_image_cache_valid = True

    def clear_contour_image_cache(self) -> None:
        clear_contour_cache_dir(self.contour_image_cache_dir)
        self.contour_image_cache_valid = False
        self.contour_image_cache_dir = ""
        self.contour_image_cache_json = "{}"

    @Slot(str)
    def invalidate_solution_and_contour_cache(self, reason: str = "模型已修改，请重新求解", clear_status: bool = True) -> None:
        self._clear_solution()
        if clear_status and reason:
            self._set_status_text(reason)
        self.resultChanged.emit()

    @Slot()
    def shutdown(self) -> None:
        self._cleanup_worker()
        self.clear_contour_image_cache()

    def _reset_sketch_boundary_load_state(self, reset_load_values: bool = False) -> None:
        self.selected_sketch_point_id = ""
        self.selected_sketch_edge_id = ""
        self.selected_sketch_face_id = ""
        self.selected_geometry_type = ""
        self.selected_geometry_id = ""
        self.sketch_fixed_edge_id = ""
        self.sketch_load_edge_id = ""
        if reset_load_values:
            self.sketch_load_qx = 0.0
            self.sketch_load_qy = -1000.0
        self._clear_edge_load_segment_range(emit_signal=False)
        self.edge_load_segment_selection_mode = False
        self.edge_load_segment_edge_id = ""
        self.edge_load_segment_first_t = -1.0
        self.geometry_target_type = ""
        self.geometry_target_id = ""
        self.partEditChanged.emit()

    def _sync_parts_from_project(self) -> None:
        if self.current_project is None:
            self.active_part_id = ""
            self.active_part_name = ""
            self.part_count = 0
            self.part_options = []
            self.partsChanged.emit()
            return

        part_rows = list_parts(self.current_project)
        active_part = next((part for part in part_rows if part["is_active"]), None)
        self.active_part_id = str(active_part["id"]) if active_part is not None else ""
        self.active_part_name = str(active_part["name"]) if active_part is not None else ""
        self.part_count = len(part_rows)
        self.part_options = [
            f"{part['id']} | {part['name']}"
            for part in part_rows
        ]
        self.partsChanged.emit()

    def _sync_instances_from_project(self) -> None:
        if self.current_project is None:
            self.active_instance_id = ""
            self.active_instance_name = ""
            self.active_instance_part_id = ""
            self.active_instance_tx = 0.0
            self.active_instance_ty = 0.0
            self.instance_count = 0
            self.instance_options = []
            self.instancesChanged.emit()
            return

        ensure_default_instance(self.current_project)
        instance_rows = list_instances(self.current_project)
        active_instance = next((row for row in instance_rows if row["is_active"]), None)
        self.active_instance_id = str(active_instance["id"]) if active_instance is not None else ""
        self.active_instance_name = str(active_instance["name"]) if active_instance is not None else ""
        self.active_instance_part_id = str(active_instance["part_id"]) if active_instance is not None else ""
        self.active_instance_tx = float(active_instance["tx"]) if active_instance is not None else 0.0
        self.active_instance_ty = float(active_instance["ty"]) if active_instance is not None else 0.0
        self.instance_count = len(instance_rows)
        self.instance_options = [
            f"{row['id']} | {row['name']} | {row['part_id']}"
            for row in instance_rows
        ]
        if self.active_instance_part_id:
            self.current_project.metadata["active_part_id"] = self.active_instance_part_id
        self.instancesChanged.emit()

    def _sync_parameter_cache_from_project(self) -> None:
        if self.current_project is None:
            return

        if not self.active_part_id:
            self.active_part_id = get_active_part_id(self.current_project)
        try:
            params = extract_workbench_project_parameters(
                self.current_project,
                self.active_part_id,
            )
        except ValueError:
            self.projectParametersChanged.emit()
            return
        self.project_width = params.width
        self.project_height = params.height
        self.project_young_modulus = params.young_modulus
        self.project_poisson_ratio = params.poisson_ratio
        self.project_thickness = params.thickness
        self.project_edge_qy = params.qy
        self.project_mesh_nx = params.mesh_nx
        self.project_mesh_ny = params.mesh_ny
        self.projectParametersChanged.emit()

    def _sync_sketch_from_active_part(self) -> None:
        if self.current_project is None or not self.active_part_id:
            self.sketch_point_count = 0
            self.sketch_edge_count = 0
            self.sketch_face_count = 0
            self.sketch_points_preview = ""
            self.sketch_edges_preview = ""
            self.sketch_can_build_face = False
            self.sketch_has_face = False
            self.geometry_diagnostics_text = ""
            self.selected_sketch_point_id = ""
            self.selected_sketch_edge_id = ""
            self.sketch_fixed_edge_id = ""
            self.sketch_load_edge_id = ""
            self.sketch_points_json = "[]"
            self.sketch_edges_json = "[]"
            self.sketch_faces_json = "[]"
            self.selected_sketch_face_id = ""
            self.selected_geometry_type = ""
            self.selected_geometry_id = ""
            self.sketchChanged.emit()
            return

        part = self.current_project.get_part_by_id(self.active_part_id)
        if part is None:
            self.sketch_point_count = 0
            self.sketch_edge_count = 0
            self.sketch_face_count = 0
            self.sketch_points_preview = ""
            self.sketch_edges_preview = ""
            self.sketch_can_build_face = False
            self.sketch_has_face = False
            self.geometry_diagnostics_text = ""
            self.selected_sketch_point_id = ""
            self.selected_sketch_edge_id = ""
            self.sketch_fixed_edge_id = ""
            self.sketch_load_edge_id = ""
            self.sketch_points_json = "[]"
            self.sketch_edges_json = "[]"
            self.sketch_faces_json = "[]"
            self.selected_sketch_face_id = ""
            self.selected_geometry_type = ""
            self.selected_geometry_id = ""
            self.sketchChanged.emit()
            return

        points = get_sketch_points(part.geometry)
        edges = get_sketch_edges(part.geometry)
        faces = get_sketch_faces(part.geometry)
        self.sketch_point_count = len(points)
        self.sketch_edge_count = len(edges)
        self.sketch_face_count = len(faces)
        self.sketch_can_build_face = can_build_closed_faces(part.geometry)
        self.sketch_has_face = self.sketch_face_count > 0
        self.geometry_diagnostics_text = build_geometry_diagnostics_text(part.geometry)
        point_ids = {point["id"] for point in points}
        edge_ids = {edge["id"] for edge in edges}
        face_ids = {face["id"] for face in faces}
        if self.selected_sketch_point_id not in point_ids:
            self.selected_sketch_point_id = ""
        if self.edge_start_point_id not in point_ids:
            self.edge_start_point_id = ""
        if self.selected_sketch_edge_id not in edge_ids:
            self.selected_sketch_edge_id = ""
        if self.selected_sketch_face_id not in face_ids:
            self.selected_sketch_face_id = ""
        if self.sketch_fixed_edge_id not in edge_ids:
            self.sketch_fixed_edge_id = ""
        if self.sketch_load_edge_id not in edge_ids:
            self.sketch_load_edge_id = ""
        if self.edge_load_segment_edge_id and self.edge_load_segment_edge_id not in edge_ids:
            self._clear_edge_load_segment_range(emit_signal=False)
            self.edge_load_segment_selection_mode = False
            self.edge_load_segment_edge_id = ""
            self.edge_load_segment_first_t = -1.0
        if self.geometry_target_type == "point" and self.geometry_target_id not in point_ids:
            self.geometry_target_type = ""
            self.geometry_target_id = ""
        if self.geometry_target_type == "edge" and self.geometry_target_id not in edge_ids:
            self.geometry_target_type = ""
            self.geometry_target_id = ""
        if self.selected_geometry_type == "point" and self.selected_geometry_id not in point_ids:
            self.selected_geometry_type = ""
            self.selected_geometry_id = ""
        if self.selected_geometry_type == "edge" and self.selected_geometry_id not in edge_ids:
            self.selected_geometry_type = ""
            self.selected_geometry_id = ""
        if self.selected_geometry_type == "face" and self.selected_geometry_id not in face_ids:
            self.selected_geometry_type = ""
            self.selected_geometry_id = ""
        self.sketch_points_preview = "\n".join(
            f"{point['id']}: ({point['x']:.3f}, {point['y']:.3f})"
            for point in points
        )
        self.sketch_edges_preview = "\n".join(
            f"{edge['id']}: {edge['start_point_id']} -> {edge['end_point_id']}"
            for edge in edges
        )
        self.sketch_node_rows_preview = "\n".join(
            f"{point['id']:>4s} | x={point['x']:.4f} | y={point['y']:.4f}"
            for point in points
        )
        self.sketch_edge_rows_preview = "\n".join(
            f"{edge['id']:>4s} | {edge['start_point_id']} -> {edge['end_point_id']}"
            for edge in edges
        )
        self.sketch_points_json = json.dumps(points, ensure_ascii=False)
        self.sketch_edges_json = json.dumps(edges, ensure_ascii=False)
        self.sketch_faces_json = json.dumps(faces, ensure_ascii=False)
        self.sketchChanged.emit()
        self.partEditChanged.emit()

    def _clear_sketch_mesh(self, emit_signal: bool = False) -> None:
        self.current_sketch_mesh = None
        self.has_sketch_mesh = False
        self.sketch_mesh_node_count = 0
        self.sketch_mesh_element_count = 0
        self.sketch_mesh_nodes_json = "[]"
        self.sketch_mesh_elements_json = "[]"
        self.sketch_mesh_status_text = "暂无草图网格"
        self.mesh_quality_summary_text = ""
        self.mesh_min_angle_value = ""
        self.mesh_degenerate_element_count = 0
        self.current_mesh_type = "none"
        if emit_signal:
            self.sketchMeshChanged.emit()

    def _sync_sketch_mesh_from_current_mesh(self) -> None:
        if self.current_sketch_mesh is None:
            self._clear_sketch_mesh(emit_signal=True)
            return

        mesh = self.current_sketch_mesh
        self.has_sketch_mesh = True
        self.sketch_mesh_node_count = len(mesh.nodes)
        self.sketch_mesh_element_count = len(mesh.elements)
        self.sketch_mesh_nodes_json = json.dumps(
            [node.to_dict() for node in mesh.nodes],
            ensure_ascii=False,
        )
        self.sketch_mesh_elements_json = json.dumps(
            [element.to_dict() for element in mesh.elements],
            ensure_ascii=False,
        )
        self.sketch_mesh_status_text = (
            f"节点 {self.sketch_mesh_node_count}，单元 {self.sketch_mesh_element_count}"
        )
        summary = build_mesh_quality_summary(mesh)
        self.mesh_quality_summary_text = (
            f"节点 {summary.node_count}，单元 {summary.element_count}，"
            f"最小面积 {summary.min_area:.6g}，最大面积 {summary.max_area:.6g}，"
            f"平均面积 {summary.avg_area:.6g}，最小角 {summary.min_angle:.3f}°，"
            f"退化单元 {summary.degenerate_element_count}"
        )
        self.mesh_min_angle_value = f"{summary.min_angle:.3f}"
        self.mesh_degenerate_element_count = summary.degenerate_element_count
        self.sketchMeshChanged.emit()

    def _sync_material_state_from_project(self) -> None:
        if self.current_project is None:
            self.material_options = []
            self.material_count = 0
            self.active_part_material_id = ""
            self.active_part_material_name = ""
            self.active_part_material_color = "#8FB7D8"
            self.active_part_thickness = 0.01
            self.material_rows_preview = ""
            self.section_rows_preview = ""
            self.face_material_rows_preview = ""
            self.active_part_face_material_json = "[]"
            self.projectChanged.emit()
            return

        material_rows = list_materials(self.current_project)
        section_rows = list_sections(self.current_project)
        self.material_options = [
            f"{row['id']} | {row['name']}"
            for row in material_rows
        ]
        self.material_count = len(material_rows)
        info = (
            get_part_material_info(self.current_project, self.active_part_id)
            if self.active_part_id
            else {}
        )
        self.active_part_material_id = str(info.get("material_id", ""))
        self.active_part_material_name = str(info.get("material_name", ""))
        self.active_part_material_color = str(info.get("material_color", "#8FB7D8") or "#8FB7D8")
        self.active_part_thickness = float(info.get("thickness", 0.01) or 0.01)
        self.material_rows_preview = "\n".join(
            f"{row['id']} | {row['name']} | E={row['young_modulus']:.6g} Pa | "
            f"nu={row['poisson_ratio']:.4g} | γ={float(row.get('unit_weight', 0.0) or 0.0):.6g} N/m³"
            for row in material_rows
        )
        self.section_rows_preview = "\n".join(
            f"{row['id']} | {row['name']} | {row['material_id']} | t={row['thickness']:.6g}"
            for row in section_rows
        )
        face_rows = []
        if self.active_part_id:
            face_rows = get_part_face_material_rows(self.current_project, self.active_part_id)
        self.face_material_rows_preview = "\n".join(
            f"{row['face_id']} | {row['material_name'] or '未指定'} | "
            f"{row['material_color'] or '-'} | γ={float(row.get('unit_weight', 0.0) or 0.0):.6g} N/m³ | "
            f"t={float(row['thickness']):.6g} | {row['source']}"
            for row in face_rows
        )
        self.active_part_face_material_json = json.dumps(face_rows, ensure_ascii=False)
        self.projectChanged.emit()

    def _sync_boundary_load_state_from_project(self) -> None:
        if self.current_project is None:
            self.boundary_condition_rows_preview = ""
            self.load_rows_preview = ""
            self.boundary_conditions_json = "[]"
            self.loads_json = "[]"
            self.projectChanged.emit()
            return

        self.boundary_condition_rows_preview = "\n".join(
            f"{bc.id} | {bc.target_type}:{bc.target_id} | ux={int(bc.ux_fixed)} uy={int(bc.uy_fixed)}"
            for bc in self.current_project.boundary_conditions
        )
        self.load_rows_preview = "\n".join(
            f"{load.id} | {load.load_type} | {load.target_type}:{load.target_id} | "
            f"start_t={load.start_t:.4f} end_t={load.end_t:.4f} | "
            f"qx={load.qx:.6g} qy={load.qy:.6g}"
            for load in self.current_project.loads
        )
        gravity_row = "gravity_enabled=1 | direction=(0,-1)" if self.gravityEnabled else "gravity_enabled=0"
        self.load_rows_preview = gravity_row if not self.load_rows_preview else gravity_row + "\n" + self.load_rows_preview
        self.boundary_conditions_json = json.dumps(
            [bc.to_dict() for bc in self.current_project.boundary_conditions],
            ensure_ascii=False,
        )
        self.loads_json = json.dumps(
            [load.to_dict() for load in self.current_project.loads],
            ensure_ascii=False,
        )
        self.projectChanged.emit()

    def _default_step_id(self) -> str:
        if self.current_project is None:
            raise ValueError("请先新建或打开工程")
        if self.current_project.get_analysis_step_by_id("step_static") is not None:
            return "step_static"
        if self.current_project.analysis_steps:
            return self.current_project.analysis_steps[0].id
        raise ValueError("当前工程没有可用分析步")

    def _next_definition_id(self, prefix: str, existing_ids: list[str]) -> str:
        used = set(existing_ids)
        index = 1
        while True:
            candidate = f"{prefix}_{index}"
            if candidate not in used:
                return candidate
            index += 1

    def _clear_edge_load_segment_range(self, emit_signal: bool) -> None:
        self.edge_load_start_t = 0.0
        self.edge_load_end_t = 1.0
        self.edge_load_has_custom_range = False
        if emit_signal:
            self.projectChanged.emit()

    def _project_point_to_edge_parameter(self, edge_id: str, x: float, y: float) -> float:
        part = self._require_active_part()
        edge = next((row for row in part.geometry.edges if row.id == edge_id), None)
        if edge is None:
            raise ValueError(f"Unknown geometry edge id: {edge_id}")
        point_by_id = {point.id: point for point in part.geometry.points}
        start = point_by_id.get(edge.start_point_id)
        end = point_by_id.get(edge.end_point_id)
        if start is None or end is None:
            raise ValueError(f"Geometry edge {edge_id!r} references unknown points")
        dx = float(end.x) - float(start.x)
        dy = float(end.y) - float(start.y)
        length_squared = dx * dx + dy * dy
        if length_squared <= 1.0e-12:
            raise ValueError("Geometry edge length is too short")
        raw_t = ((float(x) - float(start.x)) * dx + (float(y) - float(start.y)) * dy) / length_squared
        clamped_t = max(0.0, min(1.0, raw_t))
        projected_x = float(start.x) + dx * clamped_t
        projected_y = float(start.y) + dy * clamped_t
        distance = ((float(x) - projected_x) ** 2 + (float(y) - projected_y) ** 2) ** 0.5
        edge_length = length_squared**0.5
        tolerance = max(1.0e-6, edge_length * 1.0e-3)
        if distance > tolerance:
            raise ValueError("点不在当前边附近")
        return clamped_t

    def _set_status_text(self, text: str) -> None:
        if self._status_text == text:
            return
        self._status_text = text
        self.statusTextChanged.emit()
