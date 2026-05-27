# 业务 Skill 分类索引（single-entry iOS core）

本文覆盖本仓库 `skills/` 下的全部 skills。用户默认入口只有 `codex-subagent-orchestration`；低频技能与高频技能统一保存在同一根目录下。

## 分类原则
- `Core Implementation`：默认优先触发的通用实现技能。
- `Automation / Build / Validation`：自动化执行、构建配置与收尾验收技能。
- `Diagnostics`：发现问题、分析风险、定位根因的技能。
- `Internal Modules`：由主 Skill 内部路由使用的 iOS 专项模块。
- `Additional Skills`：按需触发的低频技能；与 core skills 共用同一目录，只通过路由策略区分。

## 严格路由总则
- 只要任务产出修改了 Apple Xcode 项目相关内容，最终都必须切到 `verify-ios-build` 做收尾门禁。
- 最终门禁必须在目标项目根目录的项目环境执行，而不是把沙箱内构建结果当作最终结论。
- 本地执行 `xcodebuild`（含 `-list` / `-showdestinations` / build/test）默认都走非沙盒项目环境。
- 本地构建缓存统一复用 Xcode 系统 DerivedData，不要用临时 `-derivedDataPath` 或 `XCODE_DERIVED_DATA` 覆盖。
- iOS 项目如果同时存在 `.xcworkspace` 与 `.xcodeproj`，门禁必须优先 `.xcworkspace`；默认优先已连接真机，找不到连接中的真机时再回退到 simulator。
- 如果没有用户显式指定 scheme，定向测试与最终门禁默认优先选择绑定了单元测试 `*Tests` target / bundle 的 scheme；若不存在，再回退到其它测试 scheme。
- 在 `verify-ios-build` 成功前，任何技能都不能把任务表述为“已完成”。
- 默认优先切到 `codex-subagent-orchestration` 做自适应编排：先按 `lite` / `standard` / `full` 选择角色，再协调编码、调试、性能、审查、测试与最终门禁；构建、测试、simulator、真机、截图与日志优先切 `ios-device-automation`、`ios-simulator-automation`、`xcode-build` 或 `verify-ios-build`。
- 多 Agent 编排默认遵守 checkpoint 合同：`CP0` / `CP1` / `CP2` / `CP3`。
- 多 Agent 编排默认遵守 `fail-fix-report`：先定位失败、修复并重跑，再汇报。
- 如果当前任务未进入 `codex-subagent-orchestration`，或当前轮只能以单 Agent 执行，实现型任务默认也按固定四步收口：`实现 skill -> testing -> code-review -> verify-ios-build`。
- Apple API / availability / WWDC 问题优先在主 Skill 内部路由到 `apple-docs` 并使用 `appleDeveloperDocs`。

## Core Implementation

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `ios-feature-implementation` | 默认 iOS feature 实现技能 | service / repository / use case / view model / 导航接线 / async 流程 | UIKit/SwiftUI 专项页面实现、构建配置、自动化、性能 profiling、官方文档检索 | `swiftui-feature-implementation`、`uikit-feature-implementation`、`swift-expert`、`xcode-build`、`ios-performance` |
| `swiftui-feature-implementation` | 普通 SwiftUI 落地实现 | 在既定模式下实现页面、表单、列表、状态绑定 | 新页面模式选型、既有大 view 重构、Liquid Glass、性能取证 | `ios-feature-implementation`、`ios-performance` |
| `uikit-feature-implementation` | 普通 UIKit 落地实现 | ViewController / UIView / 布局 / 列表 / 页面交互接入 | 通用业务建模、SwiftUI、构建配置、自动化 | `ios-feature-implementation`、`xcode-build`、`debugging`、`ios-performance` |
| `codex-subagent-orchestration` | 默认 iOS 主 Skill 入口 | 所有 iOS 开发任务的统一入口；先按 `lite` / `standard` / `full` 选择角色，再内部路由到实现 / 调试 / 性能 / 测试 / 门禁模块 | 只做一次纯文档型低频任务，或当前运行时限制且用户未授权 subAgent 时的临时单 Agent 回退 | `ios-feature-implementation`、`debugging`、`ios-performance`、`code-review`、`testing`、`verify-ios-build` |

## Automation / Build / Validation

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `ios-simulator-automation` | Simulator 自动化 | boot/shutdown/create/delete、语义导航、无障碍检查、模拟器验证 | 真机运行、Build Settings/签名策略、普通业务实现 | `ios-device-automation`、`xcode-build`、`ios-feature-implementation` |
| `ios-device-automation` | 真机自动化 | 连接中的真机构建、安装、启动、测试、设备诊断 | 纯 Simulator 自动化、Build Settings/签名策略设计、普通业务实现 | `ios-simulator-automation`、`xcode-build`、`ios-feature-implementation` |
| `xcode-build` | 构建配置与交付链路 | Build Settings、签名、Archive、导出 IPA、CI/CD | 任务末尾只跑一次编译验收 | `verify-ios-build` |
| `verify-ios-build` | 收尾构建门禁 + 构建验收 | 任何 Apple Xcode 项目相关改动的强制最终门禁 | 构建签名、Archive、导出、CI 设计 | `xcode-build` |
| `testing` | 测试编写专项 | 单元测试、UI 测试、Mock/Stub/Spy、异步测试 | 性能 benchmark、`measure(metrics:)`、`xctrace`、一次性 `xcodebuild` 校验 | `ios-performance`、`verify-ios-build`、`code-review`、`debugging` |

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
- `swiftui-ui-patterns`
- `swiftui-view-refactor`
- `swiftui-liquid-glass`
- `refactoring`
- `sdk-architecture`
- `swiftui-performance-audit`

## Additional Skills

这些技能同样位于 `skills/` 下，但默认按需触发，不作为 iOS 主链路的第一入口：
- `research`：`ui-ux-design-system`、`app-store-changelog`、`app-store-opportunity-research`、`open-design`
- `docs`：`html-docs`、`office-docx`、`office-pptx`
- `workflow`：`git-workflow`、`gh-pr-flow`
- `macos`：`macos-menubar-tuist-app`、`macos-spm-app-packaging`
