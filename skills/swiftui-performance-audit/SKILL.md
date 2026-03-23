---
name: swiftui-performance-audit
description: 基于代码审查与架构分析，审计并改进 SwiftUI 运行时性能。仅用于渲染缓慢、滚动卡顿、CPU 或内存过高、视图更新过多、布局抖动等性能问题，以及在纯代码审查不足时引导 Instruments 分析；不负责通用 UI 模式设计或已有 view 文件的结构化重构。
---

# SwiftUI 性能审计

## 角色定位
- 诊断型 skill。
- 只负责 SwiftUI 运行时性能问题的定位、证据收集和修复方向。
- 不负责通用 UI 架构设计，也不直接承担大规模视图重构。

## 适用场景
- 渲染缓慢、滚动掉帧、CPU / 内存异常。
- 视图更新范围过大、布局抖动、长 `body` 更新。
- 需要判断是否应向用户索要 Instruments 证据。

## 核心工作流
1. 分类症状。
2. 先做代码优先审计。
3. 代码证据不足时，再请求 profiling 材料。
4. 输出问题、证据、修复方向和验证方式。

## 参考资源
- `references/code-smells.md`
- `references/profiling-intake.md`
- `references/report-template.md`
- `references/optimizing-swiftui-performance-instruments.md`
- `references/understanding-improving-swiftui-performance.md`
- `references/understanding-hangs-in-your-app.md`
- `references/demystify-swiftui-performance-wwdc23.md`

## 与其他技能的关系
- 当问题表现为掉帧、长更新、CPU / 内存异常、视图更新过广时，优先使用本技能。
- 如果任务是新建页面或选择 SwiftUI 实现模式，切换到 `swiftui-ui-patterns`。
- 如果任务是整理已有 SwiftUI 大 view 的结构与副作用，切换到 `swiftui-view-refactor`。
- 如果问题是一般运行时崩溃、泄漏或非 SwiftUI 特定卡顿，优先使用 `debugging`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: swiftui-performance-audit`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
