---
name: swift-expert
description: Swift 进阶开发技能。仅用于复杂并发隔离、PAT/类型擦除、跨平台可用性策略和高阶 API 设计等 Swift 问题；不处理常规 iOS 业务实现、性能分析测试或一般 UI 重构。
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
- 不为普通业务代码引入不必要的高阶抽象。

## 参考资源
- `references/async-concurrency.md`
- `references/memory-performance.md`
- `references/protocol-oriented.md`
- `references/swiftui-patterns.md`

## 与其他技能的关系
- 常规 iOS 开发、通用 UIKit / SwiftUI 业务实现优先使用 `ios-base`。
- 性能 baseline、`measure(metrics:)`、`xctrace`、Instruments 优先使用 `ios-performance`。
- 新建 SwiftUI 页面模式设计优先使用 `swiftui-ui-patterns`。
- 已有 SwiftUI 视图文件整理优先使用 `swiftui-view-refactor`。
- 只有在出现复杂抽象、并发隔离或跨平台策略时，才切换到本技能。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: swift-expert`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel
