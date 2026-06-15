---
name: refactoring
description: 通用代码重构技能。用于处理长方法、重复代码、深层嵌套、回调地狱、God Object 等通用代码异味；如果目标是已有 SwiftUI 视图文件的结构化整理，应优先使用 `swiftui-feature-implementation`；若任务产出修改了 Apple Xcode 项目相关内容，默认以定向测试/必要验证与独立 reviewer subAgent `code-review` 放行为收口；`final-evidence-gate` / `verify-ios-build` 仅在用户显式要求或需要补强完整项目环境证据时按需使用。
---

# 代码重构

## Purpose

Refactor general-purpose code smells with minimal behavior change, small safe steps, and clear validation handoff.

## 中文说明

该 Skill 负责与框架无关的通用代码异味重构。

- 适用于：长方法、重复逻辑、深层嵌套、回调地狱、God Object、协议提取与依赖注入。
- 不适用于：SwiftUI 视图专项整理、纯代码审查、运行时排障。

## When to Use

- 函数过长、参数过多、重复逻辑、深层嵌套。
- 需要把回调迁移到 async/await。
- 需要拆分类、提取协议、引入策略模式或依赖注入。

## When Not to Use

- 任务核心是已有 SwiftUI 视图结构化整理；使用 `swiftui-feature-implementation`。
- 任务核心是先找出问题和风险，而不是直接改动；使用 `code-review`。
- 任务核心是 crash、泄漏、卡顿定位；使用 `debugging` 或 `ios-performance`。

## Agent Rules

- Keep refactoring changes behavior-preserving by default.
- Do not mix feature work into refactoring-only changes.
- Move in small steps and preserve or improve the validation story.
- Prefer seams that improve readability, ownership, and testability without over-abstracting.
- When editing code, preserve or improve necessary comments on touched public APIs, reusable abstractions, complex branches, side effects, and failure paths.
- Update stale comments and avoid adding comments that only restate the refactored code.
- If code changes are produced, final closure follows targeted validation / necessary verification plus independent reviewer subAgent `code-review`; the refactoring Agent must not self-review.

## Inputs

```json
{
  "goal": "Refactor code safely",
  "changed_area": [],
  "smells": [],
  "constraints": ["minimal behavior change"],
  "existing_tests": []
}
```

## Outputs

```json
{
  "status": "completed | partial | blocked",
  "changed_files": [],
  "summary": [],
  "refactoring_patterns": [],
  "known_risks": [],
  "test_impact": "...",
  "no_test_reason": null,
  "next_action": "testing | code-review | ask-user | blocked"
}
```

## Exit Conditions

- `completed`: refactoring intent, changed files, risk, and validation handoff are clear.
- `partial`: useful decomposition is done but more passes are intentionally deferred.
- `blocked`: behavior cannot be preserved safely, ownership is unclear, or no validation path exists.

## Escalation Rules

- Escalate to `swiftui-feature-implementation` for SwiftUI-specific structural cleanup.
- Escalate to `code-review` when the next step is risk discovery rather than direct refactoring.
- Escalate to `swift-expert` when abstraction, concurrency, or language-level redesign becomes the main problem.

## Token Budget

- Do not paste large before/after diffs.
- Prefer concise smell descriptions, chosen refactoring patterns, and validation handoff.
- Avoid broad unrelated cleanup in the same pass.

## Relationship to Other Skills

- Use `swiftui-feature-implementation` for SwiftUI view structure refactors.
- Use `code-review` for static risk discovery.
- Use `testing` for targeted validation and new test seams.
- Use `swift-expert` for deeper language and abstraction design.
