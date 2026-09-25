# Fem2dWorkbench Agent 1.0 — Stage 3 Workflow 架构审核包

审核日期：2026-09-24

本审核包覆盖 Stage 1（基础数据层与 LLM 抽象）、Stage 2（专业 Agent）和 Stage 3（Architect + 确定性 Workflow）。已到达强制审核门 B；Reviewer、Human Approval、真实 LLM provider 和 UI 均未实现。

## 1. 完整代码清单

以下文件共同构成本阶段完整实现。审核时应将本文件与这些源文件一并提供给外部架构对话；代码没有复制进审核文档，以免审核材料与真实源文件产生版本漂移。

### Stage 1

- `agent/llm_client.py`：provider-agnostic `LLMClient` Protocol 和 `StructuredOutputError`。
- `agent/simulation_plan.py`：`SimulationPlan`、校验、序列化和确定性 `applyRepair()`。
- `agent/workflow_state.py`：`WorkflowStage`、`WorkflowStatus`、`WorkflowState` 及状态序列化。
- `agent/review_models.py`：`ReviewResult`、`RepairProposal`。
- `agent/execution_result.py`：适配真实异常语义的轻量 `ExecutionResult`。

### Stage 2

- `agent/geometry_agent.py`：矩形、固定 64 段离散圆，以及 Agent 管理零件的幂等更新。
- `agent/material_agent.py`：材料创建、删除、整模型赋材质，支持 thickness / plane_mode。
- `agent/bc_load_agent.py`：语义 selector/坐标解析、点/边约束、点/边二维载荷、多 ID 目标及 Agent 自有定义追踪。

### Stage 3

- `agent/architect_agent.py`：Architect prompt、完整 JSON Schema、create/revise structured output。
- `agent/workflow_orchestrator.py`：确定性状态调度、Gmsh/Compile/Solver/Result 路径、异常到 `ExecutionResult` 的转换。
- `agent/__init__.py`：新增层的公开接口。

## 2. 职责边界

### ArchitectAgent

只负责：

```text
Natural Language + Project Context -> structured SimulationPlan
```

以及：

```text
New Natural Language + Current SimulationPlan + Project Context
-> revised SimulationPlan (version + 1)
```

Architect 不执行几何、材料、约束、载荷、网格、编译、求解或结果计算，不控制 workflow stage，不生成内部 entity ID。

### WorkflowOrchestrator

只负责确定性的 stage 跳转、现有工程能力调用和异常封装。它不调用 LLM 决定机械流程，不实现 FEM 数学。

### 专业 Agent

- GeometryAgent、MaterialAgent、BCLoadAgent 都只依赖统一 `LLMClient` 类型，并分别通过自己的窄职责 Prompt/Schema 请求 structured actions。
- 三者执行顺序均为：读取已校验 subplan 与必要工程摘要 → Fake/真实 provider 的统一 `LLMClient.request()` → schema + 显式二次校验 → 确定性调用既有工程 API。
- LLM action 若改变已验证 subplan 数值、带入内部 ID、包含未知字段或缺少必要字段，会在修改工程前以 `StructuredOutputError` 明确失败。
- BCLoadAgent 不调用 `WorkbenchBridge`，不依赖 QML selection state。

### LLMClient

当前只有 Protocol：

```python
class LLMClient(Protocol):
    def request(
        self,
        system_prompt: str,
        user_content: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]: ...
```

Stage 1–4 不包含网络代码、provider SDK、本地模型、训练/微调代码或关键词规则解析。所有测试使用 Fake LLM。OpenAI / DeepSeek provider 适配留到 Stage 5。

### GeometryAgent Prompt / Schema

Prompt：

```text
You are the Geometry specialist for Fem2dWorkbench Agent 1.0.
Read only the structured geometry subplan and the compact project context. Produce one
schema-constrained geometry action: create_rectangle or create_circle. Preserve all
numeric dimensions and coordinates from the subplan. Do not invent entity IDs, perform
meshing, solve FEM equations, or modify materials, constraints, or loads.
```

`GEOMETRY_ACTION_SCHEMA` 输出：

```text
{
  action: create_rectangle | create_circle,
  parameters: {
    width?, height?, originX?, originY?,
    centerX?, centerY?, radius?
  }
}
```

显式校验还要求 action 与 `SimulationPlan.geometry.type` 一致、参数集合与类型匹配、所有值与已验证 subplan 完全一致、尺寸为正。完整常量和校验代码位于 `agent/geometry_agent.py`。

### MaterialAgent Prompt / Schema

Prompt：

```text
You are the Material specialist for Fem2dWorkbench Agent 1.0.
Read only the structured material subplan and compact material/section context. Return a
schema-constrained sequence of create_material, assign_material, or delete_material
actions. Refer to materials by semantic name, never by an invented internal ID. Preserve
E, nu, thickness, and plane_mode from the validated subplan. Do not modify geometry,
boundary conditions, loads, mesh, or solver state.
```

`MATERIAL_ACTION_SCHEMA` 输出一个 `actions` 数组：

```text
create_material(name, E, nu, color?, unit_weight?)
assign_material(name, thickness, plane_mode)
delete_material(name)
```

显式校验拒绝内部 material ID、未知字段、非法物理参数、非预期删除，以及对 subplan 的 name/E/nu/thickness/plane_mode 篡改。material name 由确定性代码解析为真实 ID。完整常量和校验代码位于 `agent/material_agent.py`。

### BCLoadAgent Prompt / Schema

Prompt：

```text
You are the boundary-condition and load specialist for
Fem2dWorkbench Agent 1.0. Convert the validated constraint/load subplan into only the
schema-constrained actions add_point_constraint, add_edge_constraint, add_point_load,
or add_edge_load. Targets must remain semantic selectors or coordinates. Never emit or
invent internal point/edge IDs; deterministic code resolves targets after validation.
Preserve every displacement component and two-dimensional load vector. Do not modify
geometry, materials, mesh, or solver state.
```

`BC_LOAD_ACTION_SCHEMA` 输出一个 `actions` 数组：

```text
add_point_constraint(target, ux, uy)
add_edge_constraint(target, ux, uy)
add_point_load(target, vector[2])
add_edge_load(target, vector[2])
```

`target` 只允许 semantic `selector` 或 `[x, y]` coordinate。显式校验要求 action 列表与已验证 subplan 完全一致；真实 point/edge ID 只由 deterministic resolver 在 LLM 返回之后解析。完整常量和校验代码位于 `agent/bc_load_agent.py`。

### Gate B 第二轮一致性修正

`BCLoadAgent.apply()` 现在严格按以下顺序执行：

```text
LLM request
-> structured-output validation
-> resolve every target to real point/edge IDs
-> precheck every resolved entity and analysis step
-> snapshot current BC/load/metadata
-> clear only Agent-managed definitions
-> write replacement definitions
-> validate_references()
```

因此 LLM 请求失败、structured output 非法、selector/coordinate 无法解析或实体预检查失败时，真实工程尚未发生 mutation。写入阶段若发生异常，会恢复此前的 BC、Load 和 metadata 快照，避免留下部分更新状态。

`MaterialAgent` 不再把同名材料视为满足计划。create/assign 计划只有在工程中已存在 `name + E + nu` 完全匹配的材料时才允许仅返回 `assign_material`；否则 structured actions 必须先包含与 subplan 完全匹配的 `create_material`。执行 `assign_material` 前再次按 `name + E + nu` 查找，确保实际 Section 引用的材料参数与 `SimulationPlan` 一致。

coordinate target 使用几何 bounds 的最大 span 计算有限容差：

```text
tolerance = max(span * 1e-6, 1e-9)
```

point coordinate 只有到最近真实点的欧氏距离不超过 tolerance 才能解析；edge coordinate 使用点到有限线段的距离，并同样要求不超过 tolerance。超出容差返回无匹配目标，随后形成明确执行失败；在 Orchestrator 中该失败被封装为 `ExecutionResult` 并进入 `REVIEW`，不会静默映射到远处实体，也不会创建 BC/Load。

## 3. Architect prompt

当前 system prompt：

```text
You are the Architect Agent for Fem2dWorkbench Agent 1.0.
Convert the user's modeling intent into exactly one schema-constrained SimulationPlan.
Do not solve FEM equations, generate meshes, or control workflow stages.
Never invent internal point, edge, face, material, section, part, or step IDs.
Targets must use semantic selectors or coordinates. Use only rectangle or circle geometry.
Point loads are [Fx, Fy]; edge loads are [qx, qy]. A null displacement component means
that direction is unconstrained. Material thickness and plane_mode are mandatory: use
explicit user values when supplied, otherwise inherit the defaults supplied in project
context. Return data only through the requested structured-output schema.
```

完整 schema 为 `agent/architect_agent.py` 中的 `SIMULATION_PLAN_SCHEMA`。它要求：

- geometry 只能是 rectangle / circle；
- material 必须含 name / E / nu / thickness / plane_mode；
- 约束目标只能是 semantic selector 或 coordinate；
- 点/边载荷都是二分量 vector；
- meshSize 必须为正数；
- requestedResult 只能是 displacement / stress / strain / von_mises；
- schema 和 `SimulationPlan` 二次显式校验共同拒绝非法结构与内部 ID。

## 4. SimulationPlan 当前结构

```text
SimulationPlan
├─ version: int >= 1
├─ geometry: rectangle(width, height, originX, originY)
│             or circle(centerX, centerY, radius)
├─ material: name, E, nu, thickness, plane_mode
│            optional color, unit_weight
├─ pointConstraints: [{target, ux, uy}]
├─ edgeConstraints: [{target, ux, uy}]
├─ pointLoads: [{target, vector: [Fx, Fy]}]
├─ edgeLoads: [{target, vector: [qx, qy]}]
├─ meshSize: positive float
└─ requestedResult: displacement | stress | strain | von_mises
```

`target` 只允许：

```json
{"selector": "left"}
```

或：

```json
{"coordinate": [0.0, 0.0]}
```

`id` / `point_id` / `edge_id` 等内部 ID 在 Plan 校验阶段被拒绝。

`applyRepair()` 返回新对象并执行 `version + 1`；旧 Plan 不被修改。目前支持 add/update point/edge constraint、add/update point/edge load、set mesh size、update material 和 replace geometry。Reviewer 尚未实现。

## 5. Workflow 节点和跳转

当前 Stage 3 主路径：

```text
ARCHITECT
  -> GEOMETRY
  -> MATERIAL
  -> BC_LOAD
  -> MESH
  -> SOLVE
  -> RESULT
  -> COMPLETED
```

异常路径：

```text
ARCHITECT planning / structured-output failure
  -> ExecutionResult(success=false)
  -> ARCHITECT
  -> WAITING_USER_INPUT

GEOMETRY / MATERIAL / BC_LOAD / MESH / SOLVE failure
  -> ExecutionResult(success=false, error_type, error_message)
  -> REVIEW
  -> RUNNING (等待 Stage 4 Reviewer 接管)
```

`executePlan()` 循环执行确定性节点；`executeCurrentStage()` 每次只执行当前节点，支持暂停/恢复所需的显式状态。`WorkflowState` 可序列化工程、Plan、stage/status、ExecutionResult、ReviewResult、当前 Mesh、结果摘要、retry count 和 approval flag。

`WAITING_USER_INPUT` 状态下再次调用 `start()` 会走 `ArchitectAgent.revise_plan()`，而非重新 create plan。Reject 的状态设置和审批入口留到 Stage 4。

## 6. 真实工程调用路径

### Geometry

```text
rectangle
-> services.part_edit_service.add_rectangle_part()
-> core.engineering.geometry.GeometryModel.create_rectangle()

circle
-> 64 fixed circumference points
-> services.part_edit_service.add_sketch_part()
-> services.sketch_geometry_service.create_geometry_from_polygon_points()
```

Agent 创建的零件 ID 写入 `project.metadata["agent_managed_part_id"]`。重跑计划只更新该零件，不删除或替换用户已有零件。

### Material

```text
services.material_manager_service.add_material()
-> add_or_update_section(thickness, plane_mode)
-> assign Section to every current Part / GeometryFace
-> EngineeringProject.validate_references()
```

### BC/Load

```text
semantic target / coordinate
-> deterministic resolve_target() -> list[real point/edge ID]
-> BoundaryConditionDefinition / LoadDefinition
-> EngineeringProject.add_boundary_condition() / add_load()
-> EngineeringProject.validate_references()
```

Agent 自己创建的 BC/load ID 分别记录在 metadata；重跑只替换这些记录中的对象，保留用户已有定义。

替换采用先完整请求、校验和解析，再一次性 mutation 的顺序；任何 mutation 前失败都会完整保留旧的 Agent-managed BC/load。

### Mesh / Compile / Solve / Result

所有 Agent 几何（包括矩形）统一走：

```text
core.meshing.quality_sketch_mesher.generate_quality_sketch_tri_mesh()
-> services.compile_service.compile_workbench_project()
-> core.solver.solver_api.solve_static_linear()
-> services.result_service existing result builders
```

没有调用 `solve_workbench_project()` 或 nx/ny 结构化网格作为 Agent 主路径。Compile 只是 Orchestrator 内部调用步骤，不是 Agent、Tool 或 workflow stage。

求解成功时，既有 `SolverResult` 被保存在 `WorkbenchSolveResult` 内，再由 Agent 层 `ExecutionResult.solve_result` 持有；没有修改 Solver 或 SolverResult。

## 7. 测试清单

新增测试：

```text
tests/agent/
├─ conftest.py
├─ test_architect_agent.py
├─ test_bc_load_agent.py
├─ test_execution_result.py
├─ test_geometry_agent.py
├─ test_llm_client.py
├─ test_material_agent.py
├─ test_review_models.py
├─ test_simulation_plan.py
├─ test_workflow_orchestrator.py
└─ test_workflow_state.py

tests/integration/
└─ test_agent_normal_case.py
```

覆盖内容：

- Plan 合法创建、往返序列化、非法字段和内部 ID 拒绝；
- applyRepair 不修改旧版本并产生 version + 1；
- WorkflowState 状态保存与恢复；
- ExecutionResult 异常封装；
- provider-agnostic LLM Protocol 可由 Fake 实现；
- 矩形和固定 64 段圆写入真实 EngineeringProject；
- 材料创建、删除、全模型 Section/材质赋值；
- 点/边约束和二维点/边载荷写入真实工程；
- outer_boundary selector 解析 64 个圆边 ID；
- 不存在目标明确失败；
- Agent 管理对象重跑幂等；
- Architect create/revise 与非法 structured output；
- 三个 specialist 各自通过 FakeLLM structured-output 路径，且断言实际 schema 请求；
- Geometry LLM 篡改已验证尺寸时拒绝且工程保持未修改；
- Material LLM 注入内部 material ID 时拒绝；
- BCLoad LLM 注入 point/edge ID 时拒绝且不写入工程；
- BCLoad 非法 structured output 或 selector resolve 失败时，既有 Agent-managed BC/load 完整保留；
- point/edge coordinate 的精确值和容差内近似值可解析，明显远离几何的坐标明确失败且不创建定义；
- 同名但 E/nu 不同的既有材料不能满足 assign-only action，失败时不改变原 Section 赋值；
- 正确 create + assign 后，实际赋予材料的 name/E/nu 与 SimulationPlan 完全一致；
- Orchestrator 调用顺序；Geometry / Material / BC_LOAD / Mesh / Solve 五类失败均封装 `ExecutionResult` 并进入 REVIEW；
- Architect planning failure 不进入 Reviewer，返回 WAITING_USER_INPUT；
- 真实 Gmsh -> compile -> solver 正常路径产生网格、位移和 Von Mises 结果。

## 8. 测试命令与结果

### Stage 1

```powershell
.\scripts\codex_pytest.ps1 tests\agent -q
```

当时结果：`13 passed`。

Stage 1 全量：`94 passed, 7 baseline failed`。

### Stage 2

```powershell
.\scripts\codex_pytest.ps1 tests\agent -q
.\scripts\codex_pytest.ps1 tests\agent tests\unit\test_material_manager_service.py tests\unit\test_sketch_geometry_service.py tests\unit\test_stage18_multiple_closed_faces.py tests\unit\test_stage18_multiple_faces_material_assignment.py -q
```

结果：新增累计 `20 passed`；相关组合回归 `28 passed`。

Stage 2 全量：`101 passed, 7 baseline failed`。

### Stage 3 最终

```powershell
.\scripts\codex_pytest.ps1 tests\agent tests\integration\test_agent_normal_case.py -q
.\scripts\codex_pytest.ps1 tests -q
```

Gate B 第二轮修正后的指定命令结果：

```text
tests/agent                                      43 passed
tests/integration/test_agent_normal_case.py       1 passed, 1 warning
full tests                                      125 passed, 7 failed, 18 warnings in 27.18s
```

全量失败集合仍严格等于 Stage 0 的 7 个 baseline failures，没有新增失败。

7 个失败与 Stage 0 完全一致，均为已审核确认的 baseline：

1. `test_stage18_qml_busy_overlay_regression`
2. `test_stage18_qml_contour_regression`
3. `test_stage18_qml_fake_progress_animation`
4. `test_stage18_qml_left_panel_stability_regression`
5. `test_stage18_qml_professional_contour_regression`
6. `test_stage18_result_contour_dialog_data_export_and_qml_presence`
7. `test_stage18_no_scattered_legacy_gravity_constants`

没有新增失败；既有 QML、测试和 `dist/` 未修改。

## 9. 新增文件与既有文件保护

本阶段只新增：

- `agent/` 包；
- `tests/agent/` 测试；
- `tests/integration/test_agent_normal_case.py`；
- `docs/agent_stage_0_audit.md`；
- 本审核包。

没有修改 `core/fem/`、`core/solver/`、现有 services、现有 UI、现有测试或生成目录。

## 10. Stage 4 前置限制

- Reviewer 尚未实现；MESH/SOLVE failure 当前停在 `REVIEW` stage。
- Confirm / Reject / retry limit 尚未接入 Orchestrator 方法。
- 当前 `RepairProposal` / `ReviewResult` 是 Stage 1 数据契约，需在 Stage 4 通过 Reviewer prompt 和五类固定 case 进一步验证。
- 真实 OpenAI/DeepSeek provider 与 UI 明确保留到 Stage 5。
- 在收到明确的 `Stage 3 审核通过，继续` 前，不进入 Stage 4。
