# Fem2dWorkbench Agent 1.0 — Stage 4 Reviewer / HITL 审核包

审核日期：2026-09-24

本审核包覆盖 Stage 4 的 `ReviewerAgent`、structured `ReviewResult` / `RepairProposal`、Human Confirm / Reject、retry limit，以及 Gate B 后追加的 geometry repair 全量重跑和 Material action 顺序约束。实现停在强制审核门 C；未实现 Stage 5 的真实 OpenAI/DeepSeek provider、UI 或 E2E 接入。

## 1. 提交文件

- `agent/reviewer_agent.py`
- `agent/workflow_orchestrator.py`
- `agent/workflow_state.py`
- `agent/review_models.py`
- `agent/simulation_plan.py`
- `agent/execution_result.py`
- `agent/material_agent.py`
- `tests/agent/test_reviewer_agent.py`
- `tests/agent/test_human_approval.py`
- `tests/agent/test_workflow_orchestrator.py`
- `tests/agent/test_workflow_state.py`
- `tests/agent/test_material_agent.py`

所有变更仍位于新增 Agent 层、Agent 测试和审核文档中；未修改 `core/fem/`、`core/solver/`、既有 services、UI、既有测试或生成目录。

## 2. Reviewer 边界

固定输入：

```text
SimulationPlan
+ compact EngineeringProject snapshot
+ ExecutionResult
```

固定输出：

```text
ReviewResult
├─ hasProblem
├─ diagnosis
├─ evidence[]
└─ proposals[]
   └─ RepairProposal(title, reason, changes)
```

Reviewer 只把序列化后的 compact context 发送给统一 `LLMClient.request()`。它没有 Geometry、Material、BC/Load、Mesh 或 Solver 工具，也不持有任何工程 mutation 服务。LLM 输出必须经过 schema、显式字段校验、内部 ID 拒绝和 `SimulationPlan.applyRepair()` 可执行性预验证后才能进入审批状态。

Stage 4 自动测试仍全部使用 `FakeLLMClient`；没有网络请求、真实 provider、本地模型、训练或微调代码，也没有用规则系统代替 LLM 诊断。五类诊断结果来自 FakeLLM 的预设 structured output，生产代码只负责上下文构建和输出验证。

## 3. Reviewer system prompt

```text
You are the Reviewer specialist for Fem2dWorkbench Agent 1.0.
Diagnose the execution using all three supplied sources: the validated SimulationPlan,
the compact current EngineeringProject snapshot, and the ExecutionResult. Check plan to
model consistency, geometry targets, material assignment and parameters, two-dimensional
rigid-body restraints (Tx, Ty, Rz), load targets/vectors, mesh state, and the reported
execution error. Every diagnosis must cite concrete evidence from the supplied context.
Return only schema-constrained ReviewResult data. Propose the smallest executable repairs
to the SimulationPlan using semantic selectors or coordinates, never internal entity IDs.
Do not modify the project, run tools, solve equations, or invent evidence. If the model is
consistent and the execution result is successful, set hasProblem=false and return no
repair proposals.
```

完整常量为 `agent/reviewer_agent.py::REVIEWER_SYSTEM_PROMPT`。

## 4. Structured-output schema 与显式校验

`REVIEW_RESULT_SCHEMA` 顶层严格要求：

```text
hasProblem: boolean
diagnosis: string
evidence: string[]
proposals: RepairProposal[]
```

每个 Proposal 严格要求：

```text
title: non-empty string
reason: non-empty string
changes:
  operation: enum
  operation-specific fields
```

当前允许的确定性 patch operation：

- `set_mesh_size`
- `update_material`
- `replace_geometry`
- `add_point_constraint` / `update_point_constraint`
- `add_edge_constraint` / `update_edge_constraint`
- `add_point_load` / `update_point_load`
- `add_edge_load` / `update_edge_load`

显式二次校验还保证：

- `hasProblem=true` 必须至少有一个 Proposal，并提供 diagnosis/evidence；
- `hasProblem=false` 不允许附带 Proposal；
- 每种 operation 只能包含自己的字段；
- target 必须恰好包含一个 semantic selector 或 coordinate；
- changes 中不得出现 point/edge/face/part/material/section/step internal ID；
- 每个 Proposal 都先对当前 Plan 执行一次无副作用的 `applyRepair()`，确保可形成合法的新计划；
- Reviewer 调用前后比较 `EngineeringProject.to_dict()`，测试同时证明 Reviewer 不修改工程。

`RepairProposal` 构造和序列化使用深拷贝，避免外部输入字典随后改变已审核的 patch 内容。

## 5. buildReviewContext 实际输出示例

以下结构来自固定 Case 1（无位移约束、SOLVE 返回 SingularMatrix）的 compact context；网格只保留统计，不传节点数组、单元矩阵或完整 Solver 对象：

```json
{
  "simulationPlan": {
    "version": 1,
    "geometry": {"type": "rectangle", "width": 100.0, "height": 50.0, "originX": 0.0, "originY": 0.0},
    "material": {"name": "Steel", "E": 210000.0, "nu": 0.3, "thickness": 0.01, "plane_mode": "stress"},
    "pointConstraints": [],
    "edgeConstraints": [],
    "pointLoads": [],
    "edgeLoads": [{"target": {"selector": "right"}, "vector": [100.0, 0.0]}],
    "meshSize": 5.0,
    "requestedResult": "von_mises"
  },
  "projectSnapshot": {
    "projectName": "agent_test",
    "parts": [],
    "materials": [{"id": "mat_steel", "name": "steel", "E": 210000000000.0, "nu": 0.3, "unitWeight": 78500.0}],
    "sections": [{"id": "sec_plate", "materialId": "mat_steel", "thickness": 0.01, "planeMode": "stress"}],
    "boundaryConditions": [],
    "loads": []
  },
  "executionResult": {
    "success": false,
    "stage": "SOLVE",
    "errorType": "RuntimeError",
    "errorMessage": "SingularMatrix",
    "diagnostics": {"mesh": {"exists": true, "nodeCount": 8, "elementCount": 6}}
  }
}
```

项目摘要只包含诊断所需的 geometry point/edge 坐标和端点、材料与 Section、Part 赋值、BC/Load、以及 mesh 统计。失败态 diagnostics 会随 `WorkflowState` 序列化保存，支持暂停/恢复后继续 Reviewer/HITL。

## 6. Human Approval 状态流

执行失败后的自动路径：

```text
GEOMETRY / MATERIAL / BC_LOAD / MESH / SOLVE failure
-> ExecutionResult
-> REVIEW
-> ReviewerAgent.review()
-> ReviewResult
-> APPROVAL + WAITING_APPROVAL
```

Confirm：

```text
selected RepairProposal
-> retry limit precheck
-> current SimulationPlan.applyRepair()
-> new SimulationPlan(version + 1)
-> if geometry changed: clear old Agent-managed BC/Load
-> retryCount += 1
-> GEOMETRY -> MATERIAL -> BC_LOAD -> MESH -> SOLVE
```

Confirm 不调用 Architect。`retry()` 有内部 approval guard，外部直接调用会失败，不能绕过 Human Approval。

Reject：

```text
APPROVAL
-> ARCHITECT + WAITING_USER_INPUT
```

Reject 不清空当前 `EngineeringProject`、`SimulationPlan`、`ExecutionResult` 或 `ReviewResult`。用户下一条自然语言输入由既有 `ArchitectAgent.revise_plan()` 处理。

用户在 `WAITING_USER_INPUT` 提交新自然语言时，Orchestrator 先保存 previous Plan。只有 Architect 成功返回 new Plan 后，才开始新的人工 repair cycle：

```text
retryCount = 0
currentMesh = None
resultData = None
```

原有 `executionResult` / `reviewResult` 仍按 start planning 的既定逻辑清理。Architect 失败时不重置工程内容，也不执行 geometry-change 清理。

Retry limit：

- 每次确认并真正开始重跑时 `retryCount += 1`；
- `retryCount >= maxRetries` 时不再应用新的 Proposal，状态转为 `FAILED`；
- 已有 Plan、Project、ExecutionResult 和 ReviewResult 保留；
- 不存在无限自动循环。
- Reject 后的成功人工 revise 会开启新的 repair cycle，因此重新获得完整 `maxRetries` 预算；旧 cycle 的 retryCount 不会占用新 cycle 配额。

## 7. Geometry repair 完整重跑

强制测试 `test_confirmed_geometry_repair_clears_stale_agent_targets_and_reexecutes_full_plan` 使用真实 GeometryAgent、MaterialAgent、BCLoadAgent 和 FakeLLM：

```text
rectangle model
-> material + Agent-managed left BC/right load
-> MESH
-> SOLVE: SingularMatrix
-> Reviewer: replace_geometry(circle)
-> Human Confirm
-> Plan version 1 -> 2
-> clear old Agent-managed BC/Load
-> GEOMETRY(circle, 64 segments)
-> MATERIAL
-> BC_LOAD (resolve against new circle IDs)
-> MESH
-> COMPILE
-> SOLVE success
```

实测 retry 调用顺序：

```text
clear_managed_bc_load
geometry
material
bc_load
mesh
compile
solve
```

清理发生在用户确认之后、几何替换之前，只清除 metadata 中记录的 Agent-managed 定义。这样 `GeometryAgent.createCircle()` 的 `validate_references()` 不会被旧 rectangle edge IDs 卡死；BC_LOAD 随后依据新 circle geometry 重新解析并写入。测试断言旧 target IDs 不再存在、metadata 指向新定义，且最终 `EngineeringProject.validate_references()` 通过。

Reject → Architect revise 路径使用相同的 geometry 一致性保护，但严格延迟到 Architect 成功之后：

```text
save previous SimulationPlan
-> Architect.revise_plan()
-> compare previous/new geometry
-> if changed: clear Agent-managed BC/Load only
-> reset repair-cycle runtime state
-> GEOMETRY -> MATERIAL -> BC_LOAD -> MESH -> SOLVE
```

完整回归从 rectangle + Agent-managed BC/load + SOLVE failure 开始，Reject 后由 Architect 返回 circle Plan，实测顺序为：

```text
architect_revise
clear_managed_bc_load
geometry
material
bc_load
mesh
compile
solve
```

测试额外放置了一个用户自有 point BC，确认清理后仍存在；最终 circle 工程引用校验通过。另一个测试让 Architect revise 抛错，确认旧 Agent-managed BC/load 和 metadata 完整保留，且未调用清理接口。

旧 mesh 隔离回归先让上一 cycle 形成 `nodeCount=4 / elementCount=2` 的 SOLVE failure，再 Reject 并人工 revise，随后让新 cycle 在 MATERIAL（MESH 之前）失败。Reviewer 收到的新 diagnostics 为：

```json
{"mesh": {"exists": false, "nodeCount": 0, "elementCount": 0}}
```

因此不会携带上一 cycle 的 mesh 统计。该测试还从旧 `retryCount=1` 开始，验证 revise 后归零，并可重新执行恰好 `maxRetries=2` 次 Confirm retry，第三次才进入 `FAILED`。

## 8. Material action 执行顺序

当工程不存在与 Plan `name + E + nu` 完全匹配的材料时，`MaterialAgent._validate_actions()` 在任何 mutation 前定位匹配 create 与第一个 assign：

```text
create_material index < first assign_material index
```

以下情况会被拒绝且工程不变：

```text
assign_material
-> create_material
```

工程已有精确匹配材料时允许只返回 `assign_material`。新增测试分别验证错误顺序拒绝、无材料/Section mutation，以及精确匹配材料的 assign-only 成功。

## 9. 五类固定 Reviewer case

### Case 1：完全没有位移约束

- Plan：point/edge constraints 均为空。
- Project：无 BC。
- ExecutionResult：`SOLVE / SingularMatrix`，mesh 8 nodes / 6 elements。
- FakeLLM：明确诊断仍有 `Tx / Ty / Rz` 三个二维刚体模态，给出 `add_edge_constraint(left, ux=0, uy=0)`。
- 物理含义：固定一条非零长度边同时消除两个平移和面内转动；不再使用仅固定单点、仍保留 Rz 的不充分建议。
- 结果：通过；测试断言 diagnosis 同时包含 Tx/Ty/Rz、Proposal 为 fully fixed left edge，并验证请求包含 Plan + Project + ExecutionResult 三部分。

### Case 2：只有 ux、没有 uy

- Plan：left edge `ux=0, uy=null`。
- ExecutionResult：`SOLVE / SingularMatrix`。
- FakeLLM：把 singular 与剩余 Ty 自由度关联，给出 `update_edge_constraint(left, ux=0, uy=0)`。
- 结果：通过。

### Case 3：无有效匹配材料或未赋值

- Plan：要求 Steel E=210000、nu=0.3。
- Project：没有匹配材料赋给 Part。
- ExecutionResult：MATERIAL failure。
- FakeLLM：只诊断 material/Section 问题，给出合法 `update_material` Proposal。
- 结果：通过；没有误诊为 load 问题。

### Case 4：目标实体不存在

- Project：load 指向 `missing_edge`。
- ExecutionResult：BC_LOAD unknown geometry edge。
- FakeLLM：指出 target 不存在，给出 semantic `update_edge_load(right)`。
- 结果：通过。

### Case 5：正常模型

- Project：geometry/material/Section/BC/load 均与 Plan 一致。
- ExecutionResult：成功。
- FakeLLM：`hasProblem=false`、`proposals=[]`。
- 结果：通过；工程前后快照完全相同，没有“为修复而修复”。

另有非法 Proposal 测试：LLM 输出 `point_id` 等内部 ID 时 structured validation 明确拒绝。

## 10. SingularMatrix → Proposal 完整示例

输入证据：

```text
Plan: left edge ux=0, uy=null
Project snapshot: no y-direction displacement restraint
ExecutionResult: stage=SOLVE, errorMessage=SingularMatrix
```

FakeLLM structured output：

```json
{
  "hasProblem": true,
  "diagnosis": "The remaining Ty rigid-body mode explains the singular solve.",
  "evidence": [
    "The left edge fixes ux only.",
    "No plan constraint fixes uy.",
    "SOLVE reported SingularMatrix."
  ],
  "proposals": [
    {
      "title": "Repair update_edge_constraint",
      "reason": "The supplied project evidence requires this minimal plan repair.",
      "changes": {
        "operation": "update_edge_constraint",
        "target": {"selector": "left"},
        "ux": 0.0,
        "uy": 0.0
      }
    }
  ]
}
```

该输出只形成待审批的 `ReviewResult`；在 Confirm 前不会修改 Plan 或工程。

## 11. 测试结果

执行命令：

```powershell
.\scripts\codex_pytest.ps1 tests\agent -q
.\scripts\codex_pytest.ps1 tests\integration\test_agent_normal_case.py -q
.\scripts\codex_pytest.ps1 tests -q
```

结果：

```text
tests/agent                                      60 passed
tests/integration/test_agent_normal_case.py       1 passed, 1 warning
full tests                                      142 passed, 7 failed, 18 warnings in 27.08s
```

全量失败集合严格等于 Stage 0 已审核的 7 个 baseline failures：

1. `test_stage18_qml_busy_overlay_regression`
2. `test_stage18_qml_contour_regression`
3. `test_stage18_qml_fake_progress_animation`
4. `test_stage18_qml_left_panel_stability_regression`
5. `test_stage18_qml_professional_contour_regression`
6. `test_stage18_result_contour_dialog_data_export_and_qml_presence`
7. `test_stage18_no_scattered_legacy_gravity_constants`

没有新增 failure。

## 12. Gate C 停止点

- Stage 4 已完成，当前停在强制审核门 C。
- 没有进入 Stage 5。
- 没有真实 OpenAI/DeepSeek API、API key、provider SDK、本地模型或 UI 集成。
- 收到明确的“Stage 4 审核通过，继续”之前不继续开发 Stage 5。
