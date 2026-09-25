# Fem2dWorkbench Agent 1.0 — Stage 5 最终实施报告

日期：2026-09-25

## 1. 最终结果

Agent 1.0 已完成外部 LLM provider、真实 Backend E2E 和现有 QML GUI 集成。Agent 不包含、训练、微调或部署本地大语言模型；所有智能推理均通过统一 `LLMClient` 接口调用外部 OpenAI 或 DeepSeek API。FEM/Solver 数学核心未修改。

真实 DeepSeek 门禁已通过：

- API smoke：真实 structured output 返回成功；
- 正常 Backend E2E：Natural Language → Architect → Geometry → Material → BC/Load → Gmsh → Compile → Solver → Result；
- Reviewer E2E：无位移约束模型 → 可诊断 SOLVE 前置校验失败 → Reviewer → RepairProposal → Human Confirm → SimulationPlan v2 → 完整重试 → Solve success。

## 2. 最终文件结构

```text
agent/
  __init__.py
  llm_client.py
  llm_providers.py
  workflow_factory.py
  architect_agent.py
  geometry_agent.py
  material_agent.py
  bc_load_agent.py
  reviewer_agent.py
  simulation_plan.py
  execution_result.py
  review_models.py
  workflow_state.py
  workflow_orchestrator.py

scripts/
  configure_agent_llm.ps1
  codex_real_agent_e2e.ps1
  gui_agent_acceptance.py
  codex_py.ps1
  codex_pytest.ps1

tests/
  agent/
  e2e/test_agent_real_api.py
  e2e/test_agent_real_backend_e2e.py
  integration/test_agent_normal_case.py
  integration/test_agent_gui_bridge.py

ui/
  backend/workbench_bridge.py
  qml/MainWorkbench.qml
```

## 3. Provider 配置

统一环境变量：

```text
FEM2D_AGENT_LLM_PROVIDER
FEM2D_AGENT_LLM_MODEL
FEM2D_AGENT_LLM_API_KEY
FEM2D_AGENT_LLM_BASE_URL
```

可选：

```text
FEM2D_AGENT_LLM_TIMEOUT_SECONDS=120
```

DeepSeek 示例值：

```text
FEM2D_AGENT_LLM_PROVIDER=deepseek
FEM2D_AGENT_LLM_MODEL=deepseek-chat
FEM2D_AGENT_LLM_BASE_URL=https://api.deepseek.com
```

OpenAI 示例值：

```text
FEM2D_AGENT_LLM_PROVIDER=openai
FEM2D_AGENT_LLM_MODEL=<支持 Structured Outputs 的模型>
FEM2D_AGENT_LLM_BASE_URL=https://api.openai.com/v1
```

API key 只从环境变量读取，不写入源码、测试、配置样例或仓库。也支持相应的 `OPENAI_MODEL` / `OPENAI_API_KEY` / `OPENAI_BASE_URL` 和 `DEEPSEEK_*` 变量作为 provider-specific fallback。

实现协议：OpenAI 使用 Responses API 的 JSON Schema structured output；DeepSeek 使用 Chat Completions JSON Output，并在 Agent 层继续执行 schema 与显式业务校验。

## 4. 实际运行方法

启动 GUI：

```powershell
.\scripts\codex_run_gui.ps1
```

启动脚本会将已持久化的 Windows User 级 Agent 环境变量导入 GUI 子进程，并打印实际 Python 路径以及脱敏 provider/model/base URL/key 状态，不输出 API key。Python provider loader 也会在每次创建 workflow 时重新读取运行时环境；Windows GUI 进程若没有继承最新值，会只读 HKCU User Environment 作为后备。

运行默认离线测试（Fake/Mock LLM，不访问网络）：

```powershell
.\scripts\codex_pytest.ps1 tests -q
```

显式运行真实 API smoke/E2E：

```powershell
.\scripts\codex_real_agent_e2e.ps1
```

真实测试脚本只在显式入口中设置 `FEM2D_AGENT_RUN_REAL_API=1`；普通 pytest 不访问网络，没有凭据时真实 E2E 自动跳过或给出明确配置错误。

## 5. GUI 使用流程

1. 启动 Fem2dWorkbench，点击顶部 `Agent 1.0`。
2. 输入自然语言仿真需求，点击 `启动 Agent 工作流`。
3. 对话框持续显示 workflow status 和当前 stage。
4. 正常完成后，界面自动切换到现有 `求解结果`，复用节点结果、单元结果、位移云图、应力云图与导出能力。
5. 出现可诊断失败时，对话框显示 Reviewer diagnosis、evidence 和 RepairProposal 列表。
6. 选择 Proposal 后点击 `Confirm 并重试`；Proposal 确定性生成下一版 SimulationPlan，并从 Geometry 开始完整重跑。
7. 点击 `Reject，返回修改` 后，保留当前工程、Plan、ExecutionResult 和 ReviewResult；用户可继续输入自然语言修改说明，进入新的人工 repair cycle。
8. 如果新计划改变 geometry，且原工程存在非 Agent-managed 的手工 BC/Load，GUI 会明确提示这些定义未被静默删除、其物理目标需要重新确认。

GUI 和真实 Backend E2E 通过同一个 `create_agent_workflow()` factory 创建 provider/client 和五个 Agent。由于 Gmsh 的 Python 初始化会安装 signal handler，GUI Agent chain 通过 Qt zero-delay callback 在主解释器主线程执行，避免 `signal only works in main thread`；普通非 Agent 求解仍沿用原有 worker。

## 6. 测试结果

### Stage 5 专项

- `tests/agent`：68 passed；
- `tests/agent + tests/integration/test_agent_normal_case.py + tests/integration/test_agent_gui_bridge.py`：75 passed；
- 真实 DeepSeek `tests/e2e`：3 passed；
- QML offscreen 实际加载：1 root object，成功；
- GUI/Bridge 新回归：6 passed，覆盖运行时环境到真实 DeepSeek client 的 GUI 创建入口、正常结果复用、Reviewer Confirm、Reject 后自然语言 revise、手工定义安全提示和 QML 控件存在性；
- 真实 QML 控件验收：输入自然语言 → 触发 `agentStartButton.clicked` → DeepSeek → Gmsh → Compile → Solver → `COMPLETED / RESULT` → 现有 Result UI 节点/单元数据装载成功。

### 全量

```text
156 passed, 3 skipped, 7 failed, 18 warnings
```

7 个 failure 与 Stage 0 登记 baseline 完全一致：6 个既有 QML 文本/布局回归断言和 1 个既有 dist gravity 常量扫描；Agent 1.0 未新增全量测试 failure。3 个 skip 为普通离线测试中默认禁用的真实 API 测试。

## 7. 已知限制

- 几何范围保持 Agent 1.0 边界：rectangle 与固定 64 段离散 circle；
- 当前为单活动零件、单材料/Section 主路径，不扩展多材料区域或多物理场；
- semantic selector 只支持既定 canonical selector 或带有限 tolerance 的坐标；
- Reviewer repair 受 `maxRetries` 限制，默认 2 次；
- 静力前置校验只确定性拒绝“完全没有任何 ux/uy 位移约束”的模型；更复杂的欠约束诊断仍由 Reviewer 结合求解错误和工程快照完成；
- OpenAI adapter 对现有跨 provider schema 使用 `strict=false`，Agent 层仍执行完整显式校验；
- DeepSeek JSON Output 偶尔可能返回空内容或不合规 JSON，此时会明确失败并进入既定 workflow 处理，不会在未校验输出上修改工程；
- 为满足 Gmsh 主线程约束，Agent 1.0 的 GUI chain 当前在 Qt 主线程执行；外部 API 响应期间界面交互可能短暂停顿，后续版本可在不移动 Gmsh 的前提下进一步拆分网络阶段；
- 真实 API E2E 会产生网络请求、延迟和少量 API 费用，因此只通过显式脚本运行。

## 8. 架构边界确认

```text
Architect / Geometry / Material / BCLoad / Reviewer
                    ↓
               LLMClient
                    ↓
          OpenAI API / DeepSeek API
```

切换 provider 不修改任何 specialist Agent 的业务逻辑。Agent 输出必须先通过 structured-output 与显式校验，再执行 Fem2dWorkbench 工程调用。Mesh/Solve 主路径保持 Gmsh → Compile → `solve_static_linear()`。
