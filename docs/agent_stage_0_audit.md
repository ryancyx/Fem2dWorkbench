# Fem2dWorkbench Agent 1.0 — Stage 0 仓库审计与 API 映射

审计日期：2026-09-24

本文档只记录 Agent 1.0 的仓库审计结果，不改变任何现有业务逻辑。后续实现必须继续遵守：不修改 `core/fem/`、`core/solver/` 和既有稳定服务；优先复用当前工程层与服务层；Agent workflow 不暴露 Compile Agent/Tool。

## 1. 仓库关键结构

```text
core/
├─ engineering/                 # EngineeringProject 及工程数据模型（工程真源）
├─ meshing/                     # 矩形网格器、草图网格器、Gmsh CST 网格器
├─ compiler/                    # EngineeringProject + MeshModel -> FEMModel（既有内部链路）
├─ solver/                      # 已验证求解器数学与统一求解入口（禁止修改）
└─ fem/                         # FEM 数据模型（禁止修改）

services/
├─ project_factory_service.py   # 空工程、矩形板工程构造
├─ part_edit_service.py         # 零件与矩形几何创建
├─ sketch_geometry_service.py   # 点/边/闭合面与多边形草图创建
├─ material_manager_service.py  # 材料 CRUD、Section、整零件赋材质
├─ face_material_service.py     # 面/整零件材质赋值
├─ mesh_service.py              # 旧矩形网格服务
├─ compile_service.py           # 既有内部编译步骤
├─ solve_service.py             # 矩形工程的一体化网格+编译+求解入口
├─ result_service.py            # 位移、应变、应力、Von Mises 结果整理
└─ result_query_service.py      # 坐标结果查询

ui/
├─ backend/workbench_bridge.py  # 当前 UI 工作流及通用草图 Gmsh/求解编排
└─ qml/
   ├─ MainWorkbench.qml         # 当前实际结果展示、云图对话框与结果查询入口
   └─ pages/ResultPage.qml      # 结果摘要/节点/单元展示组件

tests/
├─ unit/                        # 工程、服务、网格、结果及 UI 回归测试
└─ integration/                 # 完整建模、Gmsh、求解、结果工作流测试
```

仓库中不存在 `agent/`、`agents/` 或 `ai/` 包。

## 2. 工程真源

工程真源是 `core.engineering.engineering_project.EngineeringProject`，定义于 `core/engineering/engineering_project.py:18`。

它直接持有：

- `materials: list[MaterialDefinition]`
- `sections: list[SectionDefinition]`
- `parts: list[Part]`
- `assembly: Assembly`
- `analysis_steps: list[AnalysisStep]`
- `loads: list[LoadDefinition]`
- `boundary_conditions: list[BoundaryConditionDefinition]`
- `metadata: dict[str, Any]`

已有写入口包括 `add_material()`、`add_section()`、`add_part()`、`add_analysis_step()`、`add_load()`、`add_boundary_condition()`；`validate_references()` 会校验材料、Section、零件、分析步以及点/边目标引用。工程对象支持 `to_dict()` / `from_dict()`。

最小工程的正式构造入口为 `services.project_factory_service.create_empty_workbench_project()`；它会创建默认钢材、默认 Section、静力分析步和必要 metadata。Stage 0 已验证该对象可构造、引用校验并序列化。

## 3. UML 职责到真实 API 映射

| Agent 设计职责 / UML 名称 | 仓库真实类或模块 | 真实方法 / 数据入口 | 文件 |
|---|---|---|---|
| `EngineeringProject` | `EngineeringProject` | `add_*()`、`get_*_by_id()`、`validate_references()`、`to_dict()` / `from_dict()` | `core/engineering/engineering_project.py` |
| 创建最小工程 | `project_factory_service` | `create_empty_workbench_project()` | `services/project_factory_service.py:17` |
| Geometry：矩形模型 | `GeometryModel` | `GeometryModel.create_rectangle(width, height, origin_x, origin_y)` | `core/engineering/geometry.py:120` |
| Geometry：向工程添加矩形零件 | `part_edit_service` | `add_rectangle_part(project, name, width, height, section_id, make_active)` | `services/part_edit_service.py:52` |
| Geometry：通用点/边/闭合面 | `sketch_geometry_service` | `add_sketch_point()`、`add_sketch_edge()`、`build_single_face_from_edges()` / `build_faces_from_edges()` | `services/sketch_geometry_service.py` |
| Geometry：由离散边界点生成闭合面 | `sketch_geometry_service` | `create_geometry_from_polygon_points(points)` | `services/sketch_geometry_service.py:279` |
| Geometry：圆形模型 | 无原生圆/圆弧类或创建方法 | 当前只能由圆周采样点调用 `create_geometry_from_polygon_points()` 形成离散多边形近似；需审核确认 | 无原生入口 |
| Material：创建材料 | `material_manager_service` | `add_material(project, name, young_modulus, poisson_ratio, color, unit_weight)` | `services/material_manager_service.py:43` |
| Material：删除材料 | `material_manager_service` | `delete_material(project, material_id)` | `services/material_manager_service.py:86` |
| Material：创建/复用 Section | `material_manager_service` | `add_or_update_section(project, name, material_id, thickness, plane_mode)` | `services/material_manager_service.py:97` |
| Material：整模型/整零件赋材质 | `material_manager_service` → `face_material_service` | `assign_material_to_part(project, part_id, material_id, thickness)`；同时更新零件及全部面 Section | `services/material_manager_service.py:131`、`services/face_material_service.py:32` |
| Material：单面赋材质（1.0 不主动使用） | `face_material_service` | `assign_material_to_face(...)` | `services/face_material_service.py:8` |
| BC：点/边位移约束数据 | `BoundaryConditionDefinition` | `target_type` 为 `geometry_point` / `geometry_edge`，`ux_fixed` / `uy_fixed` 和 `ux_value` / `uy_value` | `core/engineering/boundary_condition_definition.py:8` |
| BC：写入工程 | `EngineeringProject` | `add_boundary_condition()` + `validate_references()` | `core/engineering/engineering_project.py:72` |
| BC：当前 UI 添加流程 | `WorkbenchBridge` | `addFixedConstraintToSelectedTarget()` / `addConstraintToSelectedTarget()` | `ui/backend/workbench_bridge.py:1790` |
| Load：点集中载荷、边均布载荷数据 | `LoadDefinition` | `load_type` 为 `nodal_concentrated` / `edge_uniform`，二维分量存为 `qx` / `qy` | `core/engineering/load_definition.py:8` |
| Load：写入工程 | `EngineeringProject` | `add_load()` + `validate_references()` | `core/engineering/engineering_project.py:69` |
| Load：当前 UI 添加流程 | `WorkbenchBridge` | `addLoadToSelectedTarget(load_type, fx_or_qx, fy_or_qy)` | `ui/backend/workbench_bridge.py:1862` |
| MeshService：矩形专用 | `mesh_service` | `generate_mesh_for_part(project, part_id, nx, ny)`，内部调用矩形三角网格器 | `services/mesh_service.py:8` |
| MeshService：通用闭合草图/Gmsh | `quality_sketch_mesher` | `generate_quality_sketch_tri_mesh(geometry, target_size, max_area, min_angle)` | `core/meshing/quality_sketch_mesher.py:20` |
| Gmsh 真实封装 | `gmsh_cst_mesher` | `generate_gmsh_cst_mesh(...)` | `core/meshing/gmsh_cst_mesher.py:31` |
| Compile（仅既有内部步骤，不暴露为 Agent 节点） | `compile_service` | `compile_workbench_project(project, mesh, step_id)` | `services/compile_service.py:9` |
| SolveService：矩形一体化流程 | `solve_service` | `solve_workbench_project(project, part_id, step_id, nx, ny)` | `services/solve_service.py:23` |
| SolveService：通用草图实际调用链 | `WorkbenchBridge` + 既有 Compile/Solver API | `compile_workbench_project(...)` → `solve_static_linear(...)`；同步入口为 `solveCurrentModel()`，后台任务入口为 `_build_solve_payload()` | `ui/backend/workbench_bridge.py:2035`、`:3119` |
| SolveResult | `WorkbenchSolveResult` + `SolverResult` | 工程、网格、编译包、求解结果、warnings；数值求解异常直接抛出，由上层捕获为失败信息 | `services/solve_service.py:15`、`core/solver/solver.py:26` |
| Solver 统一入口 | `solver_api` | `solve_static_linear(fem_model)` | `core/solver/solver_api.py:8` |
| Result：节点位移 | `result_service` | `build_node_displacement_rows()`、`build_displacement_contour_data()` | `services/result_service.py:80`、`:198` |
| Result：应变/应力/Von Mises | `result_service` | `build_element_result_rows()`、`build_stress_contour_data()`、`build_result_summary()` | `services/result_service.py:106`、`:235`、`:146` |
| Result：坐标查询 | `result_query_service` | `query_result_at_point()` | `services/result_query_service.py:27` |
| ResultPage / 现有结果 UI | `MainWorkbench.qml` 与 `pages/ResultPage.qml` | 实际主界面含 deformation / displacement contour / stress contour 对话框和结果查询；`ResultPage.qml` 提供摘要、节点、单元页面 | `ui/qml/MainWorkbench.qml`、`ui/qml/pages/ResultPage.qml` |

