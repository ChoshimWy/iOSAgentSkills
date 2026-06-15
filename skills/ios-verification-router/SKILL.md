---
name: ios-verification-router
description: iOS 验证路由 Skill。用于在请求 Xcode build/test 前按 diff 类型选择最低有效验证等级、wrapper 入口和重复验证抑制策略；适用于 iOS 项目验证慢、token 消耗高或多 Agent 共享 build-queue daemon 的场景，不替代 testing、final-evidence-gate 或 verify-ios-build。
---

# iOS Verification Router

## Purpose

Choose the cheapest valid verification path before requesting any Xcode build or test.

中文说明：该 skill 用于减少多 Agent iOS 工作流中的无效编译、重复验证和 token 浪费。它不替代 build-queue daemon，而是在请求 daemon 之前完成 diff 分型、验证级别选择与重复请求抑制。

## When to Use

Use this skill when:

- An Agent is about to request any Xcode verification and the cheapest valid mode is still unclear.
- The task changed Swift, Objective-C, Xcode project, dependency, test, UI, asset, or configuration files.
- The user complains that xcodebuild is slow or consumes too many tokens.
- Multiple Agents share a build-queue daemon.

Do not use this skill for pure product discussion, UI mockup writing, or documentation-only tasks unless the user explicitly asks for verification policy changes.
Do not use this skill to replace `testing`, `final-evidence-gate`, or `verify-ios-build`; it selects the route but does not author tests, decide final evidence sufficiency, or execute project-environment verification.

## Agent Rules

- Never run `xcodebuild` directly.
- Never request full verification by default.
- Always prefer the target project wrapper: `./codex_verify.sh` when it exists.
- Otherwise use the shared fallback wrapper: `~/.codex/bin/codex_verify`.
- Prefer `--mode auto` unless the user explicitly requests a stronger mode.
- Do not escalate to simulator, real-device, UI test, archive, or full test verification unless the diff requires it.
- If a previous verification result exists for the same fingerprint, read that cached diagnostics result before requesting another build.
- If no code or runtime-affecting files changed, do not request `xcodebuild`.
- If verification fails, fix only the first real blocking error before requesting another verification.
- Never read full raw build logs by default. Use `diagnostics.json` first.

## Diff Classification

Classify changed files before verification:

| Diff Type | Examples | Default Verification |
| --- | --- | --- |
| `doc-only` | `*.md`, docs, comments only | no xcodebuild |
| `rule-only` | `AGENTS.md`, `SKILL.md`, lint policy docs | policy lint or no xcodebuild |
| `asset-only` | images, colors, json fixtures with no runtime loader change | no xcodebuild or resource check |
| `swift-small` | one or a few Swift files with narrow ownership | targeted build or affected tests |
| `swift-risky` | service, persistence, concurrency, subscription, networking, BLE, database | affected tests + build |
| `ui-only` | SwiftUI/UIKit view changes | build; UI tests only if explicit or existing targeted UI test is cheap |
| `test-only` | test files only | targeted `-only-testing` |
| `project-config` | `.xcodeproj`, `.xcworkspace`, `Package.resolved`, `Podfile`, build settings | full build, clean build only if required |
| `dependency` | package or pod dependency version changes | full build |
| `release` | archive/export/signing changes | archive/export validation path |

## Verification Modes

Use the smallest sufficient mode:

| Mode | Meaning |
| --- | --- |
| `none` | No build is needed. Explain why. |
| `lint` | Static policy or style check only. |
| `typecheck` | Lightweight source validation where supported. |
| `build` | Build the affected target only. |
| `unit` | Run targeted unit tests with `-only-testing`. |
| `ui` | Run targeted UI tests only when explicitly justified. |
| `full` | Full project build/test for release, merge, dependency, or project config risk. |

## Request Shape

When asking the build-queue daemon or wrapper for verification, prefer a structured request:

```json
{
  "mode": "auto",
  "reason": "Changed subscription ViewModel and service logic",
  "changed_files": [
    "App/Subscription/PurchaseViewModel.swift",
    "App/Subscription/SubscriptionService.swift"
  ],
  "allow_full_build": false,
  "allow_full_log": false,
  "prefer_cached_result": true
}
```

## Inputs

```json
{
  "changed_files": [],
  "goal": "Choose the cheapest valid verification route",
  "workspace": "optional",
  "scheme": "optional",
  "previous_verification": {},
  "constraints": []
}
```

## Outputs

```json
{
  "status": "passed | skipped | blocked",
  "mode": "none | lint | typecheck | build | unit | ui | full",
  "reason": "...",
  "changed_files": [],
  "prefer_cached_result": true,
  "allow_full_build": false,
  "allow_full_log": false,
  "next_action": "testing | verify-ios-build | code-review | none | blocked"
}
```

## Required Output Back to User

When reporting verification choices, keep the response short:

```text
Verification route: affected unit tests + build
Reason: service and ViewModel changed; no project or dependency config changed.
Full build: skipped
Log policy: diagnostics.json only
```

## Escalation Rules

Escalate to stronger verification only when:

- The previous cheaper verification passed and the user requests merge/release confidence.
- Project or dependency configuration changed.
- The failure cannot be explained from `diagnostics.json` or `build-summary.txt`.
- The changed code affects runtime integration that has no meaningful unit-level coverage.

## Token Budget

- Do not paste large logs.
- Do not recursively inspect `DerivedData`.
- Do not open full `.xcresult` dumps.
- Prefer one concise diagnostics object over raw command output.
- Summarize only actionable errors and skipped validation reasons.

## Exit Conditions

- `passed`: the smallest sufficient verification mode is selected with a clear reason.
- `skipped`: no Xcode verification is needed because the diff is doc-only, rule-only, or otherwise non-runtime-affecting.
- `blocked`: changed files or repository context are too unclear to choose a safe verification route.

## Relationship to Other Skills

- Use `ios-affected-tests` when exact `-only-testing` candidates are non-trivial.
- Use `testing` when test code or targeted XCTest execution becomes the next step.
- Use `verify-ios-build` when a stronger project-environment verification path is explicitly required.
- Use `ios-build-log-digest` when a verification failure needs compact attribution.
