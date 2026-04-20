---
name: swiftui-performance-audit
description: 旧名兼容 skill。仅用于兼容历史 prompt 中的 `swiftui-performance-audit` 名称；新的 UIKit / SwiftUI / 启动 / 内存 / `xctrace` / 性能测试任务统一使用 `ios-performance`；若兼容路径最终修改了 Apple Xcode 项目相关内容，收尾仍必须切到 `verify-ios-build` 并在项目环境完成最终验证。
---

# SwiftUI 性能审计（旧名兼容）

## 角色定位
- 兼容型 skill。
- 只用于承接旧 prompt 或旧文档中已经写死的 `swiftui-performance-audit` 名称。
- 不再作为默认性能分析 skill；新的性能任务统一收口到 `ios-performance`。

## 适用场景
- 用户明确提到旧 skill 名 `swiftui-performance-audit`。
- 仓库内旧文档或旧流程仍引用该名称，需要兼容解释。

## 核心工作流
1. 说明该名称已被 `ios-performance` 取代。
2. 如果任务仍然是 SwiftUI 性能问题，用 `ios-performance` 的流程继续处理。
3. 仅在解释旧名来源或兼容旧文档时保留本 skill。

## 强制收尾验证
- 如果兼容路径最终修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、构建脚本、plist / entitlements / xcconfig / scheme 或项目内环境配置），最终必须切到 `verify-ios-build`。
- 最终门禁必须在目标项目根目录的项目环境执行；沙箱内的构建结果不能作为最终验收结论。
- 对 iOS 项目，`verify-ios-build` 必须优先 `.xcworkspace`（当 `.xcworkspace` 与 `.xcodeproj` 同时存在时），并默认优先已连接真机；找不到连接中的真机时再回退到 simulator。
- 在 `verify-ios-build` 成功前，不得把任务表述为“已完成”；只能明确说明“实现已完成，但验证未完成/失败，任务未完成”。

## 与其他技能的关系
- 新的性能分析、benchmark、`measure(metrics:)`、`xctrace`、Instruments 任务统一使用 `ios-performance`。
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
