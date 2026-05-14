---
name: ios-feature-implementation
description: 默认 iOS feature 实现技能。只用于与具体 UI 技术栈无关的通用业务实现：service / repository / use case / domain model / view model、依赖注入、导航接线和常规 async/await 落地；如果任务核心已经变成 SwiftUI / UIKit 页面代码、页面模式选型、已有 SwiftUI 大 view 重构、构建配置、模拟器/真机自动化、性能取证或官方文档检索，不要使用本 skill 作为主 skill；若任务产出修改了 Apple Xcode 项目相关内容，收尾必须切到 `verify-ios-build` 并在项目环境完成最终验证。
---

# iOS Feature 实现

## 角色定位
- 默认型主 skill。
- 负责大多数通用 iOS feature 业务代码与应用层 glue code。
- 不直接承担 UIKit / SwiftUI 专项页面结构设计，也不负责构建、自动化与性能取证。

## 触发判定（硬边界）
- 用户主要在问 `service`、`repository`、`use case`、`view model`、`coordinator`、`router`、依赖注入或导航接线时，使用本 skill。
- 用户主要在问 `NavigationStack` / `TabView` / `sheet` / `body` / 页面布局 / `UIViewController` / 组件样式时，不要用本 skill 作为主 skill。
- 用户主要在问 `xcodebuild` 门禁、签名、`simctl`、`devicectl`、`xctrace`、`measure(metrics:)` 或 Apple 官方 API 事实时，切换到对应专项 skill。

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

## 强制收尾验证
- 如果当前任务没有进入 `codex-subagent-orchestration`，或当前轮只能以单 Agent 执行，本 skill 完成实现后也不要直接跳到最终门禁；默认后续链路按固定四步执行：`ios-feature-implementation -> code-review -> testing -> verify-ios-build`。
- 只要当前任务产出修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、构建脚本、plist / entitlements / xcconfig / scheme 或项目内环境配置），最终必须切到 `verify-ios-build`。
- 最终门禁必须在目标项目根目录的项目环境执行；沙箱内的构建结果不能作为最终验收结论。
- 对 iOS 项目，`verify-ios-build` 必须优先 `.xcworkspace`（当 `.xcworkspace` 与 `.xcodeproj` 同时存在时），并默认优先已连接真机；找不到连接中的真机时再回退到 simulator。
- 在 `verify-ios-build` 成功前，不得把任务表述为“已完成”；只能明确说明“实现已完成，但验证未完成/失败，任务未完成”。

## 与其他技能的关系
- 通用 iOS feature 业务开发默认优先使用本技能。
- 如果当前任务属于非编排 / 单 Agent 的实现链路，本 skill 完成代码修改后，固定先切到 `code-review`，再切到 `testing`，最后切到 `verify-ios-build`。
- 如果任务核心已经进入普通 SwiftUI 页面落地，本 skill 只作为业务层辅助，主 skill 切换到 `swiftui-feature-implementation`。
- 如果任务核心已经进入普通 UIKit 页面落地，本 skill 只作为业务层辅助，主 skill 切换到 `uikit-feature-implementation`。
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