## 4. 后续 Agent 的真实调用路径建议

### 4.1 Geometry Agent

- 矩形：调用 `add_rectangle_part()`；底层复用 `GeometryModel.create_rectangle()`。
- 圆形：仓库没有原生曲线拓扑。若审核接受“离散圆”，Agent 根据中心、半径和明确的离散段数生成圆周坐标，再调用 `create_geometry_from_polygon_points()`，并把得到的 `GeometryModel` 放入通过既有 `Part` / `EngineeringProject.add_part()` 创建的零件中。
- 不新增 `GeometryTools` 包装层。

### 4.2 Material Agent

- 依次使用 `add_material()` 和 `assign_material_to_part()`。
- Workbench 求解需要 `SectionDefinition` 的 `thickness` 与 `plane_mode`；`assign_material_to_part()` 已通过 `add_or_update_section()` 处理这些字段。
- 删除材料继续使用 `delete_material()`；被 Section 引用时现有服务会明确拒绝。

### 4.3 BC/Load Agent

- 语义 selector 必须在当前 `Part.geometry.points/edges` 上确定性解析为真实字符串 ID。
- 解析完成后构造现有 `BoundaryConditionDefinition` / `LoadDefinition`，通过 `EngineeringProject.add_boundary_condition()` / `add_load()` 写入，并调用 `validate_references()`。
- 不调用 `WorkbenchBridge` 的选择态 API，因为 backend workflow 必须脱离 QML 测试；也不复制其 UI 状态、信号和消息逻辑。
- 后续可在新增 `agent/bc_load_agent.py` 内保留最小的 ID 生成与工程写入适配，不改现有 Bridge。

### 4.4 Mesh / Solve / Result

- 矩形可复用 `solve_workbench_project()` 的既有完整链路。
- 通用草图（包括离散圆）先调用 `generate_quality_sketch_tri_mesh()` 获取 Gmsh `MeshModel`，再复用 `compile_workbench_project()` 和 `solve_static_linear()`；Compile 保持内部实现细节，不成为 workflow 节点。
- 结果继续交给 `result_service` 生成现有结果行、摘要和云图数据；Stage 5 才做最小 UI 触发。

## 5. 设计文档与真实仓库的冲突 / 不确定项

1. **没有原生圆形几何。** `GeometryModel` 只有直线 `GeometryEdge`，没有圆弧/曲线实体；“圆形”只能离散为闭合多边形，除非修改现有几何核心。为遵守只附加与不重写现有能力，建议 Agent 1.0 明确定义为可配置段数的离散圆（建议固定默认段数并写入测试）。此项需要审核确认。
2. **矩形与通用草图使用两条网格/求解路径。** `services.mesh_service.generate_mesh_for_part()` 和 `services.solve_service.solve_workbench_project()` 使用矩形 `nx/ny` 网格；当前 QML 工作流对一般闭合面使用 `generate_quality_sketch_tri_mesh()`（Gmsh），然后直接调用 compile service 与 solver API。Agent Orchestrator 需要复用这两条真实路径，或统一使用通用 Gmsh 路径，但不得新增 Mesh/Solver Agent。
3. **BC/Load 缺少独立服务函数。** 数据模型和工程写入口已存在，添加逻辑目前主要写在 `WorkbenchBridge` 内。Agent backend 不应依赖 UI selection state；应在新增 Agent 文件内用既有数据类和 `EngineeringProject.add_*()` 做最小适配。是否另建通用服务会违反“只做附加且避免无意义包装”的约束，因此 Stage 2 默认不新增 BC/Load service。
4. **位移约束表示存在语义转换。** PrePrompt 的 `ux=None` / `uy=None` 对应仓库的 `ux_fixed=False` / `uy_fixed=False`；非 `None` 值对应 `*_fixed=True` 和 `*_value=float(value)`。
5. **点载荷字段沿用 `qx/qy`。** 仓库 `LoadDefinition` 对点集中力和边均布载荷共用 `qx/qy` 字段；Agent 对外仍使用 `(Fx, Fy)`，写入时确定性映射到 `qx/qy`。
6. **材料赋值需要额外物理参数。** PrePrompt 只显式给出 `E`、`nu`，但仓库 Section 必填 `thickness`、`plane_mode`。`SimulationPlan.material` 在 Stage 1 需要包含或提供明确默认的 `thickness` 和 `plane_mode`；不能静默猜单位。建议默认沿用工程当前 Section（空工程默认为 `0.01`、`stress`），若计划明确给值则覆盖。此项需要审核确认。
7. **求解失败没有统一失败结果对象。** `solve_static_linear()` / Gmsh / compile 失败时抛异常；UI Bridge 捕获异常并写入字符串状态。`WorkflowOrchestrator` 后续需把异常类型与消息转换成 Agent 层的执行结果摘要，不能改 solver 数学或要求 solver 返回新类型。
8. **实际结果入口不只 `ResultPage.qml`。** 当前主界面的云图和查询逻辑直接位于 `MainWorkbench.qml`；独立 `pages/ResultPage.qml` 是结果摘要组件，但未发现它在主 QML 中被实例化。Stage 5 应接现有主界面结果状态，而不是重做结果页。
9. **依赖中没有 Pydantic、LangGraph 或 LLM SDK。** Stage 1 默认采用标准库 `dataclass` + 显式校验；LLM provider SDK 是否新增必须等到 Stage 5，配置来自环境变量/本地私有配置。
10. **现有完整测试基线并非全绿。** 失败项均存在于本次任何改动之前，见第 7 节。由于用户要求不修改既有内容，Stage 0 不修复这些旧 QML/打包目录测试问题。

## 6. 计划新增目录与文件

审核通过后，严格按阶段逐步新增，不一次性创建空壳：

```text
agent/
├─ __init__.py
├─ llm_client.py               # Stage 1
├─ simulation_plan.py          # Stage 1
├─ workflow_state.py           # Stage 1
├─ review_models.py            # Stage 1
├─ geometry_agent.py           # Stage 2
├─ material_agent.py           # Stage 2
├─ bc_load_agent.py            # Stage 2
├─ architect_agent.py          # Stage 3
├─ workflow_orchestrator.py    # Stage 3
└─ reviewer_agent.py           # Stage 4

tests/agent/
├─ test_simulation_plan.py
├─ test_workflow_state.py
├─ test_llm_client.py
├─ test_geometry_agent.py
├─ test_material_agent.py
├─ test_bc_load_agent.py
├─ test_architect_agent.py
├─ test_workflow_orchestrator.py
├─ test_reviewer_agent.py
└─ test_human_approval.py

tests/integration/
├─ test_agent_normal_case.py
└─ test_agent_repair_loop.py
```

Stage 5 的最小 UI 文件尚不提前定名；应在 Stage 3/4 审核通过后，根据当前 `MainWorkbench.qml` 和 `WorkbenchBridge` 的真实状态接口确定。现阶段不计划修改任何 `core/fem/`、`core/solver/` 或现有 service 文件。

## 7. Stage 0 验证与基线测试

### 7.1 使用的项目解释器

所有命令均通过仓库脚本运行，底层解释器为：

```text
D:\PersonalSoftwares\JetBrains\Pycharm\Anaconda\envs\fem2dworkbench\python.exe
```

### 7.2 最小 EngineeringProject 验证

命令：

```powershell
.\scripts\codex_py.ps1 -c "from services.project_factory_service import create_empty_workbench_project; p=create_empty_workbench_project('agent_stage0_probe'); p.validate_references(); d=p.to_dict(); print(type(p).__name__, p.name, len(p.materials), len(p.sections), len(p.analysis_steps), sorted(d.keys()))"
```

结果：通过。

```text
EngineeringProject agent_stage0_probe 1 1 1 ['analysis_steps', 'assembly', 'boundary_conditions', 'loads', 'materials', 'metadata', 'name', 'parts', 'sections']
```

### 7.3 PySide6 导入验证

命令：

```powershell
.\scripts\codex_py.ps1 -c "from PySide6.QtCore import QUrl; print('QtCore OK')"
```

结果：`QtCore OK`。

### 7.4 完整基线测试

命令：

```powershell
.\scripts\codex_pytest.ps1 tests -q
```

结果：`81 passed, 7 failed, 17 warnings in 28.18s`。

失败清单：

1. `tests/integration/test_stage18_qml_busy_overlay_regression.py::test_stage18_qml_busy_overlay_regression`
2. `tests/integration/test_stage18_qml_contour_regression.py::test_stage18_qml_contour_regression`
3. `tests/integration/test_stage18_qml_fake_progress_animation.py::test_stage18_qml_fake_progress_animation`
4. `tests/integration/test_stage18_qml_left_panel_stability_regression.py::test_stage18_qml_left_panel_stability_regression`
5. `tests/integration/test_stage18_qml_professional_contour_regression.py::test_stage18_qml_professional_contour_regression`
6. `tests/integration/test_stage18_result_contour_dialog_data.py::test_stage18_result_contour_dialog_data_export_and_qml_presence`
7. `tests/unit/test_stage18_gravity_constant.py::test_stage18_no_scattered_legacy_gravity_constants`

前六项是现有 `MainWorkbench.qml` 与旧回归字符串/控件断言不一致；最后一项是测试递归扫描 `dist/` 内第三方与旧打包源码并报告 `9.8/9.81`。本 Stage 未修改任何被测文件，故这些属于现有基线失败，不是 Agent 变更回归。

## 8. Stage 0 审核结论

- Agent 1.0 可以以独立 `agent/` 包附加到现有项目，不迁移或重写既有模块。
- 工程真源、矩形、材料、约束、载荷、Gmsh、求解、结果所需真实入口均已定位。
- 圆形离散语义、Section 默认值策略、一般草图的 Mesh/Solve 调用路径需要在审核门 A 确认。
- 当前完整基线测试可运行，但存在 7 个与 Agent 无关的既有失败；在“只做附加”的限制下未修复。
- 在收到明确的 `Stage 0 审核通过，继续` 前，不进入 Stage 1，不新增 Agent 代码。
