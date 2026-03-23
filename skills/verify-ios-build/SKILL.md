---
name: verify-ios-build
description: 在 iOS/Swift/Objective-C/Xcode 工程任务收尾阶段执行一次 `xcodebuild` 构建校验。适用于修改 `*.swift`、`*.m`、`*.mm`、`*.h`、`*.xib`、`*.storyboard`、`project.pbxproj`、`*.xcconfig`、`Package.swift`、`Podfile` 等会影响构建的文件，并且需要在任务结束前确认是否能编译通过的场景。不要在每次编辑后立即编译；只在本次实现完成、准备交付时使用。支持自动发现 workspace/project/scheme，并可通过仓库内 `.codex/xcodebuild.env` 覆盖默认构建参数。
---

# Verify iOS Build（任务收尾编译校验）

## 快速开始

当你已经完成 iOS 代码修改，并且需要在最终回复前确认当前仓库是否还能编译时，使用此技能。

这个技能的目标是：

- 只在任务收尾时执行一次 `xcodebuild`
- 默认自动发现 `.xcworkspace`、`.xcodeproj` 和共享 scheme
- 优先修复第一个真实编译错误，再重跑一次验证
- 如果构建受签名、Xcode 环境或沙箱限制阻塞，明确说明阻塞原因

## 触发规则

当满足以下任一条件时，执行构建校验：

- 本次任务修改了会影响 iOS 构建的文件
- 用户明确要求“编译验证”“构建检查”“跑一下 xcodebuild”
- 修改了 Xcode 工程配置、依赖配置或 scheme 相关文件

以下情况通常跳过构建：

- 纯文档修改
- 纯注释修改
- 纯分析、审查或方案讨论

## 工作流

1. 完成代码修改。
2. 在最终回复前运行 `scripts/build-check.sh`。
3. 如果构建失败，先定位第一个真实编译错误，不要被后续级联错误分散注意力。
4. 如果错误在本次任务范围内，修复后重跑一次 `scripts/build-check.sh`。
5. 在最终回复中说明：
   - 是否执行了构建
   - 使用了什么 workspace/project
   - 使用了什么 scheme
   - 构建是否通过
   - 如果未通过，阻塞点是什么

## 发现规则

脚本默认按以下优先级自动发现构建入口：

1. 仓库根目录下 `.codex/xcodebuild.env` 中的显式覆盖
2. 非 `Pods`、非 `project.xcworkspace` 的 `.xcworkspace`
3. 非 `Pods` 的 `.xcodeproj`
4. 共享 scheme 中第一个非测试 scheme

如果自动发现不准确，读取 `references/override-config.md`，让仓库提供一个 `.codex/xcodebuild.env`。

## 使用细节

- 默认使用 `Debug` 配置和 `generic/platform=iOS Simulator`
- 默认关闭代码签名：`CODE_SIGNING_ALLOWED=NO`、`CODE_SIGNING_REQUIRED=NO`
- 默认使用 `build`，而不是 `clean build`，避免无意义地拉长校验时间
- 如只需验证脚本推断是否正确，可设置 `XCODEBUILD_DRY_RUN=1`

## 参考文档

按需读取：

- `references/override-config.md`

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: verify-ios-build`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的配置规范与构建流程