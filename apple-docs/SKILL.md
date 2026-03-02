---
name: apple-docs
description: Apple 官方文档检索技能。当需要查询 Apple Developer Documentation、框架 API、平台兼容性、WWDC 视频与示例工程时使用。适用于 SwiftUI/UIKit/Objective-C/Swift 相关资料检索。
metadata: {"clawdbot":{"emoji":"🍎","requires":{"bins":["node"]}}}
---

# Apple 官方文档检索

## 适用场景
- 查询 Apple 官方 API 文档与符号定义
- 确认类/协议的平台可用性与版本要求
- 查找替代 API（如废弃接口替换建议）
- 搜索 WWDC 2014-2025 相关视频、主题与讲稿
- 浏览技术总览和示例工程

## 常用命令

### 文档检索
- `apple-docs search "关键词"`：搜索 Apple 文档
- `apple-docs symbols "UIView"`：按符号名检索类/结构体/协议
- `apple-docs doc "/documentation/..."`：按文档路径读取详情

### API 探索
- `apple-docs apis "UIViewController"`：查看继承链和协议遵循
- `apple-docs platform "UIScrollView"`：查看平台与版本兼容性
- `apple-docs similar "UIPickerView"`：查找推荐替代 API

### 技术与样例
- `apple-docs tech`：列出技术分类
- `apple-docs overview "SwiftUI"`：查看技术总览
- `apple-docs samples "Vision"`：查询示例工程

### WWDC 视频
- `apple-docs wwdc-search "async await"`：搜索会话
- `apple-docs wwdc-video 2024-100`：查看会话详情/讲稿/代码资源
- `apple-docs wwdc-topics`：查看主题分类
- `apple-docs wwdc-years`：查看年份与视频数量

## 常用选项
- `--limit <n>`：限制结果数量
- `--category`：按技术分类过滤
- `--framework`：按框架名过滤
- `--year`：按 WWDC 年份过滤
- `--no-transcript`：WWDC 结果中跳过讲稿
- `--no-inheritance`：`apis` 命令不返回继承信息
- `--no-conformances`：`apis` 命令不返回协议遵循信息

## 建议工作流
1. 先用 `search`/`symbols` 缩小范围
2. 再用 `doc`/`apis` 深挖细节与关系
3. 若是新技术学习，补充 `overview`/`samples`
4. 若涉及历史演进，用 `wwdc-search` + `wwdc-video` 交叉验证

## 输出要求
- 回答中优先给出：API 定义、平台可用性、官方建议替代方案
- 涉及版本差异时，明确标注平台与最低系统版本
- 对不确定结论，说明“基于当前检索结果”并给出可继续查证的命令

## 参考资源
- MCP Server: https://github.com/kimsungwhee/apple-docs-mcp
- Apple Developer Documentation: https://developer.apple.com/documentation/
- Apple Developer: https://developer.apple.com/

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: apple-docs`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel
