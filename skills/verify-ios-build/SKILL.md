---
name: verify-ios-build
description: 仅在 iOS/Swift/Objective-C/Xcode 工程任务收尾阶段执行一次 `xcodebuild` 构建校验。用于最终确认当前仓库仍能编译；不负责 Build Settings、签名、Archive/Export 或 CI/CD 配置，这些场景交给 `xcode-build`。
---

# Verify iOS Build（任务收尾编译校验）

## 角色定位
- 验证型 skill。
- 只负责任务末尾的一次性 `xcodebuild` 编译验收。
- 不负责构建系统设计、签名配置或 Archive/Export 流程。

## 适用场景
- 本次任务修改了会影响 iOS 构建的文件。
- 用户明确要求“编译验证”“构建检查”“跑一下 xcodebuild”。
- 在最终回复前需要确认当前仓库仍能编译。

## 核心工作流
1. 完成实现后运行 `scripts/build-check.sh`。
2. 构建失败时先抓第一个真实编译错误。
3. 如果错误在本次任务范围内，修复后重跑一次。
4. 最终回复中明确说明 workspace/project、scheme、结果和阻塞点。

## 参考资源
- `references/override-config.md`

## 与其他技能的关系
- 当任务已经实现完成，需要在最终回复前确认“还能编译”时，优先使用本技能。
- 如果任务本身是在改 Build Settings、签名、Archive/Export、CI 或构建脚本，主技能应是 `xcode-build`。
- 本技能不替代测试编写；需要补单元测试或 UI 测试时切换到 `testing`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: verify-ios-build`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的配置规范与构建流程
