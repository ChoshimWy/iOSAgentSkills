# iOS Agent Skills 通用技能包

本项目为 Apple 平台开发相关的 Agent Skills 集合，适用于 Claude（`.claude/skills`）与 Codex（`.codex/skills`）AI 助手。

> **仓库状态说明**
> - 自 2026-07-22 起，请开始迁移到新仓库；本仓库后续将停止维护并归档。
> - 请改用新仓库：<https://github.com/ChoshimWy/AgentDevelopmentSkills>
> - 后续文档、规则与技能更新将以新仓库为准；旧仓库仅保留历史参考。

## 目录结构

### Shared Config
- `AGENTS.md` —— 团队共享规则单一来源（宪法层锚点）
- `config/codex/codex.shared.toml` —— 可版本化、可跨设备复用的 Codex 共享默认配置
- `config/codex/templates/codex_verify.example.sh` —— 验证 wrapper 模板；既可复制到目标 Xcode 项目根目录作为 `codex_verify.sh`，也会被安装脚本同步为本机 `~/.codex/bin/codex_verify`
- `tools/digest-xcodebuild-log.sh` —— 本地验证日志摘要脚本；安装脚本同步为 `~/.codex/bin/digest-xcodebuild-log`，供 wrapper 先生成 `verification-report.json` 再交给 Agent
- `CLAUDE.md` —— Claude 入口薄包装，导入 `AGENTS.md`

### Core Implementation
- `ios-feature-implementation/` —— 唯一 iOS 代码实施入口；内部按 `business` / `swiftui` / `liquid-glass` / `uikit` / `mixed-ui` / `advanced-swift` / `refactor` / `sdk-contract` 模式细分

### Design Context
- `design-context-compiler/` —— 把 Figma / Sketch / 人工设计证据编译为 Canonical UI IR、iOS bindings 与受 context budget 约束的 Agent Packet；不直接编写产品 UI

### Automation / Build / Validation
- `ios-automation/` —— Simulator / 真机自动化；优先语义 snapshot 与 snapshot-local 元素 refs，按需采集截图、日志、UI smoke / replay 证据
- `ios-verification/`
- `xcode-build/`
- `codex-subagent-orchestration/` —— 默认优先的自适应编排入口；除 code-review 必须使用独立 reviewer subAgent 外，本仓不对其它 subAgent 使用做额外限制

### Diagnostics
- `code-review/`
- `debugging/`
- `ios-performance/`

### Skill Profile
- `skills/` 是本仓库唯一的 Skill 根目录；安装脚本与本机软链统一只暴露这一套目录。
- 默认用户入口只有一个：`codex-subagent-orchestration`。
- 其它 iOS skills 主要作为主 Skill 的内部执行模块 / 高级手动入口；iOS 代码实施统一落到 `ios-feature-implementation`。
- 低频技能也直接保存在 `skills/` 下，由路由规则决定何时按需触发，而不是再走额外目录。
- Codex 默认采用 **local-only skills mode**：`~/.codex/skills` 指向本仓 `skills/`，同时通过 `~/.codex/config.toml` 将所有 plugin-contributed skills/tools 设为 `enabled = false`。这不会删除 `~/.codex/plugins/cache`，但可防止账号/marketplace 同步回来的插件 Skill 自动生效。

## 使用方法

1. **推荐：一键接入本地 Agent 配置**
```bash
bash install-local-agent-config.sh
```

2. **可选：CC Switch 镜像接入**
```bash
bash install-local-agent-config.sh --ccswitch
```

3. **手工方式（备选）**
- 对于 Claude：复制到 `.claude/skills`
- 对于 Codex：复制到 `.codex/skills`
- 或使用软连接：
```bash
git clone https://github.com/ChoshimWy/AgentDevelopmentSkills.git
ln -s AgentDevelopmentSkills/skills .claude/skills
```

## 多角色配置（按图示结构补齐）

- 仓库内模板源：`config/codex/templates/agents/`（8 角色模板）
  - `pm.toml`（拆解需求 / 验收标准 / checkpoint）
  - `explorer.toml`（上下文收集 / 依赖梳理）
  - `builder.toml`（最小实现 / 变更说明）
  - `tester.toml`（验证建议 / 执行结果 / 失败归因）
  - `reporter.toml`（交付汇总 / 风险收口）
  - `reviewer.toml`（独立高质量静态审查）
  - `docs_researcher.toml`（OpenAI / Apple 官方事实核实）
  - `design_researcher.toml`（通过本机 SketchMCP 读取 `.sketch` 设计源文件并输出 Design Evidence / Design-to-Code source packet，再交给 `design-context-compiler`）
- 这些模板使用 Codex 当前支持的扁平 custom agent schema：`name` / `description` / `developer_instructions`，以及可选 `nickname_candidates` / `model` / `model_reasoning_effort` / `model_verbosity` / `sandbox_mode` / `mcp_servers` / `skills.config`。
- 安装脚本会同步到：`~/.codex/agents/`。
- Profile 模板源：`config/codex/templates/profiles/`；缺失时安装到 `~/.codex/<name>.config.toml`，已有本机 Profile 默认保留，只有显式执行 `bash install-local-agent-config.sh --refresh-profiles` 才备份并刷新。使用 `codex --profile daily|budget|readonly|deep|extreme|interactive-fast` 切换。
- 角色模板说明见：`config/codex/templates/agents/README.md`。
- 验证 wrapper 模板：`config/codex/templates/codex_verify.example.sh`；安装脚本会同步到本机 `~/.codex/bin/codex_verify` 作为全局 fallback，并同步 `tools/digest-xcodebuild-log.sh` 到 `~/.codex/bin/digest-xcodebuild-log`。若目标项目接入了 repo-tracked `codex_verify.sh`，则项目脚本优先；否则自动回退到全局 wrapper。wrapper 会自动接入 shared build-queue daemon，把验证型 `xcodebuild` 串行排队执行，统一使用 Xcode 系统 DerivedData（`~/Library/Developer/Xcode/DerivedData`），并默认只把 `verification-report.json` 打印给 Agent。
- 推荐执行顺序：先 `explorer -> builder -> reporter`，再按需激活 `pm` / `tester`。
- 默认先做任务分型：`doc-only` / `rule-only` / `code-small` / `code-medium` / `code-risky`，再映射到 `lite` / `standard` / `full`。
- 配置映射：
  - 图示 `AGENTS.md` 对应仓库根 `AGENTS.md`
  - 图示 `skills/*/SKILL.md` 对应本仓库全部 skills（含按需触发的低频技能）
  - 图示 `config.toml` 对应本仓库 `config/codex/codex.shared.toml`
  - 共享 Codex 基线保留 `image_model = "gpt-image-2"`、`features.multi_agent = true`、`[agents] max_threads/max_depth`、plugin 与 TUI 等跨设备配置；不再设置 model、reasoning、verbosity 或 `service_tier`，安装时保留本机已有偏好，避免降级模型或全局强制 Fast mode。
  - 角色模型策略：builder 使用 Sol + high；reviewer 使用 GPT-5.4 + high + read-only；explorer/pm/tester 使用 Terra；reporter 使用 Luna；docs_researcher 使用 GPT-5.4 mini 并独占官方文档 MCP；design_researcher 使用 GPT-5.4 + high + read-only，并仅连接本机 `http://localhost:31126/mcp`。
  - `interactive-fast` 是唯一默认启用 Fast mode 的 Profile；普通、后台与长任务使用 Standard。
  - 安装同步只会移除内容与旧 shared baseline 完全一致的全局 `codegraph` / `openaiDeveloperDocs` / `appleDeveloperDocs`，改由 explorer、reviewer、docs_researcher 按角色加载；同名但内容不同的本机自定义 MCP 与其它本机 MCP 均保留。
  - SketchMCP 不进全局 shared config；仅 `design_researcher` 在用户明确要求从 `.sketch` 源文件还原设计时连接，Sketch App 插件未启动则应报告 blocked，不能退化为截图猜测。
  - 安装同步会清理旧 baseline 遗留的单独 `service_tier = "fast"`；只有本机同时显式设置 `[features].fast_mode = true` 时才保留全局 Fast 选择。
  - 本仓 shared config 会禁用 `openai-curated`、`openai-curated-remote`、`openai-primary-runtime`、`openai-bundled` 等插件来源；如需恢复某个插件，需显式把对应 `[plugins."<id>"] enabled = true` 改回。

