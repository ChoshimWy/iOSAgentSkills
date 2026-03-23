---
name: "gh-pr-flow"
description: "仅当用户明确要求使用 GitHub CLI（`gh`）一条龙完成暂存、提交、推送并创建 Pull Request 时使用；通用 Git 规范、commit 约定和 PR 模板仍由 `git-workflow` 负责。"
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
5. 用 `GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0 gh pr create --draft --fill --head $(git branch --show-current)` 创建草稿 PR。

## 输出要求
- PR 正文必须覆盖：问题、用户影响、根因、修复方式、测试或校验。
- PR 正文使用真实换行的 Markdown，不用 `\n` 字面量拼接。

## 与其他技能的关系
- 通用 Git 规范、branch / commit / PR 文案模板优先使用 `git-workflow`。
- 如果只是整理提交信息或拆 commit，不要使用本技能。
- 只有用户明确要求走 `gh` 一条龙时，才触发本技能。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: gh-pr-flow`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
