---
name: ios-build-log-digest
description: iOS 构建日志摘要 Skill。用于 xcodebuild build/test 失败后优先读取脚本生成的 verification-report.json，再按需读取 diagnostics.json、build-summary.txt、test-summary.json 或 xcresult 摘要，避免直接读取完整 build.log 或 DerivedData；不负责执行验证、判断最终证据充分性或运行时问题排查。
---

# iOS Build Log Digest

## Purpose

Reduce token usage when analyzing `xcodebuild` failures by forcing Agents to consume script-generated verification reports and structured diagnostics instead of raw build logs.

中文说明：该 skill 用于约束 Codex / Claude Code 在 iOS 构建失败后先读取本地脚本生成的 `verification-report.json`，避免把几十 MB 的 `xcodebuild` 日志塞进上下文。

## When to Use

Use this skill when:

- A build or test command failed.
- The build-queue daemon or digest script produced `verification-report.json`, `diagnostics.json`, `build-summary.txt`, `test-summary.json`, or an `.xcresult` bundle.
- An Agent is about to inspect a raw `build.log`.
- The user asks why verification consumes too many tokens.

## When Not to Use

- The issue is a runtime crash, hang, leak, or behavior bug; use `debugging`.
- The next step is to decide verification sufficiency rather than digest a failure artifact; use `final-evidence-gate`.
- No compact build/test artifact exists yet; use `testing` or `verify-ios-build` first.

## Agent Rules

- Never read full raw `xcodebuild` logs by default.
- Never paste large build logs into the conversation.
- Prefer `verification-report.json` first.
- Then read `diagnostics.json`.
- Then read `build-summary.txt`.
- Then read `test-summary.json`.
- Inspect `.xcresult` only through a compact summary command or pre-generated summary file.
- Do not recursively read `DerivedData`.
- Do not open full `.xcresult` dumps unless the user explicitly asks or summaries are insufficient.
- Fix only the first real blocking error before requesting another verification.
- Do not request another build without a code change or a clear reason.

## Preferred Inputs

Read files in this order:

1. `verification-report.json`
2. `diagnostics.json`
3. `build-summary.txt`
4. `test-summary.json`
5. `xcresult-summary.json`
6. Small targeted source file around the reported error location

## Inputs

```json
{
  "verification_report_path": "optional",
  "diagnostics_path": "optional",
  "summary_path": "optional",
  "test_summary_path": "optional",
  "xcresult_summary_path": "optional",
  "raw_log_path": "optional",
  "goal": "Digest the first real blocking build failure"
}
```

## Forbidden by Default

Do not read these unless explicitly required:

- `build.log`
- `xcodebuild.log`
- `raw-xcodebuild.log`
- full `xcresulttool get --format json` output
- recursive `DerivedData` logs
- all warnings
- unrelated SwiftCompile sections

## Diagnostics Contract

Expected `verification-report.json` shape:

```json
{
  "status": "failed",
  "mode": "unit",
  "fingerprint": "abc123",
  "cached": false,
  "summary": "swift_compile_error: App/File.swift:82 cannot find 'productID' in scope",
  "first_blocking_error": {
    "kind": "swift_compile_error",
    "file": "App/File.swift",
    "line": 82,
    "message": "Cannot find 'productID' in scope"
  },
  "failed_tests": [],
  "warnings_count": 0,
  "artifact_paths": {
    "diagnostics_json": "build-results/latest/diagnostics.json",
    "build_summary": "build-results/latest/build-summary.txt",
    "raw_log": "build-results/latest/build.log"
  },
  "suggested_next_action": "Fix the first real blocking error only, then request verification again.",
  "raw_log_policy": "forbidden_by_default",
  "needs_raw_log": false
}
```

Expected `diagnostics.json` shape:

```json
{
  "status": "failed",
  "mode": "build",
  "fingerprint": "abc123",
  "cached": false,
  "summary": "Swift compiler error in PurchaseViewModel.swift:82",
  "diagnostics": [
    {
      "kind": "swift_compile_error",
      "severity": "error",
      "file": "App/Subscription/PurchaseViewModel.swift",
      "line": 82,
      "column": 17,
      "message": "Cannot find 'productID' in scope",
      "target": "App"
    }
  ],
  "next_action": "Fix the first real compiler error only, then request verification again."
}
```

## Error Priority

When multiple diagnostics exist, handle them in this order:

1. Project configuration cannot load.
2. Missing dependency or module.
3. Swift compiler error.
4. Objective-C compiler error.
5. Linker error.
6. Test compile error.
7. Runtime test failure.
8. Warnings and non-blocking notes.

## Outputs

```json
{
  "status": "passed | failed | blocked | skipped",
  "summary": "...",
  "first_blocking_error": {
    "kind": "swift_compile_error",
    "file": "App/File.swift",
    "line": 10,
    "message": "..."
  },
  "evidence_source": "verification-report.json | diagnostics.json | build-summary.txt | test-summary.json | xcresult-summary.json",
  "known_risks": [],
  "next_action": "fix_first_error | verify_again | blocked | none"
}
```

## Response Format

When reporting a failure, keep it compact:

```text
Verification failed.
First blocking error: PurchaseViewModel.swift:82 cannot find `productID` in scope.
Next action: fix this error only, then re-request verification.
Raw log: skipped by policy.
```

## Anti-Patterns

Avoid:

- Reading the entire build log to find one compiler error.
- Asking for a full rebuild after only reading warnings.
- Fixing many unrelated warnings in the same loop.
- Summarizing all build output.
- Re-running verification without changing code.
- Treating simulator/device failures as required for every small Swift change.

## Exit Conditions

- `failed`: the first real blocking error is identified and summarized from compact evidence.
- `passed`: diagnostics indicate there is no blocking error left to summarize.
- `skipped`: no digest work is needed because another compact summary already resolved the failure.
- `blocked`: only unusable raw artifacts exist and no trustworthy compact evidence can be produced.

## Build-Queue Integration

The build-queue daemon should emit compact files:

```text
build-results/latest/ or build-queue job dir:
  verification-report.json
  diagnostics.json
  build-summary.txt
  test-summary.json
```

Agents should consume only these files unless escalation is justified.

## Escalation Rules

- Escalate to `verify-ios-build` when no fresh verification evidence exists yet.
- Escalate to `debugging` when the first failure is clearly a runtime crash, hang, or behavior issue instead of a build/test failure.
- Escalate to raw log inspection only when `verification-report.json` sets `needs_raw_log=true` or compact summaries are insufficient and the user explicitly asks.

## Token Budget

- Never read full raw `xcodebuild` logs by default.
- Prefer `verification-report.json`, then `diagnostics.json`, then `build-summary.txt`, then `test-summary.json`.
- Report only the first real blocking error relevant to the current change.

## Reference Resources

- `references/verification-report-schema.md`: schema and Agent reading order for script-generated verification evidence.

## Relationship to Other Skills

- Use `verify-ios-build` or `testing` to generate verification evidence.
- Use this Skill to digest failures before another verification request.
- Use `code-review` after failure attribution when the next decision is static risk assessment rather than rerun.