快速发任务模板：

```text
请使用 codex-subagent-orchestration 处理这个 iOS 任务。
默认按主 Agent 串行承担 explorer -> builder -> reporter 逻辑角色；
实现链路收口必须启动独立 reviewer subAgent 执行 code-review，不能由实现 Agent 自审；
除 code-review 必须使用独立 reviewer subAgent 外，其它 subAgent 使用不做仓库级限制；
若边界不清激活 pm，若需要测试面或失败归因激活 tester。
目标：<需求>
上下文：<目录/文件/报错>
约束：最小改动；先探索再实施；失败先修复再汇报。
非 Plan 模式也必须在首次写入前自动给出 CP0 最小计划。
完成标准：列出 changed_files、验证结果、残余风险；若有阻塞项禁止宣告完成。
```

模板结构自检：

```bash
python3 scripts/validate_codex_agent_templates.py config/codex/templates/agents
```

## 规则与合同入口

- 总规则与长期约束：`AGENTS.md`
- Skill 路由矩阵：`skills/TAXONOMY.md`
- 多 Agent 执行合同：`skills/codex-subagent-orchestration/SKILL.md`
- Checkpoint / Fail-Fix-Report 细则：`skills/codex-subagent-orchestration/references/checkpoint-contract.md`
- 仓库根不保存 `.codex/` 工作目录；仅维护 `config/codex/templates/` 作为模板源，由安装脚本同步到 `~/.codex`。
- 所有技能统一放在 `skills/`；低频/高频只作为文档分组，不再区分发现路径。
- 路径示例默认以 skill 相对路径为准；若指向目标项目脚本（例如 `.codex/*` 或 `run-menubar.sh`），需由目标项目侧提供。

## 私有 Pod / 本地 `:path` 组件规则

- 涉及 CocoaPods 私有库或组件联调时，先查目标工程 `Podfile` / `Podfile.lock` / `Pods/Manifest.lock` 判断真实源码位置。
- 若命中本地 `:path` Pod，默认修改组件源码仓，不修改 `Pods/<LibraryName>` 下的副本快照。
- 如本次修改涉及私有库 / 私有组件，主项目默认必须保持本地 `:path` 私有库依赖；仅当当前尚未指向本地源码且需要验证私有库源码改动时，才先切到本地 `:path`。严格顺序是：确认或切到主项目本地 `:path` 私有库依赖 -> 再修改本地私有库源码仓 -> 最后回到主项目基于该本地依赖做开发、验证与独立 `code-review`；私有库仓内自测不能替代主项目验证。未收到明确指令前，不得把验证或 review 基线切到线上版本化依赖或 `Pods/` vendored snapshot。
- 验证通过后默认先保持当前本地 `:path` 私有库依赖状态，不为了收口自动切回线上版本化依赖；只有用户明确要求回切线上、或准备提交主项目依赖文件时，才处理回线上 / 版本化依赖并按需复测。禁止在未获明确授权时把包含本地 `:path` 私有库引用的 `Podfile` / `Podfile.lock` / `Pods/Manifest.lock` 提交进仓库。
- `Pods/` 默认视为 vendored cache / generated snapshot，不作为实现 ownership。
- 仓库自带 `scripts/pod_private_cache_guard.py`，并由 `.githooks/pre-commit` 默认阻断两类提交：私有 Pod 副本 staged 进提交；以及 `Podfile` / `Podfile.lock` / `Pods/Manifest.lock` 中仍引用本地 `:path` 私有库的提交。
- `bash install-local-agent-config.sh` 会同步全局 `~/.config/git/commitlint.py` 与 `~/.config/git/hooks/commit-msg`，并设置全局 `core.hooksPath`，使其他项目也使用同一套 commit message 规范。
- 推荐在本仓库执行：

```bash
./scripts/install-git-hooks.sh
```


## HTML 文档工作流（新增）

- 适用范围：`Docs` 下的方案、任务清单、评审报告、整改报告等 HTML 文档交付。
- 核心方案文档：[`docs/ios-high-fidelity-ui-ir-plan.html`](docs/ios-high-fidelity-ui-ir-plan.html) —— 面向 UIKit / SwiftUI 的 Design Evidence、Canonical UI IR、Task Context Compiler、Component Registry 与语义视觉验收方案。
- 默认路由：所有可归档 / 可分享的 HTML 方案、PRD、评审、报告、任务清单、接口说明与 handoff 文档都必须使用 `skills/html-docs` 生成；其它 Skill 只输出素材包、结论和证据路径。
- 模板选择：按文档类型读取 `skills/html-docs/references/*-template.md`；任务清单按 `references/tasklist-template.md` 执行任务清单样式。
- 状态标识统一：`√` 表示已完成，`□` 表示未完成 / 待办；建议用 `.check-mark.done` / `.check-mark.todo` 样式呈现。
- 样式基线：Notion-light + SidusLinkPro checklist（Hero 元信息独立行、chips、状态图例、指标卡、固定表格与 callout），同时必须通过 CSS variables + `@media (prefers-color-scheme: dark)` 支持系统暗黑模式。
- 文档治理：顶部使用绝对日期（创建/更新），实施后必须回写进度，保持文档与代码状态一致。

## 默认收口与可选证据验证

- 默认完成标准：定向验证或必要验证通过，且独立 reviewer subAgent 执行的 `code-review` 无 `阻塞问题`。
- 涉及代码改动时，`ios-verification` 默认只执行**最窄定向单测**：优先 `-only-testing` 到单个 test case / test class，其次最小受影响 test file / bundle；真机 / 模拟器验证不属于默认验证执行面。
- 如果当前改动不适合运行测试，验证阶段必须给出 `no_test_reason` 与替代验证依据，然后交给独立 reviewer subAgent 执行 `code-review`。
- 如果当前改动没有可低成本执行的单测路径，验证阶段必须给出 `no_test_reason` 与 `suggested_validation`，且不要自动升级到真机 / 模拟器验证。
- `code-review` 默认审查本次任务全量差异及本次修改带来的直接影响面，包含 staged、unstaged、untracked 与任务起点基线之后的相关提交；用于实现链路收口时必须由未参与实现的独立 reviewer subAgent 执行。
- `ios-verification` 不再把完整项目环境验证作为所有 Apple Xcode 项目改动的强制收尾，仅在按需补强时执行。
- 执行可选 `xcodebuild` 验证时，仍必须在目标项目根目录的非沙盒项目环境执行，不能把 sandbox 结果当作完整项目环境证据或最终验证结论。
- 已打开 Xcode 且官方 `xcode` MCP 可用时，日常验证优先快车道：`GetTestList` → 一次 `RunSomeTests` / `BuildProject` → 仅失败时 `GetBuildLog` / Issue Navigator；禁止验证角色调用 Xcode MCP 写工具，也不要为同一 fingerprint 默认重复跑 wrapper。
- 本地直接执行 `xcodebuild` 参数探测与验证需求（含 `-list` / `-showdestinations` / build/test）仍必须在非沙盒项目环境通过 wrapper 执行：由主 Agent 使用 `functions.exec_command` 并设置 `sandbox_permissions="require_escalated"` 启动目标项目根目录的 `codex_verify.sh`，若项目未接入则回退到本机 `~/.codex/bin/codex_verify`。不得直接调用 `xcodebuild` 二进制；wrapper 只在 MCP 不可用、需要可归档 artifact、发布前/高风险/依赖或项目配置变更、多人验证冲突或 MCP 失败无法归因时升级使用，并会接入 shared build-queue daemon 与系统 DerivedData。
- wrapper 验证输出遵守 **脚本先裁剪，Agent 后判断**：wrapper / digest 脚本先生成 `verification-report.json`、`diagnostics.json`、`build-summary.txt`，Agent 默认只读取 `verification-report.json`；只有 `needs_raw_log=true` 或用户显式要求时，才读取 raw log 的定向片段。若必须实时查看完整日志，显式设置 `CODEX_VERIFY_STREAM_LOG=1`。
- 如果 `--queue-status`、wrapper 输出或错误信息表明已有其他 Agent 正在执行验证，当前 Agent 应等待 shared build-queue daemon 完成当前任务，或把本轮标记为 `env_issue` / `blocked`；不要为了绕过同一个 `build.db` 锁而切到单独 `-derivedDataPath` 跑同一组最窄测试。
- 可选完整验证继续遵守既有 Xcode 约束：优先 `.xcworkspace`，优先绑定了单元测试 `*Tests` target / bundle 的 scheme，iOS 路径默认优先已连接真机。验证链路由 wrapper 提交到 daemon；可通过 `codex_verify.sh --queue-status` 查看当前 active job 与 pending jobs。非验证型构建讨论仍以 Xcode 系统 DerivedData 为基线；旧 `XCODE_DERIVED_DATA_*` / `CODEX_DERIVED_DATA_SLOT` 公开配置不再支持。
- 实现链路默认三步收口：`实现 skill -> 定向验证 / no_test_reason -> reviewer subAgent(code-review)`。
- 未执行可选完整验证时，交付应说明已执行的定向验证/必要验证、`code-review` 结论与残余风险。

## 多 Agent 编排锚点

- `codex-subagent-orchestration` 是默认的 iOS 主 Skill 入口；实现、调试、性能、验证、Apple 文档与可选证据验证都应先经过它，再内部路由到对应模块。所有代码实施统一转入 `ios-feature-implementation` 的内部模式，不再要求用户手动选择 SwiftUI / UIKit / Swift Expert 实施 Skill。
- 编排默认按 `lite` / `standard` / `full` 三档选择角色。
- 默认先按任务分型器分类，再决定角色激活矩阵（最小集合：`explorer + builder + reporter`）。
- 修复 / 实现任务不依赖手动 Plan 模式；允许先做最小只读定位，但首次写入前必须自动给出 CP0 最小计划，禁止从代码查找直接跳到实现。
- 除实现链路的 `code-review` 必须交给独立 reviewer subAgent 外，本仓不对 coder / tester / pm / reporter 等其它 subAgent 的启动场景、角色拆分或数量做额外限制；主 Agent 可按当前任务与运行时能力自行决定。
- 无论其它角色是否使用原生 subAgent，实现链路仍必须保留 `ios-verification` 与独立 reviewer subAgent `code-review`；reviewer subAgent 不可用时只能报告 blocked / pending review。
- CP0 最小计划（`proposed_plan`）输出只要是实现链路，就必须显式包含独立 reviewer subAgent 执行的 `code-review` 审查步骤。
- 日志输出默认低 token：只回传关键错误段或最后 80~120 行；长日志写入 `/tmp/*.log`。

## Harness Workflow 合同（新增）

- 默认启用 checkpoint：`CP0 Intent Lock`、`CP1 Anchor Slice`、`CP2 Validation Baseline Freeze`、`CP3 Final Gate`。
- 主 Agent 维护 `checkpoint_status` 作为单一事实源。
- 默认遵守 `fail-fix-report`：先定位失败 -> 修复并重跑 -> 再汇报。

## 标准门禁一键自检顺序

```bash
bash install-local-agent-config.sh
./scripts/install-git-hooks.sh
python3 scripts/lint_skill_schema.py
python3 skills/design-context-compiler/scripts/self_test.py
python3 scripts/validate_codex_agent_templates.py config/codex/templates/agents
python3 scripts/check_codex_model_policy.py --offline
python3 scripts/check_claude_config_policy.py
python3 scripts/check_codex_model_policy.py
# 可选：诊断本机旧 profile 与不可解析 MCP，不自动删除本机自定义配置
python3 scripts/check_codex_model_policy.py --local-config ~/.codex/config.toml
python3 scripts/lint_subagent_orchestration_policy.py
python3 scripts/lint_workflow_contract_policy.py
python3 scripts/lint_harness_workflow_policy.py
python3 scripts/lint_verify_ios_build_policy.py
git diff --check
```

## 贡献

欢迎补充更多 Apple 平台相关技能，完善文档与案例。
