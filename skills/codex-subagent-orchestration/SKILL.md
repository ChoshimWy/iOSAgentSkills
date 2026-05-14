---
name: codex-subagent-orchestration
description: 默认优先使用的自适应多 Agent 编排入口；它先按任务复杂度选择 lite / standard / full 档位，再协调 coder / reviewer / tester / main agent 分工；若当前运行时或上层策略要求显式授权 subAgent，而用户尚未授权，则临时回退单 Agent。
---

# Codex 多 Agent 编排

## 角色定位
- 编排型 skill。
- 负责在 Codex 原生能力范围内，先按任务复杂度选择 `lite` / `standard` / `full` 档位，再把编码、审查、测试与最终门禁拆成合适的角色协同。
- 不替代具体实现 skill，也不替代 `verify-ios-build` 的最终裁决。

## 触发判定（硬边界）
- 默认优先使用本 skill 作为编码任务的编排入口，但必须先评估复杂度，不要把所有任务都升级为全量多 Agent。
- 如果任务只是单一职责工作，例如纯代码审查、纯测试补写、纯一次性最终门禁，优先直接切到对应 skill，不要先切本 skill。
- 如果当前运行时、上层策略或用户约束要求显式授权 `subAgent`，而用户尚未授权，则本 skill 只能退化为单 Agent 编排说明；一旦授权条件满足，应恢复按档位自适应编排。

## 自适应编排档位
- `lite`：极小、单文件、无明确测试面或纯文档/规则小改。优先单 Agent，必要时只补 `reviewer explorer`；涉及 Apple Xcode 项目改动时仍必须由主 Agent 执行最终 `verify-ios-build`。
- `standard`：普通代码/规则改动。默认 `coder worker + reviewer explorer（复用 code-review） + 主 Agent gate`；只有出现测试面、失败归因或用户明确要求时才启动 `tester explorer`。
- `full`：跨模块、高风险、并发/availability/公共契约变更、测试或日志归因复杂、私有库联调，或 Apple/Xcode 项目改动需要完整验证链路。采用 `coder worker + reviewer explorer（复用 code-review） + tester explorer + 主 Agent gate`。

## 默认编排
1. 主 Agent 先本地确定目标文件范围、成功标准、编排档位，以及需要复用的 workspace / scheme / destination 基线（如适用）。
2. 按 `lite` / `standard` / `full` 选择是否启动 `coder worker`、`reviewer explorer`、`tester explorer`，不要为低风险任务启动无必要角色。
3. `wait_agent(...)` 只在需要结果推进下一步时使用，不为轮询频繁等待。
4. 如果 reviewer 或 tester 发现阻塞问题，主 Agent 用 `send_input(..., interrupt=true)` 精确回写给 coder。
5. 如果 tester 判断必须补测试代码，再单独启动 `tester worker`，且只持有测试文件 ownership。
6. 当代码、代码审查与测试预检收敛后，主 Agent 自己执行最终 `verify-ios-build`（如适用）。
7. 如果最终门禁失败，主 Agent 把首个真实失败点、影响范围和验证基线回写给 coder，再进入下一轮修复。

## 可选：按角色指定 subAgent 模型（推荐）
当你需要“coder=强模型 / reviewer=快模型 / tester=强模型（中推理）”这类分工时：
- 在 `spawn_agent` 时为每个 subAgent **单独传 `model`**（不传则继承主 Agent 的默认模型）。
- 如需控制推理强度，可为每个 subAgent **单独传 `reasoning_effort`**（例如 `medium`）。

推荐默认（可按项目/预算调整）：
- `coder worker`: 强模型（实现质量优先）
- `reviewer explorer`: 快模型（读审吞吐优先）
- `tester explorer`: 强模型 + `reasoning_effort=medium`（定位/归因质量优先）

注意：
- 具体可用的 `model` 取决于当前运行时/账号；不可用时应回退为不指定（继承默认）。
- 本 Skill 只规定“如何表达分工”，不强行绑定某个具体模型名（避免随平台迭代过期）。

## Plan 输出模板（建议在需要时直接使用）

当用户要求我给出计划（例如 `proposed_plan`）且任务包含实现/验证链路时，默认按以下结构输出：

- **Step 1 主 Agent 计划拆解**
  - 目标、边界、成功标准、所选 `lite` / `standard` / `full` 档位、workspace/scheme/destination 基线、回退条件
- **Step 2 coder worker（按需）**
  - 代码变更任务（含 ownership 与禁止项）
- **Step 3 reviewer explorer（lite 可省略，standard/full 默认启用）**
  - 只输出 `blocking_findings` / `non_blocking_findings`
- **Step 4 tester explorer（仅测试面或 full 档位）**
  - 默认只输出 `suggested_validation`、`executed_validation`、`failure_attribution`、`needs_test_code`
- **Step 5 主 Agent 聚合与裁决**
  - 回写规则、最多 2 轮回环、`verify-ios-build` 门禁（如适用）

如果是私有库本地调试场景，新增补充步骤：
- 私有库本地修改与验证（`pod :path` / 本地引用）
- 私有库提交/推送
- 主项目回到线上版本化引用并复测

## 角色边界
- `coder worker`
  - 只负责实现或修复代码。
  - prompt 必须写清 ownership、成功标准、禁止无关改动、不要回滚他人改动。
  - 输出除 `changed_files`、`summary`、`known_risks` 外，还必须补 `test_impact` 或 `no_test_reason`；只给摘要和影响面，不贴大段 diff、文件全文或完整日志。
  - 编码阶段优先复用：`ios-feature-implementation`、`uikit-feature-implementation`、`swiftui-feature-implementation`、`swift-expert`。
- `reviewer explorer`
  - 只做静态读审，不改代码、不执行最终门禁。
  - 只输出 `blocking_findings` / `non_blocking_findings`；`blocking_findings` 只放真实阻塞项，其余建议全部留在 `non_blocking_findings`，无阻塞项时写 `blocking_findings: []`。
  - 默认复用 `code-review`，重点检查并发隔离、API availability、边界遗漏、架构越界与潜在回归风险。
- `tester`
  - 默认先用 `explorer` 做测试面分析、定向验证建议、失败归因与日志解释。
  - 默认只输出 `suggested_validation`、`executed_validation`、`failure_attribution`、`needs_test_code`；`test_scope` / `suggested_fix` 仅在确实影响决策时补充。
  - 只有在明确需要补测试代码时才升级为 `worker`。
  - 默认复用：`testing`、`ios-device-automation`、`ios-simulator-automation`。
- `main agent`
  - 负责聚合、回写、轮次控制、最终 `verify-ios-build`，以及任务完成态裁决。

## 核心规则
- 在不引入额外外部 orchestrator 的前提下，按 `lite` / `standard` / `full` 档位使用原生 `spawn_agent`、`send_input`、`wait_agent`、`close_agent` 显式编排；不要假设存在自动流转流水线。
- 运行时默认只使用内建 `worker` 与 `explorer`，不额外发明新的底层 Agent 类型。
- Apple API、availability、WWDC 与 framework 指导优先 `appleDeveloperDocs`；构建、测试、simulator、真机、截图与日志优先 `Build iOS Apps` / `xcodebuildmcp` 相关工具；需要在目标项目环境越过 sandbox 时，由主 Agent 使用 `functions.exec_command` 并按需申请升级。工具与日志默认低 Token：搜索优先 `rg` 精确匹配，build/test/log 输出只回传关键错误段、过滤摘要或最后 80~120 行，长日志写入 `/tmp/*.log`。
- 只有当多个开发者工具彼此独立、不会共享写集，也不涉及 `apply_patch` 这类写操作时，才允许使用 `multi_tool_use.parallel`；否则保持串行。
- 最终 completion gate 始终由主 Agent 独占执行 `verify-ios-build`；任何 subAgent 都不能替代最终门禁，也不能决定任务已完成。
- 如果同一任务中已经先跑过定向测试或其它 build/test，最终门禁默认复用同一套 workspace / scheme / destination 基线。
- 长任务默认按“排查 / 实现 / 验证 / 提交”切分会话；新会话只携带目标、关键路径、验证基线和上一轮结论，不复制完整历史。

## 按需阅读的参考文件
- `references/coding-standards.md`：coder / reviewer / tester / main 的编码与输出规范。
- `references/tool-routing.md`：角色到 MCP / 工具 / 升级策略的固定矩阵。
- `references/model-selection.md`：按角色自动挑选 subAgent 模型与回退策略（强/快/中推理）。
- `references/role-contracts.md`：四个角色的输入输出契约。
- `references/prompt-templates.md`：coder / reviewer / tester 的 prompt 模板。
- `references/handoff-loop.md`：失败回环、回写与停止条件。
- `references/apple-gate-rules.md`：Apple/Xcode 项目的最终门禁特殊约束。

## 与其他技能的关系
- 本 skill 只负责编排入口，不替代现有技能。
- 需要实际编码时，切回对应实现型 skill。
- 需要单纯写测试时，直接切 `testing`。
- 需要单纯读审时，直接切 `code-review`。
- 需要最终收尾门禁时，最终仍由主 Agent 切 `verify-ios-build`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: codex-subagent-orchestration`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel
