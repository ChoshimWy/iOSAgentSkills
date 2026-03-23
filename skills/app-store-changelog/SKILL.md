---
name: app-store-changelog
description: 根据最近一个 git tag（或指定 ref）以来的变更，汇总并撰写面向用户的 App Store 更新文案。当用户要求生成完整版本更新说明、App Store“What's New”内容或基于 git 历史的发布文案时使用。
---

# App Store 更新文案

## 适用场景
- 需要根据 git 历史生成面向用户的 App Store 更新说明。
- 需要把技术提交整理成可读、可发布的“新增 / 优化 / 修复”文案。
- 需要在最近一个 tag 到当前版本之间筛出真正对用户可见的改动。

## 工作流
1. 收集变更
- 在仓库根目录运行 `scripts/collect_release_changes.sh`。
- 需要指定范围时使用 `scripts/collect_release_changes.sh v1.2.3 HEAD`。
- 如果仓库没有 tag，脚本会回退到完整历史。

2. 甄别用户影响
- 结合提交信息和改动文件，筛出用户可感知的功能、界面、行为、性能或稳定性变化。
- 按主题分组，如“新增”“优化”“修复”。
- 丢弃纯内部改动，如构建脚本、重构、依赖升级、CI 调整。

3. 撰写 App Store 文案
- 每条只写一个用户收益点，句子短、动词明确、避免内部术语。
- 默认输出 5 到 10 条，除非用户明确要求更短或更长。
- 优先描述结果和收益，而不是实现细节。

4. 校验
- 确认每条文案都能回溯到真实改动。
- 去重，避免同一件事拆成多条。
- 遇到是否“用户可见”存在歧义的改动，先保守处理或向用户确认。

## 参考资源
- `scripts/collect_release_changes.sh`：收集自最近 tag 以来的提交和触达文件。
- `references/release-notes-guidelines.md`：App Store 更新文案的语言、筛选和校验规则。

## 输出要求
- 可选标题使用 `What's New` 或“产品名 + 版本号”。
- 正文默认使用项目符号列表，每条一句。
- 如果用户给出商店字数限制，必须遵守。
- 将原始提交转换为用户语言，例如：

| 原始提交 | App Store 文案 |
| --- | --- |
| `fix(auth): resolve token refresh race condition on iOS 17` | • 修复了部分用户会被意外登出的登录问题。 |
| `feat(search): add voice input to search bar` | • 新增语音输入，让搜索更方便。 |
| `perf(timeline): lazy-load images to reduce scroll jank` | • 优化图片加载后，时间线滚动更流畅。 |

- 下列仅内部提交默认丢弃：
  - `chore: upgrade fastlane to 2.219`
  - `refactor(network): extract URLSession wrapper into module`
  - `ci: add nightly build job`

示例输出：

```text
What's New in Version 3.4

• 新增语音输入，让搜索更方便。
• 优化图片加载后，时间线滚动更流畅。
• 修复了部分用户会被意外登出的登录问题。
• 设置页新增深色模式支持。
• 打开大型相册时的加载速度更快。
```

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: app-store-changelog`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
