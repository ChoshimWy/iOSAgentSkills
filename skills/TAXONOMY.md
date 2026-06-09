# 业务 Skill 分类索引（single-entry iOS core）

本文覆盖本仓库 `skills/` 下的全部 skills。用户默认入口只有 `codex-subagent-orchestration`；低频技能与高频技能统一保存在同一根目录下。

## 分类原则
- `Core Implementation`：默认优先触发的通用实现技能。
- `Automation / Build / Validation`：自动化执行、构建配置与收尾验收技能。
- `Diagnostics`：发现问题、分析风险、定位根因的技能。
- `Internal Modules`：由主 Skill 内部路由使用的 iOS 专项模块。
- `Additional Skills`：按需触发的低频技能；与 core skills 共用同一目录，只通过路由策略区分。

## 严格路由总则
- 默认完成标准：定向测试或必要验证通过，且 `code-review` 无 blocking findings。
- 如果当前改动不适合运行测试，`testing` 阶段必须给出 `no_test_reason` 与替代验证依据，然后进入 `code-review`。
- `code-review` 默认审查本次任务全量差异及本次修改带来的直接影响面，包含 staged、unstaged、untracked 与任务起点基线之后的相关提交。
- 私有库 / 私有组件改动默认要求主项目切回或保持本地 `:path` 私有库依赖进行开发与验证；未收到明确指令前，不把验证基线切到线上版本化依赖或 `Pods/` vendored snapshot。
- `final-evidence-gate` 与 `verify-ios-build` 不再是所有 Apple Xcode 项目改动的强制收尾，仅作为用户显式要求、发布前自检或高风险场景的按需补强验证。
- 执行可选 `xcodebuild` 验证时，证据必须来自目标项目根目录的项目环境，而不是 sandbox 结果；同时继续遵守 `.xcworkspace` 优先、优先选择绑定了单元测试 `*Tests` target / bundle 的 scheme、iOS 默认优先已连接真机与系统 DerivedData 约束。
- 本地执行 `xcodebuild`（含 `-list` / `-showdestinations` / build/test）默认都走非沙盒项目环境；同机同仓如果有多个 Codex / Claude CLI 并发处理同一 Xcode 项目，项目环境验证必须统一经串行包装入口排队执行：优先目标项目根目录的 `codex_verify.sh`，若项目未接入则回退到本机 `~/.codex/bin/codex_verify`。
- 默认优先切到 `codex-subagent-orchestration` 做自适应编排：先按 `lite` / `standard` / `full` 选择角色，再协调编码、调试、性能、测试、审查与按需验证；构建、测试、自动化、截图与日志优先切 `ios-automation`、`xcode-build`、`testing`，需要补强证据时再切 `final-evidence-gate` 或 `verify-ios-build`。
- 多 Agent 编排默认遵守 checkpoint 合同：`CP0` / `CP1` / `CP2` / `CP3`。
- 多 Agent 编排默认遵守 `fail-fix-report`：先定位失败、修复并重跑，再汇报。
- 如果当前任务未进入 `codex-subagent-orchestration`，或当前轮只能以单 Agent 执行，实现型任务默认三步收口：`实现 skill -> testing/定向验证 -> code-review`。
- Apple API / availability / WWDC 问题优先在主 Skill 内部路由到 `apple-docs` 并使用 `appleDeveloperDocs`。

## Core Implementation

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `ios-feature-implementation` | 默认 iOS feature 实现技能 | service / repository / use case / view model / 导航接线 / async 流程 | UIKit/SwiftUI 专项页面实现、构建配置、自动化、性能 profiling、官方文档检索 | `swiftui-feature-implementation`、`uikit-feature-implementation`、`swift-expert`、`xcode-build`、`ios-performance` |
| `swiftui-feature-implementation` | SwiftUI 页面统一入口（模式选型 + 实现 + 重构） | 新页面模式选型、常规 SwiftUI 落地、已有大 view 重构 | Liquid Glass 专项、性能取证、通用非 SwiftUI 重构 | `ios-feature-implementation`、`ios-performance`、`refactoring` |
| `uikit-feature-implementation` | 普通 UIKit 落地实现 | ViewController / UIView / 布局 / 列表 / 页面交互接入 | 通用业务建模、SwiftUI、构建配置、自动化 | `ios-feature-implementation`、`xcode-build`、`debugging`、`ios-performance` |
| `codex-subagent-orchestration` | 默认 iOS 主 Skill 入口 | 所有 iOS 开发任务的统一入口；先按 `lite` / `standard` / `full` 选择角色，再内部路由到实现 / 调试 / 性能 / 测试 / 审查 / 按需验证模块 | 只做一次纯文档型低频任务，或当前运行时限制且用户未授权 subAgent 时的临时单 Agent 回退 | `ios-feature-implementation`、`debugging`、`ios-performance`、`code-review`、`testing`、`final-evidence-gate`、`verify-ios-build` |

## Automation / Build / Validation

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `ios-automation` | 设备自动化（Simulator + 真机统一入口） | 模拟器构建/导航/无障碍/生命周期，真机构建/安装/启动/诊断 | Build Settings/签名策略设计、普通业务实现 | `xcode-build`、`ios-feature-implementation` |
| `xcode-build` | 构建配置与交付链路 | Build Settings、签名、Archive、导出 IPA、CI/CD | 任务末尾只做默认收口审查 | `testing`、`code-review`、`final-evidence-gate` |
| `final-evidence-gate` | 按需证据裁决 | 用户显式要求、发布前自检或高风险场景下裁决现有 `xcodebuild test/build` 证据是否足够，必要时建议升级 `verify-ios-build` | 默认实现任务的强制收尾、构建签名、Archive、导出、CI 设计 | `verify-ios-build`、`xcode-build` |
| `verify-ios-build` | 按需项目环境构建验证 | 用户显式要求、发布前自检、证据不足或高风险场景下的项目环境验证 | 默认实现任务的强制收尾、构建签名、Archive、导出、CI 设计 | `final-evidence-gate`、`xcode-build` |
| `testing` | 测试编写专项 | 单元测试、UI 测试、Mock/Stub/Spy、异步测试，并记录可复用验证证据 | 性能 benchmark、`measure(metrics:)`、`xctrace`、一次性完成态裁决 | `ios-performance`、`final-evidence-gate`、`code-review`、`debugging` |

## Diagnostics

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `code-review` | 静态审查 | review 代码、PR diff、public API 评审 | 直接实现修复、运行时定位 | `debugging`、`ios-performance`、`sdk-architecture` |
| `debugging` | 运行时排障 | crash、异常、未释放、符号化栈、LLDB 定位 | 纯静态审查、性能分析与 benchmark、构建配置设计 | `code-review`、`ios-performance`、`xcode-build` |
| `ios-performance` | 性能分析与测试 | 掉帧、启动慢、CPU / 内存异常、性能回归基线、`measure(metrics:)`、`xctrace`、Instruments | 通用业务实现、普通单元/UI 测试补齐、泛化 crash 排查 | `testing`、`debugging`、`swift-expert` |
| `swift-expert` | 进阶 Swift 设计 | `actor`、`Sendable`、`PAT`、类型擦除、多平台可用性 | 普通 iOS 业务实现、性能 profiling / benchmark、通用页面实现 | `ios-feature-implementation`、`swiftui-feature-implementation`、`uikit-feature-implementation`、`ios-performance` |

## Internal Modules

这些 skills 保留在 core 中，主要供主 Skill 内部路由使用；只有高级场景才建议手动直达：
- `apple-docs`
- `swiftui-liquid-glass`
- `refactoring`
- `sdk-architecture`

## Additional Skills

这些技能同样位于 `skills/` 下，但默认按需触发，不作为 iOS 主链路的第一入口：
- `research`：`ui-ux-design-system`、`app-store-changelog`、`app-store-opportunity-research`、`open-design`
- `docs`：`html-docs`、`office-docx`、`office-pptx`
- `workflow`：`git-workflow`、`gh-pr-flow`
- `macos`：`macos-menubar-tuist-app`、`macos-spm-app-packaging`
