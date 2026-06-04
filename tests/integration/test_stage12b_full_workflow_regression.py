import math
from pathlib import Path

import pytest

from services.assembly_edit_service import (
    add_instance,
    get_active_instance_id,
    list_instances,
    move_instance,
    set_active_instance,
)
from services.export_service import (
    export_element_results_csv,
    export_node_displacements_csv,
    export_result_summary_txt,
)
from services.part_edit_service import (
    add_rectangle_part,
    get_active_part_id,
    list_parts,
)
from services.project_factory_service import create_rectangle_plate_project
from services.project_file_service import (
    load_workbench_project,
    save_workbench_project,
)
from services.project_parameter_service import (
    WorkbenchProjectParameters,
    apply_workbench_project_parameters,
    extract_workbench_project_parameters,
)
from services.result_service import (
    build_element_result_rows,
    build_node_displacement_rows,
    build_result_summary,
)
from services.solve_service import solve_workbench_project
from ui.backend.workbench_bridge import WorkbenchBridge


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_WORKBENCH_QML = PROJECT_ROOT / "ui" / "qml" / "MainWorkbench.qml"


def _read_main_workbench_qml() -> str:
    assert MAIN_WORKBENCH_QML.exists(), (
        "MainWorkbench.qml should exist at "
        f"{MAIN_WORKBENCH_QML}"
    )

    return MAIN_WORKBENCH_QML.read_text(encoding="utf-8")


def _parse_option_id(option_text: str) -> str:
    """
    解析 Bridge 暴露给 QML 的 option 字符串。

    兼容：
    - "part_rectangle | rectangle_plate"
    - "inst_1 | 实例 1 | part_rectangle"
    - "part_rectangle"
    """
    text = str(option_text)
    index = text.find("|")

    if index < 0:
        return text.strip()

    return text[:index].strip()


def _find_instance_option_by_part_id(instance_options, part_id: str) -> str:
    """
    在 bridge.instanceOptions 中查找引用指定 part_id 的实例 option。
    """
    for option in instance_options:
        if part_id in str(option):
            return str(option)

    raise AssertionError(f"Cannot find instance option for part_id={part_id!r}")


def test_stage12b_service_level_part_instance_parameter_solve_workflow(tmp_path):
    """
    阶段 12B 截止服务层完整回归测试。

    覆盖：
    - project_factory_service
    - project_parameter_service
    - part_edit_service
    - assembly_edit_service
    - project_file_service
    - solve_service
    - result_service
    - export_service

    这个测试不经过 QML，不启动窗口。
    """
    project = create_rectangle_plate_project(
        width=2.0,
        height=1.0,
        young_modulus=210e9,
        poisson_ratio=0.3,
        thickness=0.01,
        qy=-1000.0,
        project_name="stage12b_service_regression",
        mesh_nx=4,
        mesh_ny=2,
    )

    project.validate_references()

    default_part_id = get_active_part_id(project)
    project = add_instance(
        project=project,
        part_id=default_part_id,
        name="base_instance",
        tx=0.0,
        ty=0.0,
        make_active=True,
    )
    default_instance_id = get_active_instance_id(project)

    assert default_part_id == "part_rectangle"
    assert default_instance_id != ""

    default_params = extract_workbench_project_parameters(project)

    assert math.isclose(default_params.width, 2.0)
    assert math.isclose(default_params.height, 1.0)
    assert default_params.mesh_nx == 4
    assert default_params.mesh_ny == 2

    project = add_rectangle_part(
        project=project,
        name="large_part",
        width=3.0,
        height=1.5,
        section_id=None,
        make_active=True,
    )

    parts = list_parts(project)

    assert len(parts) == 2

    large_part = next(part for part in parts if part["name"] == "large_part")
    large_part_id = large_part["id"]

    project = add_instance(
        project=project,
        part_id=large_part_id,
        name="large_instance",
        tx=2.0,
        ty=1.0,
        make_active=True,
    )

    instances = list_instances(project)

    assert len(instances) == 2

    active_instance = next(instance for instance in instances if instance["is_active"])

    assert active_instance["name"] == "large_instance"
    assert active_instance["part_id"] == large_part_id
    assert math.isclose(active_instance["tx"], 2.0)
    assert math.isclose(active_instance["ty"], 1.0)
    assert get_active_part_id(project) == large_part_id

    active_params = extract_workbench_project_parameters(project)

    assert math.isclose(active_params.width, 3.0)
    assert math.isclose(active_params.height, 1.5)

    edited_params = WorkbenchProjectParameters(
        width=3.5,
        height=1.6,
        young_modulus=200e9,
        poisson_ratio=0.28,
        thickness=0.02,
        qy=-2000.0,
        mesh_nx=5,
        mesh_ny=3,
    )

    project = apply_workbench_project_parameters(project, edited_params)

    restored_active_params = extract_workbench_project_parameters(project)

    assert math.isclose(restored_active_params.width, 3.5)
    assert math.isclose(restored_active_params.height, 1.6)
    assert math.isclose(restored_active_params.young_modulus, 200e9)
    assert math.isclose(restored_active_params.poisson_ratio, 0.28)
    assert math.isclose(restored_active_params.thickness, 0.02)
    assert math.isclose(restored_active_params.qy, -2000.0)
    assert restored_active_params.mesh_nx == 5
    assert restored_active_params.mesh_ny == 3

    project = move_instance(
        project=project,
        instance_id=get_active_instance_id(project),
        tx=2.5,
        ty=-1.0,
    )

    moved_active_instance = next(
        instance for instance in list_instances(project) if instance["is_active"]
    )

    assert math.isclose(moved_active_instance["tx"], 2.5)
    assert math.isclose(moved_active_instance["ty"], -1.0)

    project_file = tmp_path / "stage12b_service_project.f2dw.json"
    save_workbench_project(project, project_file)

    assert project_file.exists()

    loaded_project = load_workbench_project(project_file)

    loaded_instances = list_instances(loaded_project)
    loaded_active_instance = next(
        instance for instance in loaded_instances if instance["is_active"]
    )

    assert len(loaded_instances) == 2
    assert loaded_active_instance["name"] == "large_instance"
    assert loaded_active_instance["part_id"] == large_part_id
    assert math.isclose(loaded_active_instance["tx"], 2.5)
    assert math.isclose(loaded_active_instance["ty"], -1.0)

    loaded_params = extract_workbench_project_parameters(loaded_project)

    assert math.isclose(loaded_params.width, 3.5)
    assert math.isclose(loaded_params.height, 1.6)
    assert loaded_params.mesh_nx == 5
    assert loaded_params.mesh_ny == 3

    solution = solve_workbench_project(
        project=loaded_project,
        part_id=get_active_part_id(loaded_project),
        step_id="step_static",
        nx=loaded_params.mesh_nx,
        ny=loaded_params.mesh_ny,
    )

    expected_node_count = (5 + 1) * (3 + 1)
    expected_element_count = 2 * 5 * 3

    assert len(solution.mesh.nodes) == expected_node_count
    assert len(solution.mesh.elements) == expected_element_count

    node_rows = build_node_displacement_rows(solution)
    element_rows = build_element_result_rows(solution)
    summary = build_result_summary(solution)

    assert len(node_rows) == expected_node_count
    assert len(element_rows) == expected_element_count
    assert summary.node_count == expected_node_count
    assert summary.element_count == expected_element_count
    assert summary.max_displacement > 0.0
    assert summary.max_von_mises >= 0.0

    export_dir = tmp_path / "service_exports"
    node_csv = export_dir / "node_displacements.csv"
    element_csv = export_dir / "element_results.csv"
    summary_txt = export_dir / "summary.txt"

    export_node_displacements_csv(solution, node_csv)
    export_element_results_csv(solution, element_csv)
    export_result_summary_txt(solution, summary_txt)

    assert node_csv.exists()
    assert element_csv.exists()
    assert summary_txt.exists()

    original_instance_id = next(
        instance["id"]
        for instance in list_instances(loaded_project)
        if instance["part_id"] == "part_rectangle"
    )

    loaded_project = set_active_instance(loaded_project, original_instance_id)

    original_params = extract_workbench_project_parameters(loaded_project)

    assert math.isclose(original_params.width, 2.0)
    assert math.isclose(original_params.height, 1.0)

    original_solution = solve_workbench_project(
        project=loaded_project,
        part_id=get_active_part_id(loaded_project),
        step_id="step_static",
        nx=4,
        ny=2,
    )

    assert len(original_solution.mesh.nodes) == 15
    assert len(original_solution.mesh.elements) == 16


def test_stage12b_workbench_bridge_full_part_instance_workflow(tmp_path):
    """
    阶段 12B 截止 WorkbenchBridge 完整用户流程回归测试。

    覆盖：
    newProject()
        -> addRectanglePart()
        -> moveActiveInstance()
        -> updateCurrentProjectParameters()
        -> saveCurrentProject()
        -> loadProject()
        -> solveCurrentProject()
        -> setActiveInstance()
        -> exportResults()

    这个测试不启动 QML 窗口。
    """
    bridge = WorkbenchBridge()

    assert bridge.hasProject is False
    assert bridge.hasSolution is False

    ok = bridge.newProject()

    assert ok is True
    assert bridge.hasProject is True
    assert bridge.partCount == 0
    assert bridge.instanceCount == 0
    assert bridge.activePartId == ""
    assert bridge.activeInstanceId == ""
    assert bridge.activeInstancePartId == ""

    ok = bridge.updateCurrentProjectParameters(
        2.0,
        1.0,
        210e9,
        0.3,
        0.01,
        -1000.0,
        4,
        2,
    )

    assert ok is True
    assert bridge.partCount == 1
    assert bridge.instanceCount == 0
    assert bridge.activePartId != ""
    assert bridge.activeInstanceId == ""
    assert bridge.activeInstancePartId == ""

    ok = bridge.addInstanceForPart(bridge.activePartId, "base_instance", 0.0, 0.0)

    assert ok is True
    assert bridge.instanceCount == 1
    assert bridge.activeInstancePartId == bridge.activePartId

    original_instance_option = _find_instance_option_by_part_id(
        bridge.instanceOptions,
        "part_rectangle",
    )
    original_instance_id = _parse_option_id(original_instance_option)

    ok = bridge.addRectanglePart("large_part", 3.0, 1.5)

    assert ok is True
    assert bridge.partCount == 2
    assert bridge.instanceCount == 1
    assert bridge.activePartId != "part_rectangle"
    assert bridge.activeInstanceId != ""
    assert bridge.activeInstancePartId == "part_rectangle"
    assert bridge.projectWidth == pytest.approx(3.0)
    assert bridge.projectHeight == pytest.approx(1.5)

    ok = bridge.addInstanceForPart(bridge.activePartId, "large_instance", 0.0, 0.0)

    assert ok is True
    assert bridge.instanceCount == 2
    assert bridge.activeInstancePartId == bridge.activePartId

    ok = bridge.moveActiveInstance(2.0, 1.0)

    assert ok is True
    assert bridge.activeInstanceTx == pytest.approx(2.0)
    assert bridge.activeInstanceTy == pytest.approx(1.0)

    ok = bridge.updateCurrentProjectParameters(
        3.5,
        1.6,
        200e9,
        0.28,
        0.02,
        -2000.0,
        5,
        3,
    )

    assert ok is True
    assert bridge.projectWidth == pytest.approx(3.5)
    assert bridge.projectHeight == pytest.approx(1.6)
    assert bridge.projectYoungModulus == pytest.approx(200e9)
    assert bridge.projectPoissonRatio == pytest.approx(0.28)
    assert bridge.projectThickness == pytest.approx(0.02)
    assert bridge.projectEdgeQy == pytest.approx(-2000.0)
    assert bridge.projectMeshNx == 5
    assert bridge.projectMeshNy == 3

    project_file = tmp_path / "stage12b_bridge_project.f2dw.json"

    ok = bridge.saveCurrentProject(str(project_file))

    assert ok is True
    assert project_file.exists()
    assert bridge.projectDirty is False

    bridge2 = WorkbenchBridge()

    ok = bridge2.loadProject(str(project_file))

    assert ok is True
    assert bridge2.hasProject is True
    assert bridge2.partCount == 2
    assert bridge2.instanceCount == 2
    assert bridge2.activePartId != "part_rectangle"
    assert bridge2.activeInstanceId != ""
    assert bridge2.activeInstancePartId == bridge2.activePartId
    assert bridge2.activeInstanceTx == pytest.approx(2.0)
    assert bridge2.activeInstanceTy == pytest.approx(1.0)
    assert bridge2.projectWidth == pytest.approx(3.5)
    assert bridge2.projectHeight == pytest.approx(1.6)
    assert bridge2.projectMeshNx == 5
    assert bridge2.projectMeshNy == 3

    ok = bridge2.solveCurrentProject(bridge2.projectMeshNx, bridge2.projectMeshNy)

    assert ok is False
    assert bridge2.hasSolution is False
    assert "多实例" in bridge2.statusText or "装配联合求解" in bridge2.statusText

    original_instance_option_after_load = _find_instance_option_by_part_id(
        bridge2.instanceOptions,
        "part_rectangle",
    )
    original_instance_id_after_load = _parse_option_id(original_instance_option_after_load)

    assert original_instance_id_after_load == original_instance_id

    ok = bridge2.setActiveInstance(original_instance_id_after_load)

    assert ok is True
    assert bridge2.activeInstancePartId == "part_rectangle"
    assert bridge2.activePartId == "part_rectangle"
    assert bridge2.projectWidth == pytest.approx(2.0)
    assert bridge2.projectHeight == pytest.approx(1.0)

    ok = bridge2.solveCurrentProject(4, 2)

    assert ok is False
    assert "多实例" in bridge2.statusText or "装配联合求解" in bridge2.statusText

    export_dir = tmp_path / "bridge_exports"

    ok = bridge2.exportResults(str(export_dir))

    assert ok is False


def test_stage12b_workbench_bridge_instance_error_paths():
    """
    阶段 12B 截止错误路径测试。

    覆盖：
    - 没有工程时不能设置活动实例
    - 没有工程时不能新增实例
    - 没有工程时不能移动实例
    - 不能删除最后一个实例
    - 不能设置不存在的实例为活动实例
    """
    bridge = WorkbenchBridge()

    ok = bridge.setActiveInstance("inst_missing")
    assert ok is False
    assert "工程" in bridge.statusText or "没有" in bridge.statusText

    ok = bridge.addInstanceForPart("part_rectangle", "bad_instance", 0.0, 0.0)
    assert ok is False
    assert "工程" in bridge.statusText or "没有" in bridge.statusText

    ok = bridge.moveActiveInstance(1.0, 1.0)
    assert ok is False
    assert "工程" in bridge.statusText or "没有" in bridge.statusText

    ok = bridge.newProject()
    assert ok is True
    assert bridge.instanceCount == 0

    ok = bridge.updateCurrentProjectParameters(
        2.0,
        1.0,
        210e9,
        0.3,
        0.01,
        -1000.0,
        4,
        2,
    )
    assert ok is True
    assert bridge.instanceCount == 0

    ok = bridge.deleteActiveInstance()
    assert ok is False
    assert bridge.statusText or (
        "最后" in bridge.statusText
        or "至少" in bridge.statusText
        or "删除" in bridge.statusText
        or "last" in bridge.statusText.lower()
    )

    ok = bridge.setActiveInstance("inst_not_exist")
    assert ok is False
    assert (
        "不存在" in bridge.statusText
        or "失败" in bridge.statusText
        or "not" in bridge.statusText.lower()
    )


