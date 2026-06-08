---
name: refactoring
description: 通用代码重构技能。用于处理长方法、重复代码、深层嵌套、回调地狱、God Object 等通用代码异味；如果目标是已有 SwiftUI 视图文件的结构化整理，应优先使用 `swiftui-feature-implementation`；若任务产出修改了 Apple Xcode 项目相关内容，默认以定向测试/必要验证与 `code-review` 放行为收口；`final-evidence-gate` / `verify-ios-build` 仅在用户显式要求或需要补强完整项目环境证据时按需使用。
---

# 代码重构

## 角色定位
- 专项型 skill。
- 负责与框架无关的通用代码异味重构。
- 不负责 SwiftUI view 文件专项整理，也不替代代码评审。

## 适用场景
- 函数过长、参数过多、重复逻辑、深层嵌套。
- 需要把回调迁移到 async/await。
- 需要拆分类、提取协议、引入策略模式或依赖注入。

## 核心规则
- 重构提交不混入功能改动。
- 每次一小步，保证编译和行为可验证。
- 有测试时先保住测试，再推进重构。

## 常用手法
- `Extract Method`
- `Guard Clause`
- `async/await` 替换回调地狱
- 协议提取与依赖注入
- 按职责拆分 God Object

## 可选证据验证
- 只要当前任务产出修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、构建脚本、plist / entitlements / xcconfig / scheme 或项目内环境配置），最终默认以定向测试/必要验证与 `code-review` 放行为收口；`final-evidence-gate` / `verify-ios-build` 仅在用户显式要求或需要补强完整项目环境证据时按需使用。
- 若执行可选完整验证，证据必须来自目标项目根目录的项目环境；沙箱内的构建结果不能作为完整项目环境证据。
- 对 iOS 项目，若升级到 `verify-ios-build`，必须优先 `.xcworkspace`（当 `.xcworkspace` 与 `.xcodeproj` 同时存在时），并默认优先已连接真机；找不到连接中的真机时再回退到 simulator。
- 若可选 `final-evidence-gate` / `verify-ios-build` 未执行或失败，应在交付中说明已执行的定向测试/审查证据与残余风险。

## 与其他技能的关系
- 非 SwiftUI 专项的大类重构优先使用本技能。
- 如果问题集中在已有 SwiftUI 视图文件结构、`body` 过长、子视图拆分或 Observation 用法，切换到 `swiftui-feature-implementation`。
- 如果任务重点是先找出问题和风险，而不是直接重构，优先使用 `code-review`。
