# Claude Code Runtime Orchestration

本文件只保留 Claude Code 运行时差异；通用项目规则不要在这里重复维护。

## 写入前计划

- 修复 / 实现任务允许先做最小只读定位，但首次写文件或 patch 前必须完成 CP0 最小计划：目标、成功标准、边界、任务分型、验证 / 审查路径。
- 边界不清、需求冲突或高风险时，使用 `EnterPlanMode` 或 `Agent(subagent_type="Plan")` 补强计划。

## Agent 工具映射

| subagent_type | 用途 | 逻辑角色 |
|---|---|---|
| `Explore` | 代码库探索、静态审查 | explorer / reviewer |
| `Plan` | 任务规划与范围控制 | pm |
| `general-purpose` | 实现、测试编写、复杂多步骤任务 | builder / tester |

- reviewer 审查必须由未参与实现的 `Explore` 子 Agent 执行。
- builder / tester / pm 是否启动子 Agent，由主 Agent 按任务风险和运行时能力决定。
- 角色 prompt 模板位于 `config/claude-code/agents/*.md`。

## 收口流程

- `lite`：doc-only / rule-only 默认单 Agent；若产生实现链路改动，仍需独立 reviewer。
- `standard`：实现 → 最窄定向验证或 `no_test_reason` → `Agent:Explore` 独立审查。
- `full`：高风险任务先 `Agent:Plan`，再按需拆分探索、实现、测试和审查。
- 同类问题最多回写实现步骤 2 次；定向验证失败、reviewer 未执行或存在阻塞项时，不得宣告完成。

## GitNexus

- 若 `.claude/settings.json` 已配置 `mcpServers.gitnexus`，排查、理解、影响面分析、重构和 PR 审查任务可以优先读取已有 GitNexus 索引来缩小搜索面。
- GitNexus MCP 查询不等于自动建索引；仓库未索引或 stale 时，不要因为用户只说“排查并修复”就静默运行 `analyze`。
- 子 Agent 使用 GitNexus 时，只把图谱结果当作导航线索；最终结论仍需由当前 worktree 的源码、日志或测试证据确认。

## Task 与输出约束

- 使用 `TaskCreate` / `TaskUpdate` / `TaskList` 跟踪 CP0 Intent Lock、CP1 Anchor Slice、CP2 Validation Baseline Freeze、CP3 Final Gate。
- 调用 `Skill` 工具前，先输出 `>>> Skill: <skill-name>`。
- 搜索优先 `rg`；build / test / log 只回传关键错误段或最后 80–120 行；长日志写入 `/tmp/*.log` 并只汇报路径和必要 excerpt。
- Claude Code 在 `~/.claude/projects/` 下维护项目记忆；首次进入 iOS 项目时，可用 `config/claude-code/memory-seed.md` 作为种子提示词。
