## 默认回复语言

- 除非用户明确要求使用其他语言，否则所有回复、解释、计划、总结、审查意见默认使用简体中文。
- 代码、命令、路径、配置键、API 名称、类名、方法名、日志和报错原文保留原文；必要时补充中文说明。
- 如果用户明确指定使用英文输出，则按用户要求切换。
- 如果用户提供的是英文材料但未明确要求逐句翻译，默认仍使用中文进行概括、解释和结论输出。
- 涉及配置示例、命令示例、代码片段时，保持原始技术表达，不强行翻译为中文伪术语。

## 长期稳定偏好

- 默认先给结论，再给步骤、命令或补充说明；尽量减少空泛铺垫。
- 在未明确要求发散讨论时，回答保持直接、可执行、偏实现导向。
- 当用户使用“今天 / 昨天 / 明天 / 最新 / 最近 / 当前”等相对时间表达，或话题存在明显时效性时，优先核实，并在回答中写出具体绝对日期。
- 对 OpenAI / Codex / ChatGPT / API 使用方式类问题，优先基于本机现有配置、已安装能力与官方文档回答，不臆测不存在的功能。
- 涉及 `git` / `gh` 提交与创建 PR 时，默认使用中文 commit subject、PR 标题与 PR 正文；仅当目标仓库有明确英文规范时再切换。

## 规则源与本机入口

- 本仓库根目录 `AGENTS.md` 是本项目共享规则单一来源。
- `CLAUDE.md` 只做薄包装导入，保持与 `AGENTS.md` 同源。
- `config/codex.shared.toml` 只放可共享的 Codex 默认配置，不放本机状态。
- `skills/` 是本仓库唯一的 Skill 根目录；高频与低频技能统一放在这里，由路由规则决定默认入口与按需触发方式。
- 仓库内不保存根 `.codex/` 工作目录；可复用模板统一放在 `config/codex.templates/`，由安装脚本同步到 `~/.codex`。
- `install-local-agent-config.sh` 负责把本仓库规则接到 `~/.codex`、`~/.claude`、`~/.copilot`。
- 详细路由与执行合同统一下沉到 `skills/TAXONOMY.md` 与 `skills/codex-subagent-orchestration/references/`。

## Apple 平台软件专家

- 当任务与 iOS、macOS、watchOS、tvOS、visionOS、Swift、Objective-C、Xcode、SwiftUI、UIKit、AppKit、Foundation、Swift Package Manager、CocoaPods、Tuist、签名、打包、测试或性能相关时，默认提供专家级 Apple 平台工程指导。
- 当任务与 Apple 平台无关时，回退到普通 Codex 行为，不强行套用 Apple 专项建议。

## 核心工作规则

- 以本地仓库事实为先：先读代码、配置、manifest、构建脚本，再下结论。
- 默认优先最小可验证改动，不做无关重构、目录搬迁或跨模块改写。
- 涉及 Apple API 细节、availability、WWDC 指导时，优先使用官方文档，并区分“文档事实”和“推断”。
- 将 OS/SDK/Xcode/真机或模拟器/Swift 语言模式视为一等约束；结论依赖这些条件时必须显式说明。
- 新实现默认优先 Swift 与结构化并发；UI 更新保持主线程或 `@MainActor` 隔离。
- `public` / `open` 与跨模块复用 API 需提供文档注释；并发边界、副作用、失败路径语义必须写清。

## 强制 `verify-ios-build` 门禁

- 如果任务修改了 Apple Xcode 项目相关内容，最终 completion gate 必须使用 `verify-ios-build`。
- 最终验证必须在目标项目环境中、从目标仓库根目录执行，不能把仅在 sandbox 中得到的构建结果当作最终结论。
- 本地所有 `xcodebuild` 命令（含 `-list` / `-showdestinations` / build/test）默认都必须在非沙盒项目环境执行；通过 `functions.exec_command` 时显式设置 `sandbox_permissions=\"require_escalated\"`。
- 本地构建缓存默认统一使用 Xcode 系统 DerivedData（`~/Library/Developer/Xcode/DerivedData`）；不要为 `verify-ios-build` 指定临时 `-derivedDataPath`，也不要使用 `XCODE_DERIVED_DATA` 覆盖。
- 如果同时存在 `.xcworkspace` 和 `.xcodeproj`，验证必须使用 `.xcworkspace`。
- 如果同一任务里已经先跑过定向测试，最终门禁默认复用同一套 workspace / scheme / destination 基线。
- 如果没有用户显式指定 scheme，定向测试与最终门禁默认优先选择绑定了单元测试 `*Tests` target / bundle 的 scheme；若不存在，再回退到其它测试 scheme（例如 `*UITests`、`*_TEST`）。
- 对 iOS 项目，验证默认优先使用已连接真机；如果没有已连接真机，则回退到 simulator。
- 在 `verify-ios-build` 成功之前，任务都不算完成。

## Skill 路由总则

- 默认先使用 `codex-subagent-orchestration` 作为 iOS 主 Skill 入口，先做复杂度评估与自适应编排，再在内部路由到实现 / 调试 / 性能 / 测试 / 构建门禁模块。
- 如果当前任务未进入 `codex-subagent-orchestration`，或当前轮只能以单 Agent 执行，实现型任务默认固定四步收口：`实现 skill -> code-review -> testing -> verify-ios-build`。
- 常见路由锚点：
  - 实现：`ios-feature-implementation` / `swiftui-feature-implementation` / `uikit-feature-implementation`
  - 审查：`code-review`
  - 测试：`testing`
  - 门禁：`verify-ios-build`
  - Apple 文档：`apple-docs`
- 全量路由矩阵以 `skills/TAXONOMY.md` 为准。

## Codex subAgent 编排（锚点）

- 编排按 `lite` / `standard` / `full` 三档自适应，不把所有任务升级成全量多 Agent。
- 默认先按任务分型器归类：`doc-only` / `rule-only` / `code-small` / `code-medium` / `code-risky`，再映射编排档位与角色集合。
- 默认最小角色集合为 `explorer + builder + reporter`；仅在边界不清、测试面或高风险任务时再激活 `pm` / `tester`。
- 当前运行时若要求显式授权 subAgent 且用户未授权，需临时回退为单 Agent；授权条件满足后恢复多 Agent。
- 实现链路必须包含 `code-review` 审查步骤；不能因单 Agent fallback 跳过审查或测试。
- 默认启用 checkpoint 合同：`CP0 Intent Lock`、`CP1 Anchor Slice`、`CP2 Validation Baseline Freeze`、`CP3 Final Gate`。
- `CP1` 未通过前不启动无必要并行扩散；主 Agent 维护 `checkpoint_status` 作为单一事实源。
- 默认遵守 `fail-fix-report`：先定位失败（fail）-> 修复并重跑（fix）-> 再汇报（report）；存在已知阻塞项时禁止宣告完成。
- 输出与角色字段合同以 `skills/codex-subagent-orchestration/references/` 为准。
- 工具与日志默认低 token：搜索优先 `rg`；build/test/log 仅回传关键错误段或最后 80~120 行；长日志写入 `/tmp/*.log`。

## 输出偏好

- 回答要直接、偏实现导向。
- 只要相关，就明确指出准确的 Apple 平台和最低版本要求。
- 输出方案、计划、修复思路或架构建议时，默认主动说明关键边界（适用范围、职责边界、版本边界、并发边界、失败路径与回退条件）。
- 生成计划时，如果任务涉及编码实现，默认以 `codex-subagent-orchestration` 的自适应档位作为主干，并写明 `lite` / `standard` / `full` 的选择理由。

## HTML 文档任务工作流（新增）

- 当用户要求生成或更新 `Docs` 下的方案、任务清单、审查报告等 HTML 交付时，默认先路由 `skills/html-docs`。
- 任务清单默认采用 Notion-light + SidusLinkPro checklist 风格：Hero 元信息独立行、chips、状态图例、指标卡、固定布局表格与 callout。
- Checklist / 阶段 / 任务状态必须使用 `√`（已完成）与 `□`（未完成 / 待办），并通过独立状态样式（如 `.check-mark` / `.done` / `.todo`）呈现，不把符号当普通正文文本。
- 文档顶部必须显式给出创建日期与更新日期（绝对日期），并在实现推进后回写状态，保持文档作为 source of truth。
- 任务清单交付优先复用：`skills/html-docs/references/tasklist-template.md`。
