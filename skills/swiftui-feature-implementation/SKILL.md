---
name: swiftui-feature-implementation
description: SwiftUI 常规页面落地技能。只在页面模式、路由结构和状态归属已经明确时，用于实现普通 SwiftUI 页面、组件、列表、表单、状态绑定与界面交互；如果任务核心是新页面模式选型、已有巨型 SwiftUI view 重构、Liquid Glass 专项、性能取证或官方文档检索，不要使用本 skill 作为主 skill。
---

# SwiftUI Feature 实现

## 角色定位
- 专注于普通 SwiftUI 页面与组件落地的实现型 skill。
- 负责把既定的状态、路由和业务输入转成稳定可维护的 SwiftUI 代码。
- 不负责新页面模式设计、既有大 view 重构、Liquid Glass 或性能 profiling。

## 触发判定（硬边界）
- 页面结构、路由和状态归属都已经明确，只差 SwiftUI 代码落地时，使用本 skill。
- 用户还在问“应该用什么页面模式 / `NavigationStack` / `sheet` / 组件拆分”，切换到 `swiftui-ui-patterns`。
- 用户给的是一个已经存在且过大的 SwiftUI 文件，需要清理 `body`、副作用或状态错位，切换到 `swiftui-view-refactor`。
- 只要问题核心不是普通 SwiftUI 页面代码，而是 Liquid Glass、profiling 或 Apple 文档事实，就不要用本 skill 作为主 skill。

## 适用场景
- 在既定架构下实现设置页、详情页、表单、列表、空态、状态切换等 SwiftUI 界面。
- 接入现有 view model、service 或 router，把业务状态绑定到 SwiftUI 视图。
- 编写普通动画、过渡、组件组合与预览代码。

## 核心规则
- iOS 17+ 默认优先 `@Observable`、`@State`、`@Bindable` 与显式依赖注入。
- 保持根视图结构稳定，避免在 `body` 中堆叠过多副作用和复杂分支。
- 只把真正属于界面的状态留在 View；业务逻辑放回 `ios-feature-implementation` 管理的类型中。
- 新建 `.swift` 文件且项目要求文件头时，`Created by` 必须使用本机用户名称 `Choshim.Wei`，不要写 `Codex`；日期默认使用 `YYYY/M/D`，例如 `Created by Choshim.Wei on 2026/4/11.`。

## 参考资源
- `references/swiftui.md`

## 与其他技能的关系
- 已经有明确页面模式或路由结构时，普通 SwiftUI 落地优先使用本技能。
- 如果任务是新建 SwiftUI 页面并做模式选型，主 skill 切换到 `swiftui-ui-patterns`。
- 如果任务是整理已有 SwiftUI 巨大 view 文件，主 skill 切换到 `swiftui-view-refactor`。
- 如果任务是 iOS 26+ 的 Liquid Glass 专项实现，切换到 `swiftui-liquid-glass`。
- 如果任务已经暴露为掉帧、重绘过多或 profiling 问题，切换到 `ios-performance`。
- 需要落地通用业务类型、service 或导航 wiring 时，可联动 `ios-feature-implementation`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: swiftui-feature-implementation`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel
