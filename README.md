# iOS Agent Skills 通用技能包

本项目为 Apple 平台开发相关的 Agent Skills 集合，适用于 Claude（`.claude/skills`）与 Codex（`.codex/skills`）AI 助手。

## 目录结构

### Shared Config
- `AGENTS.md` —— 团队共享规则单一来源（宪法层锚点）
- `config/codex/codex.shared.toml` —— 可版本化、可跨设备复用的 Codex 共享默认配置
- `config/codex/templates/codex_verify.example.sh` —— 验证 wrapper 模板；既可复制到目标 Xcode 项目根目录作为 `codex_verify.sh`，也会被安装脚本同步为本机 `~/.codex/bin/codex_verify`
- `tools/digest-xcodebuild-log.sh` —— 本地验证日志摘要脚本；安装脚本同步为 `~/.codex/bin/digest-xcodebuild-log`，供 wrapper 先生成 `verification-report.json` 再交给 Agent
- `CLAUDE.md` —— Claude 入口薄包装，导入 `AGENTS.md`

### Core Implementation
- `ios-feature-implementation/` —— 唯一 iOS 代码实施入口；内部按 `business` / `swiftui` / `liquid-glass` / `uikit` / `mixed-ui` / `advanced-swift` / `refactor` / `sdk-contract` 模式细分

### Automation / Build / Validation
- `ios-automation/`
- `ios-verification/`
- `xcode-build/`
- `codex-subagent-orchestration/` —— 默认优先的自适应编排入口；仅在用户显式要求 subAgent / parallel agent / delegation 或当前 prompt 明确授权时才实际调用原生 subAgent

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
ln -s iOSAgentSkills/skills .claude/skills
```

## 多角色配置（按图示结构补齐）

- 仓库内模板源：`config/codex/templates/agents/`（5 角色模板）
  - `pm.toml`（拆解需求 / 验收标准 / checkpoint）
  - `explorer.toml`（上下文收集 / 依赖梳理）
  - `builder.toml`（最小实现 / 变更说明）
  - `tester.toml`（验证建议 / 执行结果 / 失败归因）
  - `reporter.toml`（交付汇总 / 风险收口）
- 这些模板使用 Codex 当前支持的扁平 custom agent schema：`name` / `description` / `developer_instructions`，以及可选 `nickname_candidates` / `model` / `model_reasoning_effort` / `sandbox_mode` / `mcp_servers` / `skills.config`。
- 安装脚本会同步到：`~/.codex/agents/`。
- 角色模板说明见：`config/codex/templates/agents/README.md`。
- 验证 wrapper 模板：`config/codex/templates/codex_verify.example.sh`；安装脚本会同步到本机 `~/.codex/bin/codex_verify` 作为全局 fallback，并同步 `tools/digest-xcodebuild-log.sh` 到 `~/.codex/bin/digest-xcodebuild-log`。若目标项目接入了 repo-tracked `codex_verify.sh`，则项目脚本优先；否则自动回退到全局 wrapper。wrapper 会自动接入 shared build-queue daemon，把验证型 `xcodebuild` 串行排队执行，统一使用 Xcode 系统 DerivedData（`~/Library/Developer/Xcode/DerivedData`），并默认只把 `verification-report.json` 打印给 Agent。
- 推荐执行顺序：先 `explorer -> builder -> reporter`，再按需激活 `pm` / `tester`。
- 默认先做任务分型：`doc-only` / `rule-only` / `code-small` / `code-medium` / `code-risky`，再映射到 `lite` / `standard` / `full`。
- 配置映射：
  - 图示 `AGENTS.md` 对应仓库根 `AGENTS.md`
  - 图示 `skills/*/SKILL.md` 对应本仓库全部 skills（含按需触发的低频技能）
  - 图示 `config.toml` 对应本仓库 `config/codex/codex.shared.toml`
  - 截至 2026-06-15 的共享 Codex 基线：`model = "gpt-5.5"`、`image_model = "gpt-image-2"`、`features.multi_agent = true`、`[agents] max_threads/max_depth`，以及默认 `model_reasoning_effort = "medium"` / `plan_mode_reasoning_effort = "medium"`；安装脚本会同步到 `~/.codex/config.toml`。`image_model` 是本仓共享配置基线，用于对齐 Codex 内置 image generation 使用 `gpt-image-2` 的行为，不把它表述为官方 config reference 已公开稳定字段。
  - 本仓 shared config 会禁用 `openai-curated`、`openai-curated-remote`、`openai-primary-runtime`、`openai-bundled` 等插件来源；如需恢复某个插件，需显式把对应 `[plugins."<id>"] enabled = true` 改回。

快速发任务模板：

```text
请使用 codex-subagent-orchestration 处理这个 iOS 任务。
默认按主 Agent 串行承担 explorer -> builder -> reporter 逻辑角色；
实现链路收口必须启动独立 reviewer subAgent 执行 code-review，不能由实现 Agent 自审；
仅当我显式要求 subAgent / parallel agent / delegation、prompt 明确授权或风险需要时，才为 coder / tester 调用 ~/.codex/agents 原生 subAgent；
若边界不清激活 pm，若需要测试面或失败归因激活 tester。
目标：<需求>
上下文：<目录/文件/报错>
约束：最小改动；先探索再实施；失败先修复再汇报。
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
- 如本次修改涉及私有库 / 私有组件，主项目默认必须切回或保持本地 `:path` 私有库依赖；严格顺序是：先把主项目切回或保持在本地 `:path` 私有库依赖 -> 再修改本地私有库源码仓 -> 最后回到主项目基于该本地依赖做开发与验证；私有库仓内自测不能替代主项目验证。未收到明确指令前，不得把验证基线切到线上版本化依赖或 `Pods/` vendored snapshot。
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
- 默认路由：`skills/html-docs`，并按 `references/tasklist-template.md` 执行任务清单样式。
- 状态标识统一：`√` 表示已完成，`□` 表示未完成 / 待办；建议用 `.check-mark.done` / `.check-mark.todo` 样式呈现。
- 样式基线：Notion-light + SidusLinkPro checklist（Hero 元信息独立行、chips、状态图例、指标卡、固定表格与 callout）。
- 文档治理：顶部使用绝对日期（创建/更新），实施后必须回写进度，保持文档与代码状态一致。

## 默认收口与可选证据验证

- 默认完成标准：定向验证或必要验证通过，且独立 reviewer subAgent 执行的 `code-review` 无 blocking findings。
- 涉及代码改动时，`ios-verification` 默认只执行**最窄定向单测**：优先 `-only-testing` 到单个 test case / test class，其次最小受影响 test file / bundle；真机 / 模拟器验证不属于默认验证执行面。
- 如果当前改动不适合运行测试，验证阶段必须给出 `no_test_reason` 与替代验证依据，然后交给独立 reviewer subAgent 执行 `code-review`。
- 如果当前改动没有可低成本执行的单测路径，验证阶段必须给出 `no_test_reason` 与 `suggested_validation`，且不要自动升级到真机 / 模拟器验证。
- `code-review` 默认审查本次任务全量差异及本次修改带来的直接影响面，包含 staged、unstaged、untracked 与任务起点基线之后的相关提交；用于实现链路收口时必须由未参与实现的独立 reviewer subAgent 执行。
- `ios-verification` 不再把完整项目环境验证作为所有 Apple Xcode 项目改动的强制收尾，仅在按需补强时执行。
- 执行可选 `xcodebuild` 验证时，仍必须在目标项目根目录的项目环境执行，不能把 sandbox 结果当作完整项目环境证据。
- 本地所有 `xcodebuild` 参数探测与验证需求（含 `-list` / `-showdestinations` / build/test）默认都在非沙盒项目环境通过 wrapper 执行：由主 Agent 使用 `functions.exec_command` 启动目标项目根目录的 `codex_verify.sh`，若项目未接入则回退到本机 `~/.codex/bin/codex_verify`。不得直接调用 `xcodebuild` 二进制，也不要让多个 Agent 各自裸跑 `xcodebuild`；wrapper 会自动接入 shared build-queue daemon，把验证型 `xcodebuild` 串行排队执行，并统一使用 Xcode 系统 DerivedData。
- 验证输出默认遵守 **脚本先裁剪，Agent 后判断**：wrapper / digest 脚本先生成 `verification-report.json`、`diagnostics.json`、`build-summary.txt`，Agent 默认只读取 `verification-report.json`；只有 `needs_raw_log=true` 或用户显式要求时，才读取 raw log 的定向片段。若必须实时查看完整日志，显式设置 `CODEX_VERIFY_STREAM_LOG=1`。
- 如果 `--queue-status`、wrapper 输出或错误信息表明已有其他 Agent 正在执行验证，当前 Agent 应等待 shared build-queue daemon 完成当前任务，或把本轮标记为 `env_issue` / `blocked`；不要为了绕过同一个 `build.db` 锁而切到单独 `-derivedDataPath` 跑同一组最窄测试。
- 可选完整验证继续遵守既有 Xcode 约束：优先 `.xcworkspace`，优先绑定了单元测试 `*Tests` target / bundle 的 scheme，iOS 路径默认优先已连接真机。验证链路由 wrapper 提交到 daemon；可通过 `codex_verify.sh --queue-status` 查看当前 active job 与 pending jobs。非验证型构建讨论仍以 Xcode 系统 DerivedData 为基线；旧 `XCODE_DERIVED_DATA_*` / `CODEX_DERIVED_DATA_SLOT` 公开配置不再支持。
- 实现链路默认三步收口：`实现 skill -> 定向验证 / no_test_reason -> reviewer subAgent(code-review)`。
- 未执行可选完整验证时，交付应说明已执行的定向验证/必要验证、`code-review` 结论与残余风险。

## 多 Agent 编排锚点

- `codex-subagent-orchestration` 是默认的 iOS 主 Skill 入口；实现、调试、性能、验证、Apple 文档与可选证据验证都应先经过它，再内部路由到对应模块。所有代码实施统一转入 `ios-feature-implementation` 的内部模式，不再要求用户手动选择 SwiftUI / UIKit / Swift Expert 实施 Skill。
- 编排默认按 `lite` / `standard` / `full` 三档选择角色。
- 默认先按任务分型器分类，再决定角色激活矩阵（最小集合：`explorer + builder + reporter`）。
- 默认进入编排入口不等于默认实际 spawn coder / tester subAgent；只有用户显式要求 subAgent / parallel agent / delegation、当前 prompt 明确授权或风险需要时，主 Agent 才可按 `lite` / `standard` / `full` 调用 coder / tester 原生 subAgent 工具。未显式授权时 coder / tester 可由主 Agent 串行承担，但实现链路的 `code-review` 必须交给独立 reviewer subAgent。
- 即使 coder / tester 未使用原生 subAgent 或因工具/策略/写集限制回到主 Agent 串行执行，实现链路仍必须保留 `ios-verification` 与独立 reviewer subAgent `code-review`；reviewer subAgent 不可用时只能报告 blocked / pending review。
- 计划模式（`proposed_plan`）输出，只要是实现链路也必须显式包含独立 reviewer subAgent 执行的 `code-review` 审查步骤。
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
python3 scripts/validate_codex_agent_templates.py config/codex/templates/agents
python3 scripts/lint_subagent_orchestration_policy.py
python3 scripts/lint_workflow_contract_policy.py
python3 scripts/lint_harness_workflow_policy.py
python3 scripts/lint_verify_ios_build_policy.py
git diff --check
```

## 贡献

欢迎补充更多 Apple 平台相关技能，完善文档与案例。
