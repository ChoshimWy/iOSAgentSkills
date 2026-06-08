---
name: swift-expert
description: Swift 进阶开发技能。仅用于复杂并发隔离、PAT/类型擦除、跨平台可用性策略和高阶 API 设计等 Swift 问题；不处理常规 iOS 业务实现、性能分析测试或一般 UI 重构；若任务产出修改了 Apple Xcode 项目相关内容，默认以定向测试/必要验证与 `code-review` 放行为收口；`final-evidence-gate` / `verify-ios-build` 仅在用户显式要求或需要补强完整项目环境证据时按需使用。
---

# Swift 进阶开发

## 角色定位
- 专项型 skill。
- 负责高风险、高抽象度的 Swift 设计问题。
- 不替代默认 iOS 业务开发技能。

## 适用场景
- 设计协议导向深度抽象、复杂泛型约束和类型擦除。
- 设计 actor 隔离、`Sendable`、取消传播和重入策略。
- 设计跨 iOS / macOS / watchOS / tvOS 的可用性边界和条件编译。

## 核心规则
- 优先用明确、可验证的并发模型和 API 边界。
- 如果问题已经进入 benchmark、profiling 或 Instruments 取证阶段，切换到 `ios-performance`。
- 对外 API 需要清楚的可用性说明、抽象边界和测试路径。
- 对 `public` / `open` API、跨模块复用类型与可复用协议要求，默认补 `///` 文档注释；至少说明输入、输出、失败语义、并发语义与关键副作用。
- 涉及并发边界（`@MainActor` / actor / 回调线程）、副作用（状态/DB/缓存/磁盘/网络）或失败路径（throws/错误码/回退条件）的实现，注释必须写清约束与线程假设。
- 复杂分支补 `why` 注释，解释业务原因/兼容背景/失败保护；不要只复述代码字面含义。
- 只补文件头注释不算完成；关键函数与关键分支必须有可执行语义的内联注释。
- 不为普通业务代码引入不必要的高阶抽象。
- 如果产出中新增 `.swift`、`.h`、`.m`、`.mm` 文件且项目要求文件头，`Created by` 必须使用本机用户名称（`whoami` 输出），不要写 `Codex`；日期默认使用 `YYYY/M/D`，例如 `Created by $(whoami) on 2026/4/11.`。

## 参考资源
- `references/async-concurrency.md`
- `references/memory-performance.md`
- `references/protocol-oriented.md`
- `references/swiftui-patterns.md`

## 可选证据验证
- 只要当前任务产出修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、构建脚本、plist / entitlements / xcconfig / scheme 或项目内环境配置），最终默认以定向测试/必要验证与 `code-review` 放行为收口；`final-evidence-gate` / `verify-ios-build` 仅在用户显式要求或需要补强完整项目环境证据时按需使用。
- 若执行可选完整验证，证据必须来自目标项目根目录的项目环境；沙箱内的构建结果不能作为完整项目环境证据。
- 对 iOS 项目，若升级到 `verify-ios-build`，必须优先 `.xcworkspace`（当 `.xcworkspace` 与 `.xcodeproj` 同时存在时），并默认优先已连接真机；找不到连接中的真机时再回退到 simulator。
- 若可选 `final-evidence-gate` / `verify-ios-build` 未执行或失败，应在交付中说明已执行的定向测试/审查证据与残余风险。

## 与其他技能的关系
- 常规 iOS feature 业务实现优先使用 `ios-feature-implementation`。
- 普通 SwiftUI 页面落地优先使用 `swiftui-feature-implementation`。
- 普通 UIKit 页面落地优先使用 `uikit-feature-implementation`。
- 性能 baseline、`measure(metrics:)`、`xctrace`、Instruments 优先使用 `ios-performance`。
- 新建 SwiftUI 页面模式设计优先使用 `swiftui-feature-implementation`。
- 已有 SwiftUI 视图文件整理优先使用 `swiftui-feature-implementation`。
- 只有在出现复杂抽象、并发隔离或跨平台策略时，才切换到本技能。
