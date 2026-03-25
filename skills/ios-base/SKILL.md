---
name: ios-base
description: 默认 iOS/Swift 基础开发技能。用于通用业务实现、组件开发、导航、常规 async/await 与 UIKit/SwiftUI 基础实践；不负责深度 Swift 抽象、SwiftUI 专项重构、构建配置或官方文档检索。
---

# iOS/Swift 核心开发

## 角色定位
- 默认型主 skill。
- 负责大多数常规 iOS 业务开发任务。
- 只覆盖基础实现与常规工程约定，不承担专项深挖。

## 适用场景
- 编写或修改常规 Swift、UIKit、SwiftUI 业务代码。
- 创建组件、处理导航、组织 feature 目录和服务层。
- 处理常规 async/await、状态管理、基础性能习惯和内存安全约束。

## 核心规则
- 默认优先值类型、严格访问控制、`guard` 提前返回和结构化并发。
- UI 更新放在主线程或 `@MainActor`。
- 业务逻辑进入 service / model，不堆进 view 或 view controller。
- 文件、方法和视图体量超过常规阈值时，优先拆分，而不是继续堆叠复杂度。

## 参考资源
- `references/swiftui.md`：SwiftUI 基础实践。
- `references/uikit.md`：UIKit 结构与常见模式。
- `references/navigation.md`：导航组织与深链。
- `references/animations.md`：动画基础。
- `references/performance.md`：常规性能守则。
- `references/component-design.md`：组件设计。
- `references/memory-management.md`：内存管理。

## 与其他技能的关系
- 常规 iOS 业务开发默认优先使用本技能。
- 如果任务进入复杂并发、类型擦除、协议族或跨平台可用性策略，切换到 `swift-expert`。
- 如果任务已经变成 benchmark、`measure(metrics:)`、`xctrace`、Instruments 或启动 / 滚动性能分析，切换到 `ios-performance`。
- 如果任务是新建 SwiftUI 页面并做模式选型，切换到 `swiftui-ui-patterns`。
- 如果任务是整理已有 SwiftUI 巨大 view 文件，切换到 `swiftui-view-refactor`。
- 如果任务是构建配置、签名、Archive/Export 或 CI，切换到 `xcode-build`。
- 如果只是查询 Apple 官方 API、可用性或 WWDC 内容，切换到 `apple-docs`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: ios-base`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel
