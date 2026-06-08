---
name: sdk-architecture
description: SDK/Framework 架构入口：模块边界、public API、入口类、Configuration、分发策略和可测试架构。普通页面、SwiftUI 实现和一次性构建校验走其它 skill；Xcode 改动收尾交给 final-evidence-gate。
---

# SDK 架构设计

## 角色定位
- 专项型 skill。
- 负责 SDK / Framework 的分层、公共 API、模块边界、可测试性与分发策略。
- 不负责普通应用功能开发，也不替代单纯的测试补写或构建收尾校验。

## 适用场景
- 设计 SDK 架构、模块划分、对外 API、SDK 入口类和 `Configuration`。
- 规划 `SPM` 模块化、`XCFramework` 分发或多平台适配边界。
- 为 SDK 设计可测试架构、Mock/Stub 注入点和版本演进策略。

## 核心规则
- 只暴露必要的 `public API`，把可变实现细节留在内部模块。
- 分层依赖固定为：`Public API Layer -> Feature Layer -> Core Layer -> Platform Layer`。
- 入口类负责初始化、生命周期和配置校验，不承担业务实现细节。
- 分发优先 `SPM`，二进制分发使用 `XCFramework`，版本遵循 `SemVer`。
- 任何 breaking change 都必须通过显式版本策略表达，而不是静默替换行为。
- 如果示例或目标项目需要新增 `.swift`、`.h`、`.m`、`.mm` 文件且项目要求文件头，`Created by` 必须使用本机用户名称（`whoami` 输出），不要写 `Codex`；日期默认使用 `YYYY/M/D`，例如 `Created by $(whoami) on 2026/4/11.`。

## 参考资源
- `references/design-guidelines.md`：API 设计准则、稳定性、防御、安全和版本演进策略。
- `references/sdk-testing.md`：SDK 可测试设计、Mock 模式和覆盖率目标。

## 输出要求
- 默认至少回答以下问题：
  - 宿主会接触到哪些 `public` 类型和入口方法。
  - 模块如何拆分，依赖如何单向流动。
  - 初始化、配置、日志、错误和关闭流程如何设计。
  - 如何做测试注入、版本演进和分发。
- 需要示例时，优先给入口类、`Configuration`、模块边界和依赖方向示意，而不是完整业务实现。

## 最终证据门禁
- 只要当前任务产出修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、构建脚本、plist / entitlements / xcconfig / scheme 或项目内环境配置），最终必须进入 `final-evidence-gate`；证据不足、高风险或命中工程/依赖/签名/资源打包类改动时，再切到 `verify-ios-build`。
- 最终验证证据必须来自目标项目根目录的项目环境；沙箱内的构建结果不能作为最终验收结论。
- 对 iOS 项目，若升级到 `verify-ios-build`，必须优先 `.xcworkspace`（当 `.xcworkspace` 与 `.xcodeproj` 同时存在时），并默认优先已连接真机；找不到连接中的真机时再回退到 simulator。
- 在 `final-evidence-gate` 接受现有证据或 `verify-ios-build` 成功前，不得把任务表述为“已完成”；只能明确说明“实现已完成，但验证证据不足/验证失败，任务未完成”。

## 与其他技能的关系
- 如果只是普通应用功能开发，切换到 `ios-feature-implementation`、`swiftui-feature-implementation` 或 `uikit-feature-implementation`。
- 如果只是补单元测试或 UI 测试，切换到 `testing`。
- 如果任务重点是构建签名、Archive、导出或 CI，切换到 `xcode-build`。
- 需要审查公开 API 设计质量时，可联动 `code-review`。
