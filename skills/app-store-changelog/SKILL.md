---
name: app-store-changelog
description: 根据最近一个 git tag（或指定 ref）以来的真实用户可见改动生成 App Store 更新文案。只用于发布文案整理；不要用于执行 Git 提交、创建 PR、构建配置或总结纯内部技术改动。
---

# App Store 更新文案

## 角色定位
- 发布交付型 skill。
- 负责把 `git` 历史中的用户可见变更整理成可直接用于 App Store 的发布文案。
- 不负责提交代码、创建 PR、配置构建流程或替代发布负责人判断。

## 适用场景
- 需要根据最近一个 tag 到当前版本之间的改动生成 `What's New`。
- 需要把技术提交改写成用户语言，并按“新增 / 优化 / 修复”归类。
- 需要从提交历史里筛掉构建、重构、依赖升级、CI 等纯内部改动。

## 核心工作流
1. 收集变更
- 在仓库根目录运行 `scripts/collect_release_changes.sh`。
- 需要指定范围时使用 `scripts/collect_release_changes.sh v1.2.3 HEAD`。
- 如果仓库没有 tag，脚本会回退到完整历史。

2. 甄别用户影响
- 只保留用户可感知的功能、界面、行为、性能或稳定性变化。
- 丢弃纯内部改动，如构建脚本、重构、依赖升级、CI 调整、目录整理。
- 对是否“用户可见”存在歧义的改动，默认保守处理。

3. 撰写发布文案
- 每条只写一个用户收益点，句子短、动词明确、避免内部术语。
- 默认输出 5 到 10 条，除非用户明确要求更短或更长。
- 优先描述结果和收益，而不是实现细节。

4. 交叉校验
- 确认每条文案都能回溯到真实改动。
- 去重，避免把一件事拆成多条。
- 若提交历史不足以判断影响范围，明确标注不确定性。

## 参考资源
- `scripts/collect_release_changes.sh`：收集最近 tag 以来的提交和触达文件。
- `references/release-notes-guidelines.md`：App Store 文案的语言、筛选和校验规则。

## 输出要求
- 可选标题使用 `What's New` 或“产品名 + 版本号”。
- 正文默认使用项目符号列表，每条一句。
- 如果用户给出商店字数限制，必须遵守。
- 默认把原始提交改写成用户语言，例如：

| 原始提交 | App Store 文案 |
| --- | --- |
| `fix(auth): resolve token refresh race condition on iOS 17` | `• 修复了部分用户会被意外登出的登录问题。` |
| `feat(search): add voice input to search bar` | `• 新增语音输入，让搜索更方便。` |
| `perf(timeline): lazy-load images to reduce scroll jank` | `• 优化图片加载后，时间线滚动更流畅。` |

## 与其他技能的关系
- 需要提交代码、整理分支、编写 commit 或 PR 描述时，切换到 `git-workflow`。
- 用户明确要求用 `gh` 一次性 `stage + commit + push + open PR` 时，切换到 `gh-pr-flow`。
- 需要配置 Archive、导出 IPA、签名或 CI 发布链路时，切换到 `xcode-build`。
- 这里只整理发布文案，不替代实际构建验证或发布操作。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: app-store-changelog`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
