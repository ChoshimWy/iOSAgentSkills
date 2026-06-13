# AGENTS.md

本文件是 `iOSAgentSkills` 仓库的全局规则中心，也是 Codex / Claude Code / Copilot 等本地 Agent 的共享行为基线。

## Mission

- 以最低可行 token 成本完成高质量 iOS / Apple 平台工程任务。
- 默认优先级：正确性 > 验证效率 > token 效率 > 输出完整度。
- 默认采用最小可验证改动，不做无关重构、目录搬迁或跨模块改写。
- 涉及代码改动时，默认收口为：定向测试或必要验证通过，且 `code-review` 无 blocking findings。

## 默认回复语言

- 除非用户明确要求其他语言，否则所有回复、解释、计划、总结、审查意见默认使用简体中文。
- 代码、命令、路径、配置键、API 名称、类名、方法名、日志和报错原文保留原文；必要时补充中文说明。
- 如果用户明确指定使用英文输出，则按用户要求切换。
- 如果用户提供英文材料但未明确要求逐句翻译，默认仍使用中文概括、解释和输出结论。
- 涉及配置示例、命令示例、代码片段时，保持原始技术表达，不强行翻译为中文伪术语。

## 长期稳定偏好

- 默认先给结论，再给步骤、命令或补充说明。
- 在未明确要求发散讨论时，回答保持直接、可执行、偏实现导向。
- 当用户使用“今天 / 昨天 / 明天 / 最新 / 最近 / 当前”等相对时间表达，或话题存在明显时效性时，优先核实，并在回答中写出具体绝对日期。
- 对 OpenAI / Codex / ChatGPT / API 使用方式类问题，优先基于本机现有配置、已安装能力与官方文档回答，不臆测不存在的功能。
- 涉及 `git` / `gh` 提交与创建 PR 时，默认使用中文 commit subject、PR 标题与 PR 正文；仅当目标仓库有明确英文规范时再切换。commit subject 强制单行，不允许多行正文或脚注。

## 规则源与本机入口

- 本仓库根目录 `AGENTS.md` 是本项目共享规则单一来源。
- `CLAUDE.md` 做薄包装导入，保持与 `AGENTS.md` 同源，并附加 Claude Code 运行时编排指令；Codex 用户不受其影响。
- `config/codex/codex.shared.toml` 只放可共享的 Codex 默认配置，不放本机状态。
- 共享 Codex 基线使用 `model = "gpt-5.5"`、`image_model = "gpt-image-2"`、`features.multi_agent = true` 与 `[agents] max_threads/max_depth`。
- `skills/` 是本仓库唯一的 Skill 根目录；高频与低频技能统一放在这里，由路由规则决定默认入口与按需触发方式。
- 仓库内不保存根 `.codex/` 工作目录；可复用模板统一放在 `config/codex/templates/`，由安装脚本同步到 `~/.codex`。
- `install-local-agent-config.sh` 负责把本仓库规则接到 `~/.codex`、`~/.claude`、`~/.copilot`。
- 详细路由矩阵以 `skills/TAXONOMY.md` 为准。
- Skill 结构规范以 `docs/skills/skill-schema-v1.md` 为准。

## Apple 平台专家模式

- 当任务与 iOS、macOS、watchOS、tvOS、visionOS、Swift、Objective-C、Xcode、SwiftUI、UIKit、AppKit、Foundation、Swift Package Manager、CocoaPods、Tuist、签名、打包、测试或性能相关时，默认提供专家级 Apple 平台工程指导。
- 当任务与 Apple 平台无关时，回退到普通 Codex 行为，不强行套用 Apple 专项建议。
- 将 OS / SDK / Xcode / 真机或模拟器 / Swift 语言模式视为一等约束；结论依赖这些条件时必须显式说明。
- 涉及 Apple API 细节、availability、WWDC 指导时，优先使用官方文档，并区分“文档事实”和“推断”。

## Core Engineering Rules

- 以本地仓库事实为先：先读代码、配置、manifest、构建脚本，再下结论。
- 新实现默认优先 Swift 与结构化并发；UI 更新保持主线程或 `@MainActor` 隔离。
- `public` / `open` 与跨模块复用 API 需提供文档注释；并发边界、副作用、失败路径语义必须写清。
- 新增 `.swift` / `.h` / `.m` / `.mm` 文件且项目要求文件头时，`Created by` 必须使用本机用户名称（`whoami` 输出），不要写 `Codex`；日期默认 `YYYY/M/D`。
- 不得回滚用户或其他 Agent 的未授权改动。

## Private Pod / Local Component Policy

- 涉及 CocoaPods / 私有组件联调时，先查目标工程 `Podfile` / `Podfile.lock` / `Pods/Manifest.lock` 判断是否为本地 `:path` Pod。
- 若是本地 `:path` Pod，默认修改组件源码仓，不修改 `Pods/` 下的副本快照。
- 对本地 `:path` Pod / 私有组件，`Pods/<LibraryName>` 默认属于禁止改动范围；除非用户明确要求修改 vendored snapshot 并说明原因，否则不得把 `Pods/` 副本当作真实源码位置。
- 如本次修改涉及私有库 / 私有组件，主项目默认必须切回或保持本地 `:path` 私有库依赖进行开发与验证；未收到明确指令前，不得把验证基线切到线上版本化依赖或 `Pods/` vendored snapshot。
- 即使本地联调阶段允许主项目临时切到本地 `:path` 私有库依赖，`git commit` 前也必须恢复到可提交的远端/版本化依赖状态；禁止把包含本地 `:path` 私有库引用的 `Podfile` / `Podfile.lock` / `Pods/Manifest.lock` 提交进仓库。

## Verification Strategy

默认验证等级从低到高：

```text
NONE
↓
LINT
↓
AFFECTED_TESTS
↓
BUILD
↓
UI_SMOKE
↓
FULL
```

规则：

- 默认选择能覆盖当前风险的最低验证等级。
- 涉及代码改动时，`testing` 默认只执行最窄定向单测：优先 `-only-testing` 到单个 test case / test class，其次最小受影响 test file / bundle。
- 真机 / 模拟器验证不属于默认 testing 执行面。
- 如果当前改动不适合运行测试，`testing` 阶段必须给出 `no_test_reason` 与替代验证依据，然后进入 `code-review`。
- 如果当前改动没有可低成本执行的单测路径，`testing` 阶段必须给出 `no_test_reason` 与 `suggested_validation`，且不要自动升级到真机 / 模拟器验证。
- `final-evidence-gate` 与 `verify-ios-build` 不是所有 Apple Xcode 项目改动的强制收尾，仅作为按需补强验证：用户显式要求、发布前自检、或主 Agent 判断高风险时才使用。
- 禁止默认全量测试、默认完整 build、默认 Archive、默认 FULL verification。
- 高风险改动包括：工程配置、依赖基线、签名/entitlements、plist/capabilities、资源打包、target membership、scheme/xctestplan、私有库集成、release/merge confidence。

## Build Queue Policy

- 验证型 `xcodebuild` 必须通过 wrapper 入口执行：优先目标项目根目录 `./codex_verify.sh`，若项目未接入则回退到 `~/.codex/bin/codex_verify`。
- wrapper 必须接入 shared build-queue daemon，把验证型 `xcodebuild` 串行排队执行，并统一使用 Xcode 系统 DerivedData：`~/Library/Developer/Xcode/DerivedData`。
- 可通过 `./codex_verify.sh --queue-status` 或 `~/.codex/bin/codex_verify --queue-status` 查看 daemon 当前 active job 与 pending jobs。
- 禁止在验证任务中绕过 wrapper 直接运行 `xcodebuild build` / `xcodebuild test`。
- 本地执行非验证型 Xcode 查询（如讨论 Build Settings、`-list`、`-showdestinations`）仍必须明确项目环境与目的，不得把查询结果伪装成最终验证证据。
- 旧 `XCODE_DERIVED_DATA_*` / `CODEX_DERIVED_DATA_SLOT` 公开配置不再支持。

## Xcode / iOS Baseline Rules

- 如果同时存在 `.xcworkspace` 和 `.xcodeproj`，验证优先使用 `.xcworkspace`。
- 优先选择绑定单元测试 `*Tests` target / bundle 的 scheme。
- iOS 验证默认优先已连接真机；找不到连接中的真机时再回退 simulator。
- 验证证据必须来自目标项目根目录的项目环境；sandbox 中的构建结果不能作为完整项目环境证据。
- 若同一任务已冻结 workspace / scheme / destination baseline，后续 testing / final-evidence-gate / verify-ios-build 默认复用该 baseline，除非明确说明切换理由。

## Token Budget Policy

默认禁止：

- 读取完整 `build.log`。
- dump 完整 `.xcresult` JSON。
- 递归扫描 `DerivedData`。
- 全量读取 `Pods/`。
- 粘贴大段 diff、完整控制台日志或长文件。

默认优先：

- `diagnostics.json`。
- `build-summary.txt`。
- `test-summary.json`。
- `xcresult-summary.json`。
- `rg` / 精确文件读取。
- 关键错误段或最后 80~120 行相关日志。
- 对长日志先写入文件，再摘要分析。

## Multi-Agent Strategy

默认按任务复杂度选择编排档位，不把所有任务升级为 full multi-agent。

```text
lite      = planner/main + implementer
standard  = planner/main + implementer + reviewer
full      = planner/main + implementer + reviewer + tester/verifier
```

规则：

- 默认先由 `codex-subagent-orchestration` 判断任务类型：`doc-only` / `rule-only` / `code-small` / `code-medium` / `code-risky`。
- `CP0 Intent Lock`、`CP1 Anchor Slice`、`CP2 Validation Baseline Freeze`、`CP3 Final Gate` 是默认 checkpoint。
- `CP1` 未通过前不启动无必要并行扩散；主 Agent 维护 `checkpoint_status` 作为单一事实源。
- 默认遵守 `fail-fix-report`：先定位失败（fail）-> 修复并重跑（fix）-> 再汇报（report）；存在已知阻塞项时禁止宣告完成。
- 实现链路必须包含 `testing/targeted validation` 与 `code-review`；不能因单 Agent fallback 跳过审查或测试影响说明。
- 多 Agent 不得共享不安全写集，不得并行修改同一路径或并发执行验证型 `xcodebuild`。

## Skill Routing Policy

- 使用任何 Skill 前，必须先输出 `>>> Skill: <skill-name>` 声明即将使用的 Skill。
- 默认先使用 `codex-subagent-orchestration` 作为 iOS 主 Skill 入口，先做复杂度评估与自适应编排，再在内部路由到实现 / 调试 / 性能 / 测试 / 审查 / 按需验证模块。
- 如果当前任务未进入 `codex-subagent-orchestration`，或当前轮只能以单 Agent 执行，实现型任务默认三步收口：`实现 Skill -> testing/定向验证 -> code-review`；`final-evidence-gate` / `verify-ios-build` 仅按需升级。
- 常见路由锚点：
  - 实现：`ios-feature-implementation` / `swiftui-feature-implementation` / `uikit-feature-implementation`
  - SDK 架构：`ios-sdk-architecture`
  - 进阶 Swift：`swift-expert`
  - 审查：`code-review`
  - 测试：`testing`
  - 可选验证：`final-evidence-gate` / `verify-ios-build`
  - Apple 文档：`apple-docs`
  - 文档交付：`html-docs`
- 全量路由矩阵以 `skills/TAXONOMY.md` 为准。

## Skill Contract Policy

所有 `skills/*/SKILL.md` 默认遵守 `docs/skills/skill-schema-v1.md`。

必须章节：

- `## Purpose`
- `## Agent Rules`
- `## Outputs`
- `## Exit Conditions`

主链路 Skill 还应包含：

- `## Inputs`
- `## Escalation Rules`
- `## Relationship to Other Skills`

输出合同必须尽量包含：

- `status`
- `changed_files` 或 `output_files`
- `summary`
- `known_risks`
- `next_action`

新增或修改 Skill 后，默认运行或建议运行：

```bash
python scripts/lint_skill_schema.py
```

严格模式：

```bash
python scripts/lint_skill_schema.py --strict
```

## SDK Architecture Baseline

SDK / Framework 默认架构方向：

```text
Public API Layer
↓
Feature Layer
↓
Core Layer
↓
Platform Layer
```

规则：

- 默认 `internal`，仅必要类型暴露 `public` / `open`。
- 入口类负责初始化、生命周期和配置校验，不承载业务细节。
- Public API 必须说明输入、输出、错误、并发、availability 与副作用语义。
- 分发优先 SPM；二进制分发使用 XCFramework；版本遵循 SemVer。
- breaking change 必须通过显式版本策略表达。

## HTML 文档任务工作流

- 当用户要求生成或更新 `Docs` 下的方案、任务清单、审查报告等 HTML 交付时，默认先路由 `html-docs`。
- 任务清单默认采用 Notion-light + SidusLinkPro checklist 风格：Hero 元信息独立行、chips、状态图例、指标卡、固定布局表格与 callout。
- Checklist / 阶段 / 任务状态必须使用 `√`（已完成）与 `□`（未完成 / 待办），并通过独立状态样式（如 `.check-mark` / `.done` / `.todo`）呈现，不把符号当普通正文文本。
- 文档顶部必须显式给出创建日期与更新日期（绝对日期），并在实现推进后回写状态，保持文档作为 source of truth。
- 任务清单交付优先复用：`skills/html-docs/references/tasklist-template.md`。

## 输出偏好

- 回答要直接、偏实现导向。
- 只要相关，就明确指出准确的 Apple 平台和最低版本要求。
- 输出方案、计划、修复思路或架构建议时，默认主动说明关键边界：适用范围、职责边界、版本边界、并发边界、失败路径与回退条件。
- 生成计划时，如果任务涉及编码实现，默认以 `codex-subagent-orchestration` 的自适应档位作为主干，并写明 `lite` / `standard` / `full` 的选择理由。
