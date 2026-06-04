import csv
import math
import re
from pathlib import Path

from services.project_factory_service import create_rectangle_plate_project
from services.project_file_service import (
    load_workbench_project,
    save_workbench_project,
)
from services.solve_service import solve_workbench_project
from services.result_service import (
    build_element_result_rows,
    build_node_displacement_rows,
    build_result_summary,
)
from services.export_service import (
    export_element_results_csv,
    export_node_displacements_csv,
    export_result_summary_txt,
)
from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage10_backend_file_solve_result_export_regression(tmp_path):
    """
    阶段 10 截止后端主链路回归测试。

    覆盖：
    project_factory_service
        -> project_file_service
        -> solve_service
        -> result_service
        -> export_service

    这个测试不启动 QML 窗口。
    """
    project = create_rectangle_plate_project(
        width=2.0,
        height=1.0,
        young_modulus=210e9,
        poisson_ratio=0.3,
        thickness=0.01,
        qy=-1000.0,
        project_name="stage10_full_workflow_demo",
    )

    project.validate_references()

    assert project.name == "stage10_full_workflow_demo"
    assert project.get_material_by_id("mat_steel") is not None
    assert project.get_section_by_id("sec_plate") is not None
    assert project.get_part_by_id("part_rectangle") is not None
    assert project.get_analysis_step_by_id("step_static") is not None
    assert project.get_boundary_condition_by_id("bc_fix_left") is not None
    assert project.get_load_by_id("load_right_down") is not None

    project_file = tmp_path / "stage10_full_workflow_demo.f2dw.json"
    saved_path = save_workbench_project(project, project_file)

    assert saved_path.exists()

    restored_project = load_workbench_project(saved_path)
    restored_project.validate_references()

    assert restored_project.to_dict() == project.to_dict()

    nx = 4
    ny = 2

    solution = solve_workbench_project(
        project=restored_project,
        part_id="part_rectangle",
        step_id="step_static",
        nx=nx,
        ny=ny,
    )

    expected_node_count = (nx + 1) * (ny + 1)
    expected_element_count = 2 * nx * ny

    assert solution.project is restored_project
    assert solution.mesh is not None
    assert solution.compiled_bundle is not None
    assert solution.solver_result is not None

    assert len(solution.mesh.nodes) == expected_node_count
    assert len(solution.mesh.elements) == expected_element_count

    bundle = solution.compiled_bundle

    assert bundle.step_id == "step_static"
    assert len(bundle.mesh_node_to_fem_node_id) == expected_node_count
    assert len(bundle.mesh_element_to_fem_element_id) == expected_element_count
    assert bundle.section_to_solver_material_id["sec_plate"] == 1

    assert set(bundle.geometry_edge_to_fem_node_ids.keys()) == {
        "bottom",
        "right",
        "top",
        "left",
    }

    left_node_ids = bundle.geometry_edge_to_fem_node_ids["left"]
    right_node_ids = bundle.geometry_edge_to_fem_node_ids["right"]

    assert len(left_node_ids) == ny + 1
    assert len(right_node_ids) == ny + 1

    result = solution.solver_result

    assert result.global_stiffness.shape == (
        2 * expected_node_count,
        2 * expected_node_count,
    )
    assert result.global_load.shape == (2 * expected_node_count,)
    assert result.displacement.shape == (2 * expected_node_count,)

    assert len(result.node_displacements) == expected_node_count
    assert len(result.element_results) == expected_element_count

    for node_id in left_node_ids:
        ux, uy = result.node_displacements[node_id]

        assert math.isclose(ux, 0.0, abs_tol=1e-12)
        assert math.isclose(uy, 0.0, abs_tol=1e-12)

    right_displacement_norms = []
    for node_id in right_node_ids:
        ux, uy = result.node_displacements[node_id]
        right_displacement_norms.append(math.hypot(ux, uy))

    assert max(right_displacement_norms) > 0.0

    node_rows = build_node_displacement_rows(solution)
    element_rows = build_element_result_rows(solution)
    summary = build_result_summary(solution)

    assert len(node_rows) == expected_node_count
    assert len(element_rows) == expected_element_count

    assert summary.node_count == expected_node_count
    assert summary.element_count == expected_element_count
    assert summary.max_displacement > 0.0
    assert summary.max_displacement_node_id is not None
    assert summary.max_von_mises >= 0.0
    assert summary.max_von_mises_element_id is not None
    assert summary.warning_count == len(solution.warnings)

    for row in node_rows:
        assert row.node_id > 0
        assert math.isclose(
            row.u_magnitude,
            math.sqrt(row.ux**2 + row.uy**2),
            rel_tol=1e-12,
            abs_tol=1e-12,
        )

    for row in element_rows:
        assert row.element_id > 0
        assert len(row.node_ids) == 3
        assert row.von_mises >= 0.0

    export_dir = tmp_path / "exports"
    node_csv = export_dir / "node_displacements.csv"
    element_csv = export_dir / "element_results.csv"
    summary_txt = export_dir / "summary.txt"

    export_node_displacements_csv(solution, node_csv)
    export_element_results_csv(solution, element_csv)
    export_result_summary_txt(solution, summary_txt)

    assert node_csv.exists()
    assert element_csv.exists()
    assert summary_txt.exists()

    with node_csv.open("r", encoding="utf-8", newline="") as f:
        node_csv_rows = list(csv.DictReader(f))

    with element_csv.open("r", encoding="utf-8", newline="") as f:
        element_csv_rows = list(csv.DictReader(f))

    assert len(node_csv_rows) == expected_node_count
    assert len(element_csv_rows) == expected_element_count

    assert {
        "node_id",
        "x",
        "y",
        "ux",
        "uy",
        "u_magnitude",
    }.issubset(node_csv_rows[0].keys())

    assert {
        "element_id",
        "node_ids",
        "strain_x",
        "strain_y",
        "strain_xy",
        "stress_x",
        "stress_y",
        "stress_xy",
        "von_mises",
    }.issubset(element_csv_rows[0].keys())

    summary_text = summary_txt.read_text(encoding="utf-8")

    assert "node_count" in summary_text
    assert "element_count" in summary_text
    assert "max_displacement" in summary_text
    assert "max_von_mises" in summary_text


def test_stage10_workbench_bridge_full_user_workflow(tmp_path):
    """
    阶段 10 截止 WorkbenchBridge 用户流程回归测试。

    覆盖：
    createDefaultProject()
        -> saveCurrentProject()
        -> loadProject()
        -> solveCurrentProject()
        -> exportResults()

    这个测试不启动 QML 窗口。
    """
    bridge = WorkbenchBridge()

    assert bridge.hasProject is False
    assert bridge.hasSolution is False

    ok = bridge.createDefaultProject(
        2.0,
        1.0,
        210e9,
        0.3,
        0.01,
        -1000.0,
    )

    assert ok is True
    assert bridge.hasProject is True
    assert bridge.projectName != ""
    assert bridge.projectDirty is True
    assert bridge.hasSolution is False

    project_file = tmp_path / "bridge_stage10_project.f2dw.json"

    ok = bridge.saveCurrentProject(str(project_file))

    assert ok is True
    assert project_file.exists()
    assert bridge.projectPath != ""
    assert bridge.projectDirty is False

    bridge2 = WorkbenchBridge()

    ok = bridge2.loadProject(str(project_file))

    assert ok is True
    assert bridge2.hasProject is True
    assert bridge2.projectName != ""
    assert bridge2.projectPath != ""
    assert bridge2.projectDirty is False
    assert bridge2.hasSolution is False

    ok = bridge2.solveCurrentProject(4, 2)

    assert ok is True
    assert bridge2.hasSolution is True
    assert bridge2.nodeCount == 15
    assert bridge2.elementCount == 16
    assert bridge2.nodeRowsPreview != ""
    assert bridge2.elementRowsPreview != ""
    assert bridge2.maxDisplacement != ""
    assert bridge2.maxVonMises != ""

    export_dir = tmp_path / "bridge_stage10_exports"

    ok = bridge2.exportResults(str(export_dir))

    assert ok is True
    assert (export_dir / "node_displacements.csv").exists()
    assert (export_dir / "element_results.csv").exists()
    assert (export_dir / "summary.txt").exists()


