---
name: "gh-pr-flow"
description: "仅当用户明确要求使用 GitHub CLI（`gh`）一条龙完成暂存、提交、推送并创建 Pull Request 时使用；通用 Git 规范、commit 约定和 PR 模板仍由 `git-workflow` 负责。默认使用中文 PR 标题与正文。"
---

# GitHub PR 一条龙流程

## 角色定位
- 发布交付型 skill。
- 只负责基于 `gh` 的提审执行流。
- 不负责通用 Git 规范定义。

## 适用场景
- 用户明确要求用 `gh` 完成 `git add`、`git commit`、`git push` 和 `gh pr create`。
- 目标是把当前改动整理成可审查 PR，而不是只做本地提交。

## 核心工作流
1. 先检查 `gh --version` 与 `gh auth status`。
2. 如在默认分支，创建 `codex/{description}` 分支。
3. 执行 `git status -sb`、`git add -A`、`git commit -m "{description}"`。
4. 运行必要检查，再执行 `git push -u origin $(git branch --show-current)`。
5. 准备中文 PR 标题与正文，其中正文写入 `/tmp/pr-body.md`，并使用真实换行 Markdown。
6. 用 `GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 gh pr create --draft --title "<中文 PR 标题>" --body-file /tmp/pr-body.md --head $(git branch --show-current)` 创建草稿 PR。

## 输出要求
- PR 标题默认使用中文，简洁描述“做了什么 + 影响范围”。
- PR 正文默认使用中文，至少覆盖：概述、问题与根因、改动详情、用户影响、测试或校验、风险与回滚、关联 Issue。
- PR 正文使用真实换行的 Markdown，不用 `\n` 字面量拼接。
- 若目标仓库强制英文模板，按仓库规范切换并在回复中说明原因。

## 与其他技能的关系
- 通用 Git 规范、branch / commit / PR 文案模板优先使用 `git-workflow`。
- 如果只是整理提交信息或拆 commit，不要使用本技能。
- 只有用户明确要求走 `gh` 一条龙时，才触发本技能。

