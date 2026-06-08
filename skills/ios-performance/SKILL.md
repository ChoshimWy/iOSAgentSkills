---
name: ios-performance
description: iOS 性能分析与测试技能。只在需要处理 UIKit / SwiftUI 的掉帧、启动慢、CPU / 内存压力、性能回归基线、`measure(metrics:)`、`xctrace` 或 Instruments 取证时使用；如果问题核心是 crash、异常、对象未释放根因、纯静态审查或普通单元/UI 测试补齐，不要把它当作主 skill；若任务产出修改了 Apple Xcode 项目相关内容，默认以定向测试/必要验证与 `code-review` 放行为收口；`final-evidence-gate` / `verify-ios-build` 仅在用户显式要求或需要补强完整项目环境证据时按需使用。
---

# iOS 性能分析与测试

## 角色定位
- 专项型 skill。
- 负责性能基线设计、profiling 取证、模板选择、优化方向和 before/after 验证。
- 不负责默认业务实现，也不替代普通测试编写和泛化 crash 调试。

## 触发判定（硬边界）
- 用户主要在问掉帧、启动慢、CPU / 内存压力、性能回归、`measure(metrics:)`、`xctrace` 或 Instruments 时，使用本 skill。
- 如果问题核心是 crash、异常、`unrecognized selector`、野指针或对象未释放根因，不要用本 skill 作为主 skill，切换到 `debugging`。
- 如果只是补业务单元测试、UI 测试或测试替身，切换到 `testing`。

## 适用场景
- UIKit / SwiftUI 列表滚动掉帧、动画卡顿、页面进入慢、启动慢。
- CPU 高、内存增长、可疑泄漏、主线程繁忙、SwiftUI 更新过多。
- 需要建立 `XCTest` 性能基线，如 `measure {}`、`measure(metrics:)`、`XCTApplicationLaunchMetric`。
- 需要用 `xcrun xctrace` / Instruments 录制 `Time Profiler`、`Animation Hitches`、`Allocations`、`Leaks`、`App Launch`、`SwiftUI`。

## 核心工作流
1. 先定义单一症状和目标交互。
2. 再区分“回归基线”还是“运行时取证”。
3. 为目标交互选择 XCTest metric 或 `xctrace` template。
4. 固定设备、OS 和构建配置，优先使用 Release。
5. 输出症状、证据、根因假设、优化方向和 before/after 验证方式。

## 参考资源
- `references/template-selection.md`
- `references/profiling-workflow.md`

## 可选证据验证
- 只要当前任务产出修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、构建脚本、plist / entitlements / xcconfig / scheme 或项目内环境配置），最终默认以定向测试/必要验证与 `code-review` 放行为收口；`final-evidence-gate` / `verify-ios-build` 仅在用户显式要求或需要补强完整项目环境证据时按需使用。
- 若执行可选完整验证，证据必须来自目标项目根目录的项目环境；沙箱内的构建结果不能作为完整项目环境证据。
- 对 iOS 项目，若升级到 `verify-ios-build`，必须优先 `.xcworkspace`（当 `.xcworkspace` 与 `.xcodeproj` 同时存在时），并默认优先已连接真机；找不到连接中的真机时再回退到 simulator。
- 若可选 `final-evidence-gate` / `verify-ios-build` 未执行或失败，应在交付中说明已执行的定向测试/审查证据与残余风险。

## 与其他技能的关系
- 只补业务单元测试、UI 测试、Mock / Stub / Spy 时，切换到 `testing`。
- 主要问题是 crash、异常、符号化栈、LLDB 或对象未释放时，切换到 `debugging`。
- 主要问题是复杂并发、类型擦除、协议抽象或跨平台可用性策略时，切换到 `swift-expert`。
- 需要整理 SwiftUI 视图结构时，切换到 `swiftui-feature-implementation`。
- 需要新建 SwiftUI 页面并做模式选型时，切换到 `swiftui-feature-implementation`。
- 需要 Apple 官方 API 或 Instruments 官方资料时，可辅以 `apple-docs`。
