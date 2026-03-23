---
name: "yeet"
description: "仅当用户明确要求使用 GitHub CLI（`gh`）一条龙完成暂存、提交、推送并创建 GitHub Pull Request 时使用。"
---

# GitHub 一条龙提交流程

## 适用场景
- 用户明确要求一次性完成 `git add`、`git commit`、`git push` 和 `gh pr create`。
- 任务目标是“把当前改动整理成可审查的 PR”，而不是仅做本地提交。

## 核心规则
- 必须先确认 `gh` 可用并已登录。
- 如果当前在 `main` / `master` / 默认分支上，先创建功能分支。
- 提交信息保持简短明确；PR 标题和正文要覆盖完整变更影响。
- 推送失败时先排查认证或远端同步问题，再重试。

## 工作流
1. 检查前置条件
- 运行 `gh --version`；缺失时要求用户先安装 `gh`。
- 运行 `gh auth status`；未登录时要求用户先执行 `gh auth login`。

2. 规范命名
- 分支名默认使用 `codex/{description}`。
- commit message 默认使用 `{description}`。
- PR 标题默认使用 `[codex] {description}`。

3. 执行提交流程
- 如果当前位于默认分支，创建新分支：

```bash
git checkout -b "codex/{description}"
```

- 否则保留当前分支。
- 确认状态并暂存变更：

```bash
git status -sb
git add -A
```

- 用简短描述提交：

```bash
git commit -m "{description}"
```

- 如未执行检查，先运行必要检查；如果因缺少依赖或工具失败，安装后重试一次。
- 推送并建立跟踪：

```bash
git push -u origin $(git branch --show-current)
```

- 如果 `git push` 因工作流鉴权失败，先同步默认分支后再重试。
- 创建草稿 PR：

```bash
GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 gh pr create --draft --fill --head $(git branch --show-current)
```

- PR 正文应写入临时文件（如 `pr-body.md`），避免 `\n` 转义破坏 Markdown。

## 输出要求
- PR 正文必须是完整 prose，至少覆盖：
  - 问题是什么。
  - 用户层面的影响是什么。
  - 根因是什么。
  - 修复方式是什么。
  - 使用了哪些测试或校验。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: yeet`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
