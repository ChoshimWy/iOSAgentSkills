---
name: refactoring
description: 通用代码重构技能。用于处理长方法、重复代码、深层嵌套、回调地狱、God Object 等通用代码异味；如果目标是已有 SwiftUI 视图文件的结构化整理，应优先使用 `swiftui-view-refactor`；若任务产出修改了 Apple Xcode 项目相关内容，收尾必须切到 `verify-ios-build` 并在项目环境完成最终验证。
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

## 强制收尾验证
- 只要当前任务产出修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、构建脚本、plist / entitlements / xcconfig / scheme 或项目内环境配置），最终必须切到 `verify-ios-build`。
- 最终门禁必须在目标项目根目录的项目环境执行；沙箱内的构建结果不能作为最终验收结论。
- 对 iOS 项目，`verify-ios-build` 必须优先 `.xcworkspace`（当 `.xcworkspace` 与 `.xcodeproj` 同时存在时），并默认优先已连接真机；找不到连接中的真机时再回退到 simulator。
- 在 `verify-ios-build` 成功前，不得把任务表述为“已完成”；只能明确说明“实现已完成，但验证未完成/失败，任务未完成”。

## 与其他技能的关系
- 非 SwiftUI 专项的大类重构优先使用本技能。
- 如果问题集中在已有 SwiftUI 视图文件结构、`body` 过长、子视图拆分或 Observation 用法，切换到 `swiftui-view-refactor`。
- 如果任务重点是先找出问题和风险，而不是直接重构，优先使用 `code-review`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: refactoring`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel
