---
name: swiftui-ui-patterns
description: 提供“新建或模式选型”阶段的 SwiftUI UI 最佳实践与示例导向指南，专门用于新页面结构、导航层级、状态归属和组件拆分方案选择；不要用于既定结构下的普通 SwiftUI 实现、已有巨型 SwiftUI view 清理、视觉设计系统生成或性能审计；若任务产出修改了 Apple Xcode 项目相关内容，收尾必须切到 `verify-ios-build` 并在项目环境完成最终验证。
---

# SwiftUI UI 模式

## 角色定位
- 专项型 skill。
- 只负责新页面搭建、模式选型和组件级实现路线。
- 不负责跨栈设计系统或已有视图文件清理。

## 触发判定（硬边界）
- 用户在问“新页面该怎么组织 / 该选什么模式 / 状态放哪 / 路由怎么搭”时，使用本 skill。
- 页面结构已经确定，只是要把方案写成 SwiftUI 代码时，不要用本 skill 作为主 skill，切换到 `swiftui-feature-implementation`。
- 已经存在一个庞大的 SwiftUI 文件需要清理时，切换到 `swiftui-view-refactor`。

## 适用场景
- 设计新的 SwiftUI 页面、组件和导航模式。
- 为 `TabView`、`NavigationStack`、`sheet`、`List`、`Grid` 选择合适实现路径。
- 为新 feature 确定状态归属、路由组织和组件拆分方式。

## 核心工作流
1. 先判断页面类型。
2. 再决定状态归属与路由结构。
3. 最后从 `references/components-index.md` 进入对应组件参考。
4. 如果新建 `.swift` 文件且项目要求文件头，`Created by` 必须使用本机用户名称 `Choshim.Wei`，不要写 `Codex`；日期默认使用 `YYYY/M/D`，例如 `Created by Choshim.Wei on 2026/4/11.`。

## 参考资源
- `references/components-index.md`
- `references/app-wiring.md`
- `references/async-state.md`
- `references/navigationstack.md`
- `references/sheets.md`
- `references/previews.md`

## 强制收尾验证
- 只要当前任务产出修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、构建脚本、plist / entitlements / xcconfig / scheme 或项目内环境配置），最终必须切到 `verify-ios-build`。
- 最终门禁必须在目标项目根目录的项目环境执行；沙箱内的构建结果不能作为最终验收结论。
- 对 iOS 项目，`verify-ios-build` 必须优先 `.xcworkspace`（当 `.xcworkspace` 与 `.xcodeproj` 同时存在时），并默认优先已连接真机；找不到连接中的真机时再回退到 simulator。
- 在 `verify-ios-build` 成功前，不得把任务表述为“已完成”；只能明确说明“实现已完成，但验证未完成/失败，任务未完成”。

## 与其他技能的关系
- 新建 SwiftUI 页面或做模式选型时优先使用本技能。
- 如果页面模式已经明确，只需要把页面落地成普通 SwiftUI 代码，主 skill 切换到 `swiftui-feature-implementation`。
- 如果目标是整理已有 SwiftUI 巨型 view 文件，切换到 `swiftui-view-refactor`。
- 如果目标是视觉设计系统、色板、字体、无障碍和跨栈 UI/UX 方向，切换到 `ui-ux-design-system`。
- 如果是 Liquid Glass 专项设计与实现，切换到 `swiftui-liquid-glass`。
- 如果是 SwiftUI 运行时卡顿、掉帧、profiling 或 `xctrace` 取证，切换到 `ios-performance`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定当前任务已经加载并正在使用本 Skill 时：

- 在回复末尾追加一行：`// skill-used: swiftui-ui-patterns`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
