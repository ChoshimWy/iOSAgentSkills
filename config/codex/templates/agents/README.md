# Multi-Agent Role Templates

该目录提供 5 角色协作模板：
- `pm.toml`
- `explorer.toml`
- `builder.toml`
- `tester.toml`
- `reporter.toml`

以及 1 个项目侧验证模板：
- `../codex_verify.example.sh` —— 复制到目标 Xcode 项目根目录并重命名为 `codex_verify.sh`，作为多 Codex CLI 本地 `xcodebuild` / `build-check` 的统一验证入口；wrapper 会自动接入 shared build-queue daemon，把验证型 `xcodebuild` 串行排队执行，并统一使用 Xcode 系统 DerivedData

以及 1 个本机全局验证入口：
- `~/.codex/bin/codex_verify` —— 由安装脚本自动同步；当目标项目没有 repo-tracked `codex_verify.sh` 时，`ios-verification` 会自动回退到这个全局 wrapper
- `~/.codex/bin/digest-xcodebuild-log` —— 由安装脚本自动同步；wrapper 用它从 raw `xcodebuild` 日志生成 `verification-report.json` / `diagnostics.json`，默认只把结构化报告交给 Agent

推荐执行顺序：
`explorer -> builder -> reporter`，按需激活 `pm` 与 `tester`

说明：
- 这些 `.toml` 是 Codex custom agent 文件，使用当前支持的扁平 schema：`name` / `description` / `developer_instructions`，以及可选 `nickname_candidates` / `model` / `model_reasoning_effort` / `sandbox_mode` / `mcp_servers` / `skills.config`。
- 截至 2026-06-15 的共享 Codex 基线使用 `model = "gpt-5.5"`、`image_model = "gpt-image-2"`、`features.multi_agent = true` 与 `[agents] max_threads/max_depth`；默认 reasoning effort 为 `medium`，高难任务可通过 profile 或临时配置升到 `xhigh`。默认进入 `codex-subagent-orchestration` 只表示先做编排决策；除实现链路 reviewer subAgent 是强制收口角色外，本仓不对其它 subAgent 使用做额外限制。
- 主 Agent 可自主决定 coder / tester / pm / reporter 等非 review 角色是否使用原生 subAgent；本仓只强制实现链路 `code-review` 使用独立 reviewer subAgent。
- 模型默认继承主 Agent；只有用户明确要求、任务风险需要或预算/吞吐目标明确时才在 `spawn_agent` 中覆盖 `model` / `reasoning_effort`。
- 工作流合同字段不再放单独 TOML table，而是内嵌在 `developer_instructions` 中约束输出与职责边界。
- 安装脚本会把它们同步到 `~/.codex/agents/`。
- Codex 默认采用 local-only skills mode：`~/.codex/skills` 指向本仓 `skills/`，共享配置会把所有 plugin-contributed skills/tools 设为 `enabled = false`；插件 cache 可保留但不会自动参与 Skill 选择。
- 安装脚本也会同步 `~/.codex/bin/codex_verify` 作为全局验证入口。
- 安装脚本也会同步 `~/.codex/bin/digest-xcodebuild-log` 作为全局日志摘要入口。
- `codex_verify.example.sh` 会同步到 `~/.codex/templates/codex_verify.example.sh`，供目标项目复制落地。
- 推荐优先级：`<repo-root>/codex_verify.sh` > `~/.codex/bin/codex_verify`。
- 可通过 `codex_verify.sh --queue-status` 或 `~/.codex/bin/codex_verify --queue-status` 查看 daemon 当前 active job 与 pending jobs。
- 全局硬约束仍以仓库根 `AGENTS.md` 与 `skills/codex-subagent-orchestration/` 合同为准。
- Apple Xcode 项目改动默认以定向验证与独立 reviewer subAgent code-review 收口；`ios-verification` 仅按需补强。
- `ios-verification` 默认只执行最窄定向单测；真机 / 模拟器验证不属于默认收口执行面。
- 默认先做任务分型：`doc-only` / `rule-only` / `code-small` / `code-medium` / `code-risky`。
- 默认最小逻辑角色集合：`explorer + builder + reporter`；命中风险条件再激活 `pm` 与 `tester`。非 review 角色是否使用 subAgent 不做仓库级限制，但实现链路 reviewer subAgent 是强制独立收口角色。
- 统一字段：每个角色输出都需包含 `checkpoint_status`、`first_failure`、`next_action`（无阻塞时 `first_failure: none`）。
- 需要生成可归档 / 可分享的正式 HTML 文档时，角色只整理 source packet；最终 HTML 由 `skills/html-docs` 统一生成并处理暗黑模式适配。
- Builder 新增 Apple 源文件时必须执行 file_header_check：同目录 header 风格 -> 真实 `whoami` / `id -un` -> `YYYY/M/D` 日期 -> 禁止 `Codex` / 字面量 `$(whoami)` / 占位符 -> 完成前复查。

快速任务模板：
```text
请按 explorer -> builder -> reporter 逻辑角色执行；
实现链路收口必须启动独立 reviewer subAgent 执行 code-review，不能由实现 Agent 自审；
除 code-review 必须使用独立 reviewer subAgent 外，其它 subAgent 使用不做仓库级限制；
若边界不清激活 pm，若需要测试面或失败归因激活 tester。
目标：<需求>
上下文：<目录/文件/报错>
约束：最小改动；先探索再实施；失败先修复再汇报。
非 Plan 模式也必须在首次写入前自动给出 CP0 最小计划。
完成标准：列出 changed_files、验证结果、残余风险；若有阻塞项禁止宣告完成。
```
