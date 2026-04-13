---
name: swiftui-view-refactor
description: 以小而明确的子视图、MV 优先的数据流、稳定视图树、显式依赖注入和正确的 Observation 用法为默认策略，重构已有 SwiftUI 视图文件；只用于现有 SwiftUI 文件的结构化整理，不用于新页面模式设计、普通页面落地或通用非 SwiftUI 重构。
---

# SwiftUI 视图重构

## 角色定位
- 专项型 skill。
- 只负责已有 SwiftUI 视图文件的结构化重构执行。
- 不负责新页面模式选型，也不替代通用代码重构。

## 触发判定（硬边界）
- 已经有现成的 SwiftUI 文件，而且问题是 `body` 过长、子视图边界混乱、副作用堆在视图里或状态归属错位时，使用本 skill。
- 如果任务是从零设计新页面结构，切换到 `swiftui-ui-patterns`。
- 如果只是按既定结构实现普通 SwiftUI 页面，不要用本 skill 作为主 skill，切换到 `swiftui-feature-implementation`。

## 适用场景
- 清理 SwiftUI 巨型 view、过长 `body` 和过多计算型 helper。
- 把内联动作、副作用和业务逻辑从视图中抽离。
- 统一 `@Observable`、`@State`、view model 初始化和视图树稳定性。

## 核心工作流
1. 先理顺视图结构顺序。
2. 再抽离 `body` 内动作和副作用。
3. 拆独立子视图，稳定根视图结构。
4. 仅在现有代码明确要求时保留或调整 view model。
5. 如果重构中新增 `.swift` 文件且项目要求文件头，`Created by` 必须使用本机用户名称 `Choshim.Wei`，不要写 `Codex`；日期默认使用 `YYYY/M/D`，例如 `Created by Choshim.Wei on 2026/4/11.`。

## 参考资源
- `references/mv-patterns.md`

## 与其他技能的关系
- 当目标是“整理一个已经存在的 SwiftUI 大 view 文件”时，优先使用本技能。
- 如果任务是新建 SwiftUI 页面、设计 `TabView` / `NavigationStack` / `sheet` 模式，切换到 `swiftui-ui-patterns`。
- 如果任务只是把既定页面模式落地成普通 SwiftUI 代码，主 skill 切换到 `swiftui-feature-implementation`。
- 如果任务是通用代码异味重构而不是 SwiftUI 视图专项整理，切换到 `refactoring`。
- 如果任务已经暴露为掉帧、重绘过多或 profiling 问题，先交给 `ios-performance` 做诊断。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定当前任务已经加载并正在使用本 Skill 时：

- 在回复末尾追加一行：`// skill-used: swiftui-view-refactor`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
