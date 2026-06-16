@AGENTS.md

---

# Claude Code Runtime Orchestration (平台适配层)

本段是 Claude Code 特有的运行时编排指令，位于共享规则 AGENTS.md 之上。Codex 用户不受本段影响。

## Plan Mode 作为 CP0 Intent Lock (对应 AGENTS.md "默认工作流" → 编排入口)

当任务涉及实现且边界不明确时，先使用 `EnterPlanMode` 进入计划模式：
- 输出任务目标、成功标准、边界范围
- 判定任务分型：doc-only / rule-only / code-small / code-medium / code-risky
- 选择编排档位：lite / standard / full
- 确定 workspace / scheme / destination 基线

退出条件：目标与边界已明确，主 Agent 确认可进入实现阶段。

## Agent 工具角色映射 (对应 AGENTS.md "默认工作流" → 多角色协作)

Claude Code 的 `Agent` 工具支持以下 `subagent_type`：

| subagent_type | 用途 | 对应 Codex 角色 |
|---|---|---|
| `Explore` | 快速代码库探索、静态审查 | explorer / reviewer |
| `Plan` | 任务规划与范围控制 | pm |
| `general-purpose` | 复杂多步骤实现、测试编写 | builder / tester |

使用规则：
- explorer 探索：`Agent(subagent_type="Explore", prompt=<explorer.md 模板>)`
- reviewer 审查：`Agent(subagent_type="Explore", prompt=<reviewer.md 模板>)`
- builder 实现：`Agent(subagent_type="general-purpose", prompt=<builder.md 模板>)`
- tester 验证：`Agent(subagent_type="general-purpose", prompt=<tester.md 模板>)`
- pm 规划：`Agent(subagent_type="Plan", prompt=<pm.md 模板>)` 或直接使用 `EnterPlanMode`
- reporter 汇总：由主 Agent 直接完成，不另启动子 Agent

角色 prompt 模板参见 `config/claude-code/agents/*.md`。

## 自适应编排档位 (对应 AGENTS.md "默认工作流" → 编排策略)

### lite（doc-only / rule-only）
- 单 Agent 执行
- 若任务实际产生实现链路改动，仍必须启动独立 reviewer 子 Agent 执行 code-review，主 Agent 不得自审
- 涉及 Apple Xcode 项目改动时可按需执行 ios-verification

### standard（code-small / code-medium）
- 顺序执行：实现 Skill → ios-verification / 定向验证 → `Agent:Explore` 独立审查
- 审查必须由未参与实现的 reviewer 子 Agent 执行；若不可用则 blocked / pending review
- 主 Agent 聚合结果，必要时回写修正（最多 2 轮）

### full（code-risky）
- `Agent:Plan` 完成需求拆解与范围控制
- `Agent:Explore` 收集上下文、梳理依赖与风险
- `Agent:general-purpose` 执行实现
- 并行启动：`Agent:Explore`（审查）∥ `Agent:general-purpose`（测试）
- 主 Agent 聚合验证与审查结论；按需执行 `ios-verification`

## 三步收口工作流 (对应 AGENTS.md "默认工作流" → 三步收口)

遵循 AGENTS.md 定义的三步收口流程（实现 → 定向验证 → 独立审查）。Claude Code 补充：

- Step 2 默认只执行最窄定向单测：优先 `-only-testing` 到单个 test case / test class，其次最小受影响 test file / bundle。
- 若没有可低成本执行的单测路径，则记录 `no_test_reason` 与 `suggested_validation`，不自动升级到真机 / 模拟器验证。
- 真机 / 模拟器验证仅在用户显式要求、发布前自检、高风险或证据不足时，按需进入 `ios-verification`。

循环控制（源自 AGENTS.md "Checkpoint 与 Fail-Fix-Report"）：
- 同类问题最多回写实现步骤 2 次
- 超过上限仍未收敛 → `next_action = blocked`
- 定向验证失败、独立 reviewer 子 Agent 未执行、或 code-review 存在阻塞项时不得宣告默认收口完成

## Skill 使用声明 (对应 AGENTS.md "默认工作流" → Skill 路由)

调用 `Skill` 工具前，必须先输出 `>>> Skill: <skill-name>` 声明即将使用的 skill，让用户明确知道当前路由到了哪个 skill。

## Task 工具用于 Checkpoint 跟踪 (对应 AGENTS.md "Checkpoint 与 Fail-Fix-Report")

使用 `TaskCreate` / `TaskUpdate` / `TaskList` 跟踪 AGENTS.md 定义的四个 Checkpoint：

| CP | 名称 | Task 示例 |
|---|---|---|
| CP0 | Intent Lock | `TaskCreate("CP0 Intent Lock — 目标与边界确认")` |
| CP1 | Anchor Slice | `TaskCreate("CP1 Anchor Slice — 首个关键切片验收")` |
| CP2 | Validation Baseline Freeze | `TaskCreate("CP2 Baseline Freeze — 锁定验证基线")` |
| CP3 | Final Gate | `TaskCreate("CP3 Final Gate — 定向验证与审查收口")` |

主 Agent 维护 `checkpoint_status` 作为单一事实源。每个 CP 完成后标记 `completed`。

## 低 Token 输出约束

- 搜索优先使用 `rg`（Bash 执行）
- build / test / log 只回传关键错误段或最后 80~120 行
- 长日志写入 `/tmp/*.log`，回复只给路径和必要 excerpt
- 长任务按"排查 / 实现 / 验证 / 提交"切分会话

## 记忆系统

Claude Code 在 `~/.claude/projects/` 下自动维护项目记忆。首次进入 iOS 项目时，可用 `config/claude-code/memory-seed.md` 作为种子提示词，在首次对话中明确项目约定和关键规则。后续会话会自动加载。