def test_stage12b_main_workbench_qml_keeps_project_file_parameter_part_instance_entries():
    """
    阶段 12B QML 静态回归测试：

    检查 MainWorkbench.qml 中阶段 10.6、11、12A、12B 的关键入口没有被删除。
    """
    qml_text = _read_main_workbench_qml()

    required_snippets = [
        # 阶段 10.6：工程文件对话框
        "import QtQuick.Dialogs",
        "openProjectDialog",
        "saveProjectDialog",
        "fileUrlToLocalPath",
        "ensureProjectFileSuffix",
        "打开工程",
        "保存工程",
        "另存为",
        "bridge.loadProject",
        "bridge.saveCurrentProject",
        # 阶段 11：参数同步
        "syncParametersFromBridge",
        "onProjectParametersChanged",
        "updateCurrentProjectParameters",
        "bridge.projectWidth",
        "bridge.projectHeight",
        "bridge.projectMeshNx",
        "bridge.projectMeshNy",
        "参数设置",
        "更新工程",
        "求解",
        # 阶段 12A：Part 编辑
        "bridge.partOptions",
        "bridge.activePartId",
        "bridge.activePartName",
        "bridge.partCount",
        "parsePartIdFromOption",
        "onPartsChanged",
        "setActivePart",
        "addEmptySketchPart",
        "renameActivePart",
        "deleteActivePart",
        "新建二维零件",
        "重命名",
        "删除活动零件",
        "当前活动零件",
        # 阶段 12B：Assembly Instance 编辑
        "bridge.instanceOptions",
        "bridge.activeInstanceId",
        "bridge.activeInstanceName",
        "bridge.activeInstancePartId",
        "bridge.activeInstanceTx",
        "bridge.activeInstanceTy",
        "bridge.instanceCount",
        "parseInstanceIdFromOption",
        "syncInstancesFromBridge",
        "selectAssemblyInstance",
        "onInstancesChanged",
        "setActiveInstance",
        "addInstanceForPart",
        "renameActiveInstance",
        "moveActiveInstance",
        "deleteActiveInstance",
        "新增实例",
        "移动实例",
        "删除活动实例",
        "当前活动实例",
        "装配实例",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text, f"Missing QML stage 12B snippet: {snippet}"


def test_stage12b_main_workbench_qml_keeps_viewport_interaction_and_selection_features():
    """
    阶段 12B 不应破坏阶段 9/10 的视口交互和选择功能。

    这个测试只做静态文本回归，不启动 Qt 窗口。
    """
    qml_text = _read_main_workbench_qml()

    required_snippets = [
        # 视口状态
        "property real viewportScale",
        "property real viewportOffsetX",
        "property real viewportOffsetY",
        "property string viewportTool",
        "property bool showGrid",
        "property bool showMesh",
        "property bool showBoundary",
        "property bool showLoad",
        "property bool showResultOverlay",
        # 视口工具
        "function fitViewport()",
        "function setViewportTool(",
        "function toggleMeshDisplay()",
        "function toggleBoundaryDisplay()",
        "function toggleLoadDisplay()",
        "function toggleResultOverlay()",
        "适应窗口",
        "选择",
        "平移",
        "网格",
        "约束",
        "载荷",
        "结果",
        # 选择状态
        "property string selectedObjectType",
        "property string selectedObjectName",
        "property string selectedObjectDescription",
        "function selectObject(",
        "function clearSelection()",
        "function selectPart()",
        "function selectSection()",
        "function selectAssembly()",
        "function selectBoundary()",
        "function selectLoad()",
        "function selectMesh()",
        "function selectResult()",
        # 实例拖动状态
        "dragInstanceEnabled",
        "isDraggingInstance",
        "dragStartMouseX",
        "dragStartMouseY",
        "dragStartInstanceTx",
        "dragStartInstanceTy",
        # 状态栏
        "工具：",
        "缩放：",
        "选择：",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text, f"Missing viewport/selection snippet: {snippet}"

    assert (
        "WheelHandler" in qml_text
        or "onWheel" in qml_text
        or "wheel.angleDelta" in qml_text
    ), "Viewport should still support mouse wheel zoom"

    assert "MouseArea" in qml_text, "Viewport should still have MouseArea"

    assert (
        "onPressed" in qml_text
        or "onPositionChanged" in qml_text
        or "onReleased" in qml_text
    ), "Viewport should still support mouse click/drag interaction"

    assert (
        "viewportTool === \"平移\"" in qml_text
        or "viewportTool == \"平移\"" in qml_text
    ), "Panning tool logic should still exist"

    assert (
        "viewportTool === \"选择\"" in qml_text
        or "viewportTool == \"选择\"" in qml_text
    ), "Selection tool logic should still exist"


def test_stage12b_main_workbench_qml_documents_current_solver_boundary():
    """
    阶段 12B 的求解边界必须清楚：

    当前只求解活动实例对应的 Part，不做装配级联合求解。
    """
    bridge = WorkbenchBridge()

    ok = bridge.newProject()
    assert ok is True
    assert bridge.updateCurrentProjectParameters(
        2.0,
        1.0,
        210e9,
        0.3,
        0.01,
        -1000.0,
        4,
        2,
    ) is True

    ok = bridge.addRectanglePart("large_part", 3.0, 1.5)
    assert ok is True

    assert bridge.partCount == 2
    assert bridge.instanceCount == 0
    assert bridge.activeInstancePartId == ""

    ok = bridge.solveCurrentProject(5, 3)

    assert ok is True
    assert bridge.nodeCount == 24
    assert bridge.elementCount == 30

    assert "实例" in bridge.statusText or "零件" in bridge.statusText
