# AGENTS.md

## 目标与语言

- 以尽量低的 token 成本完成高质量 iOS / Apple 平台工程任务；默认优先级：正确性 > 验证效率 > token 效率 > 输出完整度。
- 除非用户明确要求其他语言，否则回复、计划、总结和审查意见使用简体中文；代码、命令、路径、API 名称和报错原文保留原文。
- 遇到“今天 / 最新 / 当前”等相对时间或时效性事实，先核实并在回答中写出具体日期。

## 基本原则

- 以本地仓库事实为先：先读代码、配置、脚本和现有 Skill，再下结论。
- 不得回滚用户或其他 Agent 未授权的改动；默认做最小可验证改动，不做无关重构、目录搬迁或跨模块改写。
- 优先更新最接近约束来源的文件，避免同一规则散落在多个入口重复维护。
- 修复 / 实现类任务不依赖手动 Plan 模式；允许先做最小只读定位，但首次写文件或 patch 前必须输出简短计划；超小 doc-only / rule-only 改动也至少用一句话锁定计划。
- 使用任何 Skill 前，必须先输出 `>>> Skill: <skill-name>` 声明当前路由。
- 涉及 Apple API、availability、WWDC 或 OpenAI / Codex 官方行为时，优先使用官方文档，并区分文档事实与推断。

## 路由与收口

- `doc-only` / `rule-only`：直接修改目标文档或规则文件，并检查相关引用是否一致。
- 正式 HTML 方案、PRD、评审、报告、任务清单、接口说明或 handoff 统一路由到 `html-docs`。
- iOS 开发任务默认先进入 `codex-subagent-orchestration`，由任务分型器归类为 `doc-only` / `rule-only` / `code-small` / `code-medium` / `code-risky`；默认逻辑角色为 `explorer + builder + reporter`。实现归 `ios-feature-implementation`，验证归 `ios-verification`，审查归 `code-review`，细分边界以 `skills/TAXONOMY.md` 为准。
- 除 `code-review` 必须由独立 reviewer subAgent 执行外，本仓不限制其它 subAgent 角色拆分；实现型任务默认三步收口：实现 Skill → 定向验证 / `no_test_reason` → 独立 reviewer subAgent 执行 `code-review`；reviewer 不可用时只能报告 blocked / pending review。
- 审查型任务默认交给独立 reviewer subAgent；没有阻塞项时明确说明 `阻塞问题：无`，并指出剩余风险或验证缺口。
- 高风险才升级完整 build、Archive、真机验证或 FULL verification；不要把这些当默认收尾。
- 默认遵守 checkpoint 合同：`CP0 Intent Lock`、`CP1 Anchor Slice`、`CP2 Validation Baseline Freeze`、`CP3 Final Gate`；主 Agent 维护 `checkpoint_status`，并按 `fail-fix-report` 先定位失败、修复并重跑，最多回环同类问题 2 次。

## 代码智能 / CodeGraph

- 代码理解、排查并修复、影响面分析、重构或 PR 审查任务，可在手工大范围搜索前按需使用 CodeGraph 缩小搜索面。
- CodeGraph 查询只作为低 token 导航和影响面证据；修改前仍必须回到当前 worktree 的源码、配置、日志或测试证据确认。
- 默认低 token 路径：`rg` / `git grep` → 精准文件切片 → 少量 `codegraph_search` → 仅在跨文件关系仍不清楚时升级 `codegraph_explore` / `codegraph_node`。
- 使用 CodeGraph 时避免把大输出反复回灌上下文；优先提取符号、文件路径、调用关系和最小必要行号。

## Apple 平台工程规则

- 将 OS / SDK / Xcode / Swift 语言模式 / 真机或模拟器视为一等约束；结论依赖这些条件时必须显式说明。
- 新实现默认优先 Swift 与结构化并发；UI 更新保持主线程或 `@MainActor` 隔离。
- 新增或改动 `public` / `open` / 跨模块 API 时补中文 `///`，写清并发边界、副作用和失败语义；复杂业务分支、兼容逻辑、降级路径补中文 why 注释，避免噪音注释。
- 新增 `.swift` / `.h` / `.m` / `.mm` 且项目要求文件头时，参考同目录格式；`Created by` 必须使用 `whoami` 或 `id -un` 的真实本机用户名，不写 `Codex`、字面量 `$(whoami)` 或占位符，日期默认 `YYYY/M/D`。
- 涉及 CocoaPods / 私有组件联调时，先检查 `Podfile`、`Podfile.lock`、`Pods/Manifest.lock`；本地 `:path` Pod 默认修改真实组件仓，不改 `Pods/` 快照。
- 私有库 / 私有组件改动时，主项目默认必须保持本地 `:path` 私有库依赖；私有库仓内自测不能替代主项目验证；验证通过后默认先保持当前本地 `:path` 私有库依赖状态。未获明确授权前，不切回线上依赖、不提交本地 `:path` 依赖文件。

## 验证规则

- 默认验证等级：`NONE → LINT → AFFECTED_TESTS → BUILD → UI_SMOKE → FULL`，选择覆盖风险的最低等级。
- 代码改动优先最窄定向验证：单个 test case / class → 最小受影响 test file / bundle；无低成本测试时给出 `no_test_reason` 与 `suggested_validation`。
- 验证链路优先读取结构化证据：`verification-report.json`、`diagnostics.json`、`build-summary.txt` / `test-summary.json`；不要默认读取完整 raw log 或 `.xcresult` dump。
- 同时存在 `.xcworkspace` 和 `.xcodeproj` 时，验证优先 `.xcworkspace`；优先选择绑定 `*Tests` target / bundle 的 scheme；iOS 默认优先已连接真机，无真机再回退 simulator。
- 本地执行验证型 `xcodebuild`（含 `-list` / `-showdestinations` / build/test）必须由主 Agent 使用 `functions.exec_command` + `sandbox_permissions="require_escalated"` 在目标项目根目录的非沙盒项目环境启动 `./codex_verify.sh`，否则用 `~/.codex/bin/codex_verify`，并接入 shared build-queue daemon；可用 `--queue-status` 查看队列；不得直接调用 `xcodebuild` 二进制。
- 验证证据必须来自目标项目根目录的项目环境；sandbox 中的 `xcodebuild` / wrapper 结果只能作为环境诊断线索，不得作为完整项目环境证据；需要完整项目环境证据时继续使用 Xcode 系统 DerivedData；不得为了绕过同一个 `build.db` 锁而切到单独 `-derivedDataPath` 跑同一组验证。

## Skill 与规则维护

- 修改 `skills/*/SKILL.md` 默认遵守 `docs/skills/skill-schema-v1.md`；影响职责边界、入口建议或路由关系时同步更新 `skills/TAXONOMY.md`。
- 可重复、确定性强、输出量大的本地处理优先沉淀到 `skills/<skill>/scripts/`；`references/` 只放 schema、判读说明和示例报告。
- 新增或修改 Skill 后默认运行或建议运行 `python3 scripts/lint_skill_schema.py`；需要更严格校验时使用 `--strict`。

## 完成标准

- `doc-only` / `rule-only`：内容已更新，交叉引用一致，无多余改动。
- 实现任务：已完成定向测试或必要验证，且独立 reviewer subAgent 的 `code-review` 无 `阻塞问题`；无法测试时已说明 `no_test_reason` 和替代验证建议。
- 最终回复默认包含：改了什么、如何验证、已知风险或后续动作。
