---
name: app-store-changelog
description: 根据最近一个 git tag（或指定 ref）以来的真实用户可见改动生成 App Store 更新文案。只用于发布文案整理；不要用于执行 Git 提交、创建 PR、构建配置或总结纯内部技术改动。
---

# App Store 更新文案

## Purpose

Generate App Store release notes from real user-visible changes while filtering out internal-only commits and preserving traceability to actual repo history.

## 中文说明

该 Skill 负责把 `git` 历史中的真实用户可见改动整理成可直接用于 App Store 的发布文案。

## When to Use

- 需要根据最近一个 tag 到当前版本之间的改动生成 `What's New`。
- 需要把技术提交改写成用户语言，并按“新增 / 优化 / 修复”归类。
- 需要从提交历史里筛掉构建、重构、依赖升级、CI 等纯内部改动。

## When Not to Use

- 需要提交代码、创建 PR、配置构建流程或决定发布策略时。
- 需要总结纯内部技术变更时。

## Agent Rules

- Prefer `scripts/collect_release_changes.sh` to collect candidate changes.
- Keep only user-visible changes in functionality, UX, behavior, performance, or stability.
- Treat ambiguous changes conservatively; do not overclaim user impact.
- Default output should be short, benefit-oriented, and free of internal jargon.
- Every release-note bullet should map back to a real underlying change.
- Prefer 3-8 bullets unless the user explicitly asks for another length.

## Inputs

```json
{
  "range": "last-tag..HEAD | explicit refs",
  "product_name": "optional",
  "character_limit": "optional",
  "language": "zh-CN by default"
}
```

## Outputs

```json
{
  "status": "completed | partial | blocked",
  "title": "optional",
  "release_notes": [],
  "source_range": "...",
  "excluded_change_types": [],
  "known_risks": [],
  "next_action": "none | ask-user | git-workflow | blocked"
}
```

## Exit Conditions

- `completed`: release notes are concise, user-facing, and traceable to real changes.
- `partial`: useful draft exists but history or release boundaries remain ambiguous.
- `blocked`: there is not enough repo history or user-visible change evidence to write trustworthy notes.

## Escalation Rules

- Escalate to `git-workflow` when the task becomes commit / branch / PR text preparation.
- Escalate to `gh-pr-flow` when the user explicitly asks for `gh` based PR execution.
- Escalate to `xcode-build` when the task becomes archive, signing, export, or CI release work.

## Token Budget

- Do not paste long commit histories.
- Prefer a compact list of user-visible bullets and a short exclusion rationale.
- Load detailed guidance from references only when wording rules are needed.

## Reference Resources

- `scripts/collect_release_changes.sh`
- `references/release-notes-guidelines.md`

## Relationship to Other Skills

- Use `git-workflow` for Git text and process work.
- Use `gh-pr-flow` for `gh` based PR execution.
- Use `xcode-build` for release pipeline, signing, archive, and export work.