def test_stage10_workbench_bridge_error_paths(tmp_path):
    """
    阶段 10 截止错误路径回归测试。

    覆盖：
    - 没有工程时不能保存
    - 没有工程时不能求解
    - 没有结果时不能导出
    - 不存在的工程文件不能打开
    """
    bridge = WorkbenchBridge()

    ok = bridge.saveCurrentProject(str(tmp_path / "should_not_exist.f2dw.json"))
    assert ok is False
    assert "没有" in bridge.statusText or "保存" in bridge.statusText

    ok = bridge.solveCurrentProject(4, 2)
    assert ok is False
    assert (
        "创建" in bridge.statusText
        or "打开" in bridge.statusText
        or "工程" in bridge.statusText
    )

    ok = bridge.exportResults(str(tmp_path / "exports_without_solution"))
    assert ok is False
    assert "结果" in bridge.statusText or "导出" in bridge.statusText

    missing_file = tmp_path / "missing_project.f2dw.json"
    ok = bridge.loadProject(str(missing_file))

    assert ok is False
    assert (
        "错误" in bridge.statusText
        or "失败" in bridge.statusText
        or "不存在" in bridge.statusText
        or "does not exist" in bridge.statusText
        or "No such" in bridge.statusText
    )


def test_stage10_main_workbench_qml_keeps_stage9_viewport_interaction_features():
    """
    阶段 10 不应破坏阶段 9 的视口交互功能。

    这个测试不启动 Qt 窗口，只读取 MainWorkbench.qml 文本。
    """
    qml_path = Path("ui/qml/MainWorkbench.qml")
    assert qml_path.exists(), "MainWorkbench.qml should exist"

    qml_text = qml_path.read_text(encoding="utf-8")

    required_snippets = [
        "property real viewportScale",
        "property real viewportOffsetX",
        "property real viewportOffsetY",
        "property string viewportTool",
        "property bool showGrid",
        "property bool showMesh",
        "property bool showBoundary",
        "property bool showLoad",
        "property bool showResultOverlay",
        "function fitViewport()",
        "function setViewportTool(",
        "function toggleMeshDisplay()",
        "function toggleBoundaryDisplay()",
        "function toggleLoadDisplay()",
        "function toggleResultOverlay()",
        "viewportScale",
        "viewportOffsetX",
        "viewportOffsetY",
        "requestPaint()",
        "适应窗口",
        "选择",
        "平移",
        "网格",
        "约束",
        "载荷",
        "结果",
        "工具：",
        "缩放：",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text, f"Missing stage 9 QML snippet: {snippet}"

    assert (
        "WheelHandler" in qml_text
        or "onWheel" in qml_text
        or "wheel.angleDelta" in qml_text
    ), "Viewport should support mouse wheel zoom"

    assert (
        "MouseArea" in qml_text
        and (
            "onPressed" in qml_text
            or "onPositionChanged" in qml_text
            or "onReleased" in qml_text
        )
    ), "Viewport should support mouse drag or click interaction"

    assert (
        "0.4" in qml_text and "4.0" in qml_text
    ), "Viewport zoom range should include 0.4 to 4.0"

    assert "showBoundary = true" in qml_text
    assert "showLoad = true" in qml_text
    assert "showMesh = true" in qml_text
    assert "showResultOverlay = true" in qml_text


def test_stage10_main_workbench_qml_contains_selection_state_and_functions():
    """
    阶段 10 QML 对象选择功能静态回归测试。

    检查：
    - 选择状态
    - 选择函数
    - 点击命中相关状态
    - 选择对象的中文描述
    """
    qml_path = Path("ui/qml/MainWorkbench.qml")
    assert qml_path.exists(), "MainWorkbench.qml should exist"

    qml_text = qml_path.read_text(encoding="utf-8")

    required_snippets = [
        "property string selectedObjectType",
        "property string selectedObjectName",
        "property string selectedObjectDescription",
        "property real lastPlateX",
        "property real lastPlateY",
        "property real lastPlateW",
        "property real lastPlateH",
        "function selectObject(",
        "function clearSelection()",
        "function selectPart()",
        "function selectSection()",
        "function selectAssembly()",
        "function selectBoundary()",
        "function selectLoad()",
        "function selectMesh()",
        "function selectResult()",
        "selectedObjectType",
        "selectedObjectName",
        "selectedObjectDescription",
        "零件",
        "矩形零件",
        "属性",
        "钢材薄板属性",
        "装配",
        "装配实例",
        "边界条件",
        "左边界固定",
        "载荷",
        "右边界均布载荷",
        "网格",
        "结构化 CST 网格",
        "结果",
        "求解结果",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text, f"Missing stage 10 selection snippet: {snippet}"


def test_stage10_main_workbench_qml_contains_viewport_hit_test_logic():
    """
    阶段 10 视口点击命中逻辑静态回归测试。

    这个测试不验证真实鼠标行为，只保证关键点击判断代码未被删除。
    """
    qml_path = Path("ui/qml/MainWorkbench.qml")
    assert qml_path.exists(), "MainWorkbench.qml should exist"

    qml_text = qml_path.read_text(encoding="utf-8")

    required_snippets = [
        "lastPlateX",
        "lastPlateY",
        "lastPlateW",
        "lastPlateH",
        "mouse.x",
        "mouse.y",
        "selectBoundary()",
        "selectLoad()",
        "selectMesh()",
        "selectPart()",
        "clearSelection()",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text, f"Missing viewport hit-test snippet: {snippet}"

    assert (
        "Math.abs" in qml_text
        or "abs(" in qml_text
    ), "Hit-test should check distance to plate boundary"

    assert (
        "viewportTool === \"选择\"" in qml_text
        or "viewportTool == \"选择\"" in qml_text
    ), "Selection should only happen under select tool"

    assert (
        "viewportTool === \"平移\"" in qml_text
        or "viewportTool == \"平移\"" in qml_text
    ), "Panning tool should still be handled"


def test_stage10_main_workbench_qml_contains_model_tree_selection_linkage():
    """
    阶段 10 模型树联动静态回归测试。

    检查模型树条目是否已经从纯文本变成可点击对象，
    且点击后能调用对应选择函数。
    """
    qml_path = Path("ui/qml/MainWorkbench.qml")
    assert qml_path.exists(), "MainWorkbench.qml should exist"

    qml_text = qml_path.read_text(encoding="utf-8")

    required_snippets = [
        "TreeItem",
        "对象列表",
        "矩形板分析",
        "矩形零件",
        "钢材薄板属性",
        "装配实例",
        "左边界固定",
        "右边界均布载荷",
        "结构化 CST 网格",
        "求解结果",
        "selectPart()",
        "selectSection()",
        "selectAssembly()",
        "selectBoundary()",
        "selectLoad()",
        "selectMesh()",
        "onClicked",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text, f"Missing model tree selection snippet: {snippet}"

    obsolete_prefixes = [
        "工程 / 矩形板分析",
        "零件 / 矩形零件",
        "属性 / 钢材薄板属性",
        "装配 / 单零件实例",
        "约束 / 左边界固定",
        "载荷 / 右边界均布载荷",
        "网格 / 结构化 CST 网格",
    ]

    for snippet in obsolete_prefixes:
        assert snippet not in qml_text, f"Model tree should not repeat module prefix: {snippet}"


def test_main_workbench_uses_left_navigation_as_unique_module_entry():
    """
    当前布局将模块切换收敛到左侧工程导航：
    - 顶部不再使用全局 ModuleTab 模块栏；
    - 菜单不再重复放建模/分析/结果模块入口；
    - 视口工具栏位于中央视口上方。
    """
    qml_path = Path("ui/qml/MainWorkbench.qml")
    assert qml_path.exists(), "MainWorkbench.qml should exist"

    qml_text = qml_path.read_text(encoding="utf-8")

    assert "ModuleTab {" not in qml_text
    assert not re.search(r'Menu\s*\{\s*title:\s*"建模"', qml_text)
    assert not re.search(r'Menu\s*\{\s*title:\s*"分析"', qml_text)
    assert not re.search(r'Menu\s*\{\s*title:\s*"结果"', qml_text)

    for module_name in [
        'title: "工程"',
        'title: "零件"',
        'title: "属性"',
        'title: "装配"',
        'title: "边界"',
        'title: "载荷"',
        'title: "网格"',
        'title: "结果"',
        'title: "导出"',
    ]:
        assert module_name in qml_text, f"Left navigation should keep module entry: {module_name}"

    assert 'title: "求解"' not in qml_text

    toolbar_index = qml_text.index("id: viewportToolBarDock")
    viewport_index = qml_text.index("id: viewportPanel")
    assert toolbar_index < viewport_index


def test_stage10_main_workbench_qml_contains_property_inspector_selection_linkage():
    """
    阶段 10 右侧属性检查器联动静态回归测试。

    检查右侧属性面板是否展示当前选择对象，
    并根据对象类型显示不同参数。
    """
    qml_path = Path("ui/qml/MainWorkbench.qml")
    assert qml_path.exists(), "MainWorkbench.qml should exist"

    qml_text = qml_path.read_text(encoding="utf-8")

    required_snippets = [
        "选择类型",
        "对象名称",
        "对象说明",
        "selectedObjectType",
        "selectedObjectName",
        "selectedObjectDescription",
        "visible:",
        "宽度",
        "高度",
        "弹性模量",
        "泊松比",
        "厚度",
        "当前目标",
        "ux",
        "uy",
        "qy",
        "预计节点",
        "预计单元",
        "最大位移",
        "最大 Von Mises",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text, f"Missing property inspector snippet: {snippet}"

    assert "模块：" in qml_text, "Current module should remain in the bottom status bar"


def test_stage10_main_workbench_qml_keeps_stage8_project_file_ui_entries():
    """
    阶段 10 不应破坏阶段 8 的工程文件 UI 入口。

    检查：
    - 新建工程
    - 保存工程
    - 打开工程
    - 创建/更新工程
    - 导出结果
    - 工程状态显示
    """
    qml_path = Path("ui/qml/MainWorkbench.qml")
    assert qml_path.exists(), "MainWorkbench.qml should exist"

    qml_text = qml_path.read_text(encoding="utf-8")

    required_snippets = [
        "新建工程",
        "保存工程",
        "打开工程",
        "创建/更新工程",
        "导出结果",
        "newProject",
        "saveCurrentProject",
        "loadProject",
        "projectName",
        "projectPath",
        "projectDirty",
    ]

    for snippet in required_snippets:
        assert snippet in qml_text, f"Missing stage 8 project file UI snippet: {snippet}"


def test_stage10_manual_test_is_still_required_for_real_qml_interaction():
    """
    提醒：
    这个测试只是把人工验收要求写进测试说明中，确保后续维护者知道：
    QML 文本静态回归不能替代真实窗口交互验收。

    真正需要人工确认的内容：
    - 鼠标点击零件/边界/载荷/网格是否能正确选中
    - 右侧属性面板是否实时更新
    - 视口高亮是否符合预期
    - 缩放、平移和选择工具是否手感正常
    """
    manual_checks = [
        "点击矩形板应选择零件",
        "点击左边界应选择边界条件",
        "点击右边界应选择载荷",
        "显示网格后点击板内应选择网格",
        "点击空白区域应清空选择",
        "模型树点击对象应同步右侧属性面板",
        "状态栏应显示当前选择对象",
        "缩放和平移仍应正常",
    ]

    assert len(manual_checks) == 8
    assert "点击矩形板应选择零件" in manual_checks
