---
name: apple-docs
description: Apple 官方文档检索辅助技能。只在需要查询 Apple Developer Documentation、框架 API、平台可用性、WWDC 视频或示例工程时使用；不要把它当作默认主开发、重构、调试或构建技能。
metadata: {"clawdbot":{"emoji":"🍎","requires":{"bins":["node"]}}}
---

# Apple 官方文档检索

## 角色定位
- 辅助型 skill。
- 负责检索 Apple 官方 API、平台兼容性、WWDC 内容和示例工程，为其它 Apple 平台 skill 提供事实依据。
- 不负责主导实现代码、替代架构判断或直接承担调试、重构、构建配置任务。

## 适用场景
- 需要确认 Apple 官方 API 定义、可用性、废弃替代方案。
- 需要查询 SwiftUI、UIKit、Foundation、AppKit 等框架的官方说明。
- 需要追溯 WWDC 会话、示例工程或技术总览。
- 用户明确要求“查 Apple 官方文档”或需要最新官方依据时。

## 核心工作流
1. 先缩小搜索范围。
2. 读取官方详情。
3. 交叉核对历史资料。

## 输出要求
- 优先给出：API 定义、平台可用性、版本要求和官方建议替代方案。
- 回答中明确区分“官方文档事实”和“基于文档的推断”。
- 涉及版本差异时，必须标注平台与最低系统版本。
- 若当前检索结果不足以支持结论，直接说明缺口并给出下一步检索命令。

## 参考资源
- `cli.js`：Apple Docs MCP 命令入口。
- Apple Developer Documentation：`https://developer.apple.com/documentation/`
- Apple Developer：`https://developer.apple.com/`

## 与其他技能的关系
- 需要写或改 iOS/macOS 业务代码时，主技能应是 `ios-feature-implementation`、`swiftui-feature-implementation`、`uikit-feature-implementation`、`swift-expert`、`swiftui-ui-patterns`、`swiftui-liquid-glass` 或对应专项 skill，`apple-docs` 只作为辅助查询。
- 需要运行时排障时，切换到 `debugging`。
- 需要构建配置、签名、Archive 或 CI 时，切换到 `xcode-build`。
- 需要官方 API 依据来支撑其它技能的结论时，再附带使用本 skill。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: apple-docs`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel
