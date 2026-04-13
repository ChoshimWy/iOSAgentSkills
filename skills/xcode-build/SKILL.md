---
name: xcode-build
description: Xcode 构建与配置技能。只用于 Xcode 项目配置、Build Settings、构建脚本、Archive/Export、CI/CD、代码签名和分发链路；如果任务只是收尾阶段跑一次 `xcodebuild` 验收、选择 Simulator / 真机执行路径或编写测试，不要使用本 skill 作为主 skill。
---

# Xcode 构建与配置

## 角色定位
- 专项型 skill。
- 负责构建系统设计、签名、Archive/Export 和 CI/CD 配置。
- 不负责任务末尾的一次性编译验收。

## 触发判定（硬边界）
- 用户主要在问 `Build Settings`、scheme、xcconfig、签名、证书、Archive、导出、CI/CD、XCFramework 或构建脚本时，使用本 skill。
- 如果只是任务完成后的单次门禁构建，不要用本 skill 作为主 skill，切换到 `verify-ios-build`。
- 如果任务重点是“在哪台 Simulator / 真机上执行”，而不是“如何配置构建链路”，切换到 `ios-simulator-automation` 或 `ios-device-automation`。

## 适用场景
- 调整 `Build Settings`、scheme、xcconfig 和构建脚本。
- 处理签名、证书、配置文件、Archive 和 IPA 导出。
- 设计或修改 CI/CD 中的 `xcodebuild` 流程。
- 处理 XCFramework 打包和构建性能优化。

## 核心工作流
1. 先明确入口：`workspace` / `project` / `scheme`。
2. 再确认配置目标：本地构建、Archive、导出、CI 或签名。
3. 最后根据目标选择 `build`、`test`、`archive` 或 `-exportArchive` 流程。
4. 如果需要为目标项目新增 `.swift`、`.h`、`.m`、`.mm` 等源码文件且项目要求文件头，`Created by` 必须使用本机用户名称 `Choshim.Wei`，不要写 `Codex`；日期默认使用 `YYYY/M/D`，例如 `Created by Choshim.Wei on 2026/4/11.`。

## 参考资源
- `references/build-settings.md`
- `references/ci-templates.md`

## 与其他技能的关系
- 当任务是配置 Build Settings、签名、Archive/Export、CI/CD 或构建脚本时，优先使用本技能。
- 如果只是本次实现完成后跑一次 `xcodebuild` 做收尾验证，切换到 `verify-ios-build`。
- 如果任务是 SDK 分发策略、模块边界或 XCFramework 设计层面，优先结合 `sdk-architecture` 使用。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: xcode-build`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel
