---
name: ios-feature-implementation
description: 默认 iOS feature 实现技能。用于通用 iOS/Swift 业务实现、service / repository / use case / view model、依赖注入、导航接线和常规 async/await 落地；不要用于 UIKit/SwiftUI 专项页面实现、已有 SwiftUI 大 view 重构、构建配置、模拟器/真机自动化、性能取证或官方文档检索。
---

# iOS Feature 实现

## 角色定位
- 默认型主 skill。
- 负责大多数通用 iOS feature 业务代码与应用层 glue code。
- 不直接承担 UIKit / SwiftUI 专项页面结构设计，也不负责构建、自动化与性能取证。

## 适用场景
- 编写或修改 service、repository、use case、domain model、view model。
- 处理依赖注入、feature wiring、导航接线和错误流转。
- 落地常规 async/await、状态同步和业务层内存安全约束。

## 核心规则
- 默认优先值类型、严格访问控制、`guard` 提前返回和结构化并发。
- UI 更新放在主线程或 `@MainActor`。
- 业务逻辑进入 service / model / coordinator，不堆进 view 或 view controller。
- 文件、方法或类型体量超过常规阈值时优先拆分，而不是继续堆叠复杂度。
- 对应项目中新建 `.swift`、`.h`、`.m`、`.mm` 等源码文件且项目要求文件头时，`Created by` 必须使用本机用户名称 `Choshim.Wei`，不要写 `Codex`；日期默认使用 `YYYY/M/D`，例如 `Created by Choshim.Wei on 2026/4/11.`。

## 参考资源
- `references/navigation.md`：导航组织与深链。
- `references/memory-management.md`：内存管理与循环引用防护。

## 与其他技能的关系
- 通用 iOS feature 业务开发默认优先使用本技能。
- 如果任务进入普通 SwiftUI 页面落地，切换到 `swiftui-feature-implementation`。
- 如果任务进入普通 UIKit 页面落地，切换到 `uikit-feature-implementation`。
- 如果任务进入复杂并发、类型擦除、协议族或跨平台可用性策略，切换到 `swift-expert`。
- 如果任务已经变成 benchmark、`measure(metrics:)`、`xctrace`、Instruments 或启动 / 滚动性能分析，切换到 `ios-performance`。
- 如果任务是构建配置、签名、Archive/Export 或 CI，切换到 `xcode-build`。
- 如果只是查询 Apple 官方 API、可用性或 WWDC 内容，切换到 `apple-docs`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: ios-feature-implementation`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel
