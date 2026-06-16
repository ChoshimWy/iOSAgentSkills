---
name: "gh-pr-flow"
description: "仅当用户明确要求使用 GitHub CLI（`gh`）一条龙完成暂存、提交、推送并创建 Pull Request 时使用；通用 Git 规范、commit 约定和 PR 模板仍由 `git-workflow` 负责。默认使用中文 PR 标题与正文。"
---

# GitHub PR 一条龙流程

## Purpose

Execute a GitHub CLI based delivery flow that stages, commits, pushes, and opens a draft pull request with compact, review-ready metadata.

## 中文说明

该 Skill 只负责基于 `gh` 的提审执行流。

- 负责：检查 `gh` 可用性、整理提交、推送分支、创建草稿 PR。
- 不负责：定义通用 Git 规范、替代代码审查、替代构建验证结论。

## When to Use

- 用户明确要求使用 `gh` 完成 `git add`、`git commit`、`git push` 和 `gh pr create`。
- 目标是把当前改动整理成可审查的草稿 PR，而不是只做本地提交。

## When Not to Use

- 只需要分支命名、commit 文案或 PR 模板时；使用 `git-workflow`。
- 只需要本地提交，不需要 `gh pr create` 时。
- 任务仍处于实现、测试、审查阶段，尚未准备进入提审交付时。

## Agent Rules

- Only run this Skill when the user explicitly asks for a `gh` based PR flow.
- Always check `gh --version` and `gh auth status` first.
- Prefer a non-default working branch. If currently on the default branch, create a `codex/<description>` branch first.
- PR title and body default to Chinese unless the target repository clearly requires English.
- PR body must use real Markdown line breaks, not `\n` literals.
- Do not hide missing validation or unresolved review blockers in the PR description.

## Inputs

```json
{
  "goal": "Create draft PR with gh",
  "branch_name": "optional",
  "commit_subject": "required",
  "pr_title": "optional",
  "pr_body_outline": [],
  "validation_summary": [],
  "constraints": []
}
```

## Outputs

```json
{
  "status": "completed | blocked | partial",
  "branch_name": "...",
  "commit_subject": "...",
  "pr_title": "...",
  "pr_body_sections": [],
  "changed_files": [],
  "known_risks": [],
  "next_action": "push-and-open-pr | blocked | ask-user | none"
}
```

## Exit Conditions

- `completed`: branch, commit, push, and draft PR metadata are ready or executed successfully.
- `partial`: commit or PR text is prepared but final execution is intentionally deferred.
- `blocked`: `gh` unavailable, auth missing, branch/push blocked, or required validation/review state is unresolved.

## Escalation Rules

- Escalate to `git-workflow` when commit subject, branch naming, or PR template needs to be defined first.
- Escalate to `code-review` when review blockers or missing verification story prevent safe PR creation.
- Escalate to `xcode-build` / `ios-verification` only when the user explicitly asks to strengthen build confidence before opening the PR.

## Token Budget

- Do not paste full git diff or full PR body drafts multiple times.
- Prefer compact branch / commit / PR summaries.
- Only include the final PR title, key body sections, and validation summary.

## Relationship to Other Skills

- Use `git-workflow` for general Git rules, branch naming, commit conventions, and PR templates.
- Use this Skill only for the `gh` based execution path.
- Use implementation, testing, and review Skills before this Skill when code work is still in progress.

