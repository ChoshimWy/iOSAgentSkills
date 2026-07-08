# 业务 Skill 分类索引（single-entry iOS core）

本文覆盖本仓库 `skills/` 下的全部 skills。用户默认入口只有 `codex-subagent-orchestration`；低频技能与高频技能统一保存在同一根目录下。
根级 `AGENTS.md` 只保留仓库总纲；本文件承接默认入口、路由与验证升级策略。

## 分类原则

- `Core Implementation`：只有一个真正的 iOS 代码实施 Skill：`ios-feature-implementation`。它内部再按模式细分业务、SwiftUI、Liquid Glass、UIKit、混合 UI、高级 Swift、重构、SDK 契约 / 架构和测试代码编写。
- `Automation / Build / Validation`：设备自动化、构建配置与统一验证技能。
- `Diagnostics`：发现问题、分析风险、定位根因的技能。
- `Additional Skills`：按需触发的低频技能；与 core skills 共用同一目录，只通过路由策略区分。

## 严格路由总则

- iOS 开发任务默认先进入 `codex-subagent-orchestration`；由主入口决定单 Agent 还是 `lite` / `standard` / `full` 编排，再按需路由到统一实施、统一验证、审查、调试、性能与构建模块。
- 修复 / 实现任务即使未手动进入 Plan 模式，也必须在写入前完成 CP0 最小计划；允许先做只读定位，但禁止从代码查找直接进入实现。
- 默认完成标准：定向测试或必要验证通过，且独立 reviewer subAgent 执行的 `code-review` 无 `阻塞问题`。
- 测试代码编写、Mock / Stub / Spy / Fake、fixture、Page Object 与最小 testability seam 默认归入 `ios-feature-implementation` 的 `test-implementation` mode。
- 涉及代码改动时，验证阶段默认只执行**最窄定向单测**：优先 `-only-testing` 到单个 test case / test class，其次最小受影响 test file / bundle；真机 / 模拟器验证不属于默认验证执行面。
- 如果当前改动不适合运行测试，验证阶段必须给出 `no_test_reason` 与替代验证依据，然后交给独立 reviewer subAgent 执行 `code-review`。
- 如果当前改动没有可低成本执行的单测路径，验证阶段必须给出 `no_test_reason` 与 `suggested_validation`，且不要自动升级到真机 / 模拟器验证。
- 私有库 / 私有组件改动默认要求主项目保持本地 `:path` 私有库依赖进行开发、验证与独立 `code-review`；仅当当前尚未指向本地源码且需要验证私有库源码改动时，才切到本地 `:path`。修改真实私有库源码仓后，回主项目基于本地依赖验证与 review；未收到明确指令前，不把验证或 review 基线切到线上版本化依赖或 `Pods/` vendored snapshot。
- 涉及私有库验证时，必须保持本地 `:path` 私有库依赖作为开发验证基线；验证通过后默认保持当前本地 `:path` 状态完成独立 review，除非用户明确要求回切线上版本化依赖或需要提交主项目依赖文件。
- 任何流程如果产出正式文档（HTML 方案、PRD、评审、报告、任务清单、接口说明、handoff），统一路由到 `html-docs`。其它 Skill 只提供素材包、结论和证据路径，不自行维护最终 HTML 文档结构或样式。
- `ios-verification` 统一负责验证前路由、受影响测试选择、定向验证执行、项目环境验证、失败摘要和最终证据裁决。
- `ios-verification` 不再是所有 Apple Xcode 项目改动的强制收尾；只有用户显式要求、发布前自检、高风险、证据不足或需要项目环境证据时才补强执行。
- 执行可选 `xcodebuild` 验证时，证据必须来自目标项目根目录的非沙盒项目环境，而不是 sandbox 结果；继续遵守 `.xcworkspace` 优先、优先选择绑定了单元测试 `*Tests` target / bundle 的 scheme、iOS 默认优先已连接真机约束。
- 本地执行 `xcodebuild`（含 `-list` / `-showdestinations` / build/test）必须由主 Agent 以非沙盒环境（Codex 使用 `functions.exec_command` + `sandbox_permissions="require_escalated"`）启动目标项目根目录 `codex_verify.sh` 或本机 `~/.codex/bin/codex_verify`，并接入 shared build-queue daemon；可用 `--queue-status` 查看队列；不得直接调用 `xcodebuild`，也不要让多个 Agent 各自裸跑。
- 主入口 `codex-subagent-orchestration` 负责自适应编排：所有生产代码和测试代码实施统一切到 `ios-feature-implementation` 的内部模式，验证相关动作统一切到 `ios-verification`。
- 除实现链路的 reviewer subAgent 是强制收口角色外，本仓不对 coder / tester / pm / reporter 等其它原生 subAgent 的启动场景、角色拆分或数量做额外限制；主 Agent 可按当前任务与运行时能力自行决定。
- 多 Agent 编排默认遵守 checkpoint 合同：`CP0` / `CP1` / `CP2` / `CP3`。
- 多 Agent 编排默认遵守 `fail-fix-report`：先定位失败、修复并重跑，再汇报。
- 如果当前任务未进入 `codex-subagent-orchestration`，或 coder / tester 只能由主 Agent 串行承担，实现型任务仍必须三步收口：`实现 skill -> 定向验证 / no_test_reason -> reviewer subAgent(code-review)`；若 reviewer subAgent 不可用，只能报告 blocked / pending review，不能降级为实现者自审。
- Apple API / availability / WWDC 问题优先在主 Skill 内部路由到 `apple-docs` 并使用 `appleDeveloperDocs`。

## 边界优先级

- 实现链路：`ios-feature-implementation` 是唯一真正实施入口；先在内部选择 `business` / `swiftui` / `liquid-glass` / `uikit` / `mixed-ui` / `advanced-swift` / `refactor` / `sdk-contract` / `test-implementation`，不要把普通页面、业务、高级 Swift、SDK 架构、Liquid Glass、测试代码编写或重构实施拆到独立 Skill。
- 验证链路：`ios-verification` 是唯一验证入口；内部使用 `route` / `affected-tests` / `execute` / `digest` / `final-gate` 模式完成验证路由、测试面选择、执行、失败归因和证据裁决。
- 构建链路：`xcode-build` 只处理 Build Settings、签名、Archive / Export、CI/CD、scheme / xcconfig / build script 设计；一次性 build/test 验证转交 `ios-verification`。
- 诊断链路：`debugging` 只处理运行时症状；`ios-performance` 只处理性能证据与基线，不接泛化 crash 或普通测试补写。
- SDK 架构、Liquid Glass 与测试代码编写：均归入 `ios-feature-implementation` 内部模式；SDK 模块边界 / Public API / 分发 / 版本演进使用 `sdk-contract`，iOS 26+ 玻璃 API / 回退 / 审查使用 `liquid-glass`，XCTest / XCUITest / test doubles / fixtures 使用 `test-implementation`。

## Core Implementation

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `codex-subagent-orchestration` | 默认 iOS 主 Skill 入口 | 所有 iOS 开发任务的统一入口；先按 `lite` / `standard` / `full` 做编排决策，再内部路由到统一实施 / 验证 / 调试 / 性能 / 审查 / 按需补强模块；除 reviewer subAgent 是强制收口角色外，其它 subAgent 使用不做仓库级限制 | 只做一次纯文档型低频任务时直接使用 `html-docs`；或运行时工具不可用、策略禁止导致 reviewer subAgent 无法启动时，需要报告 blocked / pending review | `ios-feature-implementation`、`ios-verification`、`debugging`、`ios-performance`、`code-review`、`html-docs` |
| `ios-feature-implementation` | 唯一 iOS 代码实施 Skill | service / repository / use case / view model / 导航接线 / SwiftUI / Liquid Glass / UIKit / mixed UI / advanced Swift / refactor / SDK contract / SDK architecture / XCTest / XCUITest / Mock / Stub / Spy / Fake / fixture / Page Object | 构建配置、设备自动化、性能 profiling、运行时诊断、官方文档事实检索、纯验证执行、纯静态审查、纯视觉方向探索 | `ios-verification`、`code-review`、`debugging`、`ios-performance`、`xcode-build`、`apple-docs`、`ui-ux-design-system` |

## Automation / Build / Validation

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `ios-automation` | 设备自动化（Simulator + 真机统一入口） | 模拟器生命周期、安装启动、语义 snapshot、snapshot-local 元素 refs、UI smoke、replay 取证、无障碍、截图、真机诊断 | Build Settings / 签名策略设计、普通业务实现、默认验证收口 | `xcode-build`、`ios-feature-implementation`、`ios-verification` |
| `xcode-build` | 构建配置与交付链路 | Build Settings、签名、Archive、导出 IPA、CI/CD、scheme、xcconfig、build script、XCFramework | 一次性 build/test 验证、默认收口审查、测试代码编写 | `ios-verification`、`code-review`、`ios-feature-implementation` |
| `ios-verification` | 统一验证入口 | 验证前路由、受影响测试选择、定向 XCTest、项目环境 build/test、失败摘要、final evidence gate、重复验证抑制 | 测试代码编写、构建配置设计、运行时调试、性能 profiling、设备导航自动化 | `ios-feature-implementation`、`code-review`、`xcode-build`、`ios-automation`、`debugging`、`ios-performance` |

## Diagnostics

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `code-review` | 静态审查 | review 代码、PR diff、public API 评审；默认由独立 reviewer subAgent 执行 | 直接实现修复、运行时定位 | `debugging`、`ios-performance`、`ios-feature-implementation` |
| `debugging` | 运行时排障 | crash、异常、未释放、符号化栈、LLDB 定位 | 纯静态审查、性能分析与 benchmark、构建配置设计 | `code-review`、`ios-performance`、`xcode-build`、`ios-feature-implementation` |
| `ios-performance` | 性能分析与测试 | 掉帧、启动慢、CPU / 内存异常、性能回归基线、`measure(metrics:)`、`xctrace`、Instruments | 通用业务实现、普通单元/UI 测试补齐、泛化 crash 排查 | `ios-feature-implementation`、`ios-verification`、`debugging` |

## Internal Modules

这些 skills 保留在 core 中，主要供主 Skill 内部路由使用；只有高级场景才建议手动直达：
- `apple-docs`

## Additional Skills

这些技能同样位于 `skills/` 下，但默认按需触发，不作为 iOS 主链路的第一入口：
- `docs`：`html-docs`（正式 HTML 文档唯一规范入口；承接方案、PRD、评审、报告、任务清单、接口说明与 handoff，并负责统一样式和暗黑模式适配）
- `research`：`ui-ux-design-system`、`app-store-changelog`、`app-store-opportunity-research`
- `workflow`：`git-workflow`、`gh-pr-flow`
