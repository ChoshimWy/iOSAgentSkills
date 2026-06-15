---
name: git-workflow
description: Git 通用工作流技能。用于分支命名、commit message、PR 描述模板、`.gitignore` 和常规 Git 操作规范；不负责使用 GitHub CLI（`gh`）一条龙执行提审流程，该场景交给 `gh-pr-flow`。
---

# Git 工作流

## Purpose

Provide general Git workflow rules for branch naming, commit messages, PR text templates, and safe local Git hygiene without taking over `gh` based PR execution.

## 中文说明

该 Skill 负责通用 Git 规范和提交文案质量。

## When to Use

- 需要创建或规范分支名。
- 需要编写 Conventional Commit。
- 需要整理 PR 描述模板或 `.gitignore`。
- 需要在不依赖 `gh` 的前提下执行常规 Git 操作。

## When Not to Use

- 用户明确要求使用 `gh` 完成暂存、提交、推送和开 PR 时。
- 任务主目标仍是代码评审、重构或调试时。

## Agent Rules

- 分支命名默认使用：

```text
feature/<ticket-id>-<简短描述>
bugfix/<ticket-id>-<简短描述>
hotfix/<ticket-id>-<简短描述>
release/<version>
refactor/<简短描述>
```

- Commit 使用 Conventional Commits：

```text
<type>(<scope>): [TAG] <subject>
```

- `TAG` 必须使用以下三者之一：
  - `[Codex-GENERATED]`：完全由 AI Agent 自动化生成，没有人工代码。
  - `[Codex-ASSIST]`：AI 辅助生成，人工参与决策或只生成部分代码。
  - `[HUMAN]`：完全由人工编写。
- `scope` 可包含空格；冒号后必须有一个空格，例如 `feat(Action Panel): [Codex-GENERATED] ...`。
- `subject` 中文、不加句号、单行长度不超过 72 字符。commit 强制单行，不允许正文（body）、脚注（footer）或 `Co-Authored-By` 尾注。
- 示例：

```text
feat(Action Panel): [Codex-GENERATED] 增加Action Panel主页面UI
refactor(Cue): [Codex-ASSIST] Cue增量更新重构
fix(bug): [HUMAN] 修复ONES bug #xxxxx
```

- PR 标题与正文默认使用中文；仅当目标仓库明确要求英文时再切换。
- 不要使用多个 `-m` 参数。
- 提交前检查 diff，避免调试代码、临时文件和敏感信息。

## Inputs

```json
{
  "goal": "Prepare Git workflow text or guidance",
  "change_summary": [],
  "ticket_id": "optional",
  "repo_constraints": [],
  "need_pr_template": false
}
```

## Outputs

```json
{
  "status": "completed | partial | blocked",
  "branch_suggestions": [],
  "commit_subjects": [],
  "pr_template_sections": [],
  "git_hygiene_notes": [],
  "next_action": "commit | gh-pr-flow | ask-user | blocked"
}
```

## Exit Conditions

- `completed`: usable branch, commit, or PR text guidance is ready.
- `partial`: some text guidance is ready but repo policy or scope is still ambiguous.
- `blocked`: repository conventions are too unclear to produce safe guidance.

## Escalation Rules

- Escalate to `gh-pr-flow` when the user explicitly requests `gh` based PR execution.
- Escalate to implementation, review, or debugging Skills when Git text is not the primary problem.

## Token Budget

- Do not paste large diffs only to derive commit text.
- Prefer short candidate branch names, one or two commit subjects, and a compact PR outline.

## Relationship to Other Skills

- Use this Skill for Git rules and text.
- Use `gh-pr-flow` for `gh` execution.
- Use it as a closing helper after implementation, testing, and review work.
