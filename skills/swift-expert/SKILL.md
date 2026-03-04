---
name: swift-expert
description: Swift 进阶开发技能。当任务涉及复杂并发隔离设计、协议导向深度抽象（PAT/类型擦除）、高性能与内存剖析、跨平台可用性策略时使用。适用于 iOS/macOS/watchOS/tvOS 与部分服务端 Swift 场景。
---

# Swift 进阶开发

## 适用场景
- 设计协议导向深度抽象（PAT、泛型、类型擦除、API 泛化边界）
- 设计复杂并发模型（actor 隔离、`Sendable`、取消与重入策略）
- 构建复杂 SwiftUI 状态流与可测试 ViewModel（跨模块状态一致性）
- 基于数据做性能与内存剖析（ARC、复制开销、热路径量化）
- UIKit 与 SwiftUI 混合项目中的边界与迁移策略

## 工作原则

### 必做项
- 遵循 Swift API Design Guidelines
- 默认优先值类型（`struct`/`enum`），必要时再用 `class`
- 异步逻辑优先使用 async/await 与结构化并发
- 涉及跨线程共享状态时优先使用 `actor` 或明确同步策略
- 对外 API 补充文档注释与可用性说明
- 关键路径优化前先基于 Instruments 或可观测数据判断

### 禁止项
- 无充分理由的强制解包（`!`）
- 忽略错误传播与恢复策略
- 在并发上下文中无视隔离规则或 `Sendable` 警告
- 直接把 Objective-C 旧模式照搬到 Swift
- 在热路径中引入不必要的对象分配与复制

## 交付要求
- 给出可直接落地的 Swift 代码（含必要类型/协议定义）
- 说明关键设计选择（并发模型、抽象层次、可测试性）
- 包含最小可行测试示例（单元测试或并发测试）
- 需要跨平台时明确平台差异与可用性条件

## 专项参考
- **并发模型**: [references/async-concurrency.md](references/async-concurrency.md)
- **内存与性能**: [references/memory-performance.md](references/memory-performance.md)
- **协议导向**: [references/protocol-oriented.md](references/protocol-oriented.md)
- **SwiftUI 模式**: [references/swiftui-patterns.md](references/swiftui-patterns.md)
- **测试模式**: [references/testing-patterns.md](references/testing-patterns.md)

## 与其他技能的关系
- 常规 iOS 开发（UI 组件、导航、基础 async/await、通用规范）优先使用 `ios-base`
- 仅当出现以下任一情况时切换到本技能：
	- 需要设计可复用抽象层（协议族、类型擦除、复杂泛型约束）
	- 需要处理高风险并发问题（共享可变状态隔离、竞态、取消传播）
	- 需要做深入性能优化（基于 Instruments/指标而非经验判断）
	- 需要跨平台可用性设计与条件编译策略

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: swift-expert`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel
