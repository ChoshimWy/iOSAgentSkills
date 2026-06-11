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
- `~/.codex/bin/codex_verify` —— 由安装脚本自动同步；当目标项目没有 repo-tracked `codex_verify.sh` 时，`verify-ios-build` 会自动回退到这个全局 wrapper

推荐执行顺序：
`explorer -> builder -> reporter`，按需激活 `pm` 与 `tester`

说明：
- 这些 `.toml` 是 Codex custom agent 文件，使用当前支持的扁平 schema：`name` / `description` / `developer_instructions`，以及可选 `model_reasoning_effort` / `sandbox_mode`。
- 工作流合同字段不再放单独 TOML table，而是内嵌在 `developer_instructions` 中约束输出与职责边界。
- 安装脚本会把它们同步到 `~/.codex/agents/`。
- 安装脚本也会同步 `~/.codex/bin/codex_verify` 作为全局验证入口。
- `codex_verify.example.sh` 会同步到 `~/.codex/templates/codex_verify.example.sh`，供目标项目复制落地。
- 推荐优先级：`<repo-root>/codex_verify.sh` > `~/.codex/bin/codex_verify`。
- 可通过 `codex_verify.sh --queue-status` 或 `~/.codex/bin/codex_verify --queue-status` 查看 daemon 当前 active job 与 pending jobs。
- 全局硬约束仍以仓库根 `AGENTS.md` 与 `skills/codex-subagent-orchestration/` 合同为准。
- Apple Xcode 项目改动默认以定向验证与 code-review 收口；`final-evidence-gate` / `verify-ios-build` 仅按需补强。
- `testing` 默认只执行最窄定向单测；真机 / 模拟器验证不属于默认收口执行面。
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
