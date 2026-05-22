# Multi-Agent Role Templates

该目录提供 5 角色协作模板：
- `pm.toml`
- `explorer.toml`
- `builder.toml`
- `tester.toml`
- `reporter.toml`

推荐执行顺序：
`explorer -> builder -> reporter`，按需激活 `pm` 与 `tester`

说明：
- 这些 `.toml` 是 Codex custom agent 文件，使用当前支持的扁平 schema：`name` / `description` / `developer_instructions`，以及可选 `model_reasoning_effort` / `sandbox_mode`。
- 工作流合同字段不再放单独 TOML table，而是内嵌在 `developer_instructions` 中约束输出与职责边界。
- 安装脚本会把它们同步到 `~/.codex/agents/`。
- 全局硬约束仍以仓库根 `AGENTS.md` 与 `skills/codex-subagent-orchestration/` 合同为准。
- Apple Xcode 项目改动的最终完成态，必须由主 Agent 执行 `verify-ios-build` 决定。
- 默认先做任务分型：`doc-only` / `rule-only` / `code-small` / `code-medium` / `code-risky`。
- 默认最小角色集合：`explorer + builder + reporter`；命中风险条件再激活 `pm` 与 `tester`。
- 统一字段：每个角色输出都需包含 `checkpoint_status`、`first_failure`、`next_action`（无阻塞时 `first_failure: none`）。

快速任务模板：
```text
请按 ~/.codex/agents 角色分工执行：默认 explorer -> builder -> reporter；
若边界不清激活 pm，若需要测试面或失败归因激活 tester。
目标：<需求>
上下文：<目录/文件/报错>
约束：最小改动；先探索再实施；失败先修复再汇报。
完成标准：列出 changed_files、验证结果、残余风险；若有阻塞项禁止宣告完成。
```
