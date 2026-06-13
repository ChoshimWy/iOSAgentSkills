# iOS Build Log Digest

## Purpose

Reduce token usage when analyzing `xcodebuild` failures by forcing Agents to consume structured diagnostics instead of raw build logs.

中文说明：该 skill 用于约束 Codex / Claude Code 在 iOS 构建失败后只读取摘要文件，避免把几十 MB 的 `xcodebuild` 日志塞进上下文。

## When to Use

Use this skill when:

- A build or test command failed.
- The build-queue daemon produced `diagnostics.json`, `build-summary.txt`, `test-summary.json`, or an `.xcresult` bundle.
- An Agent is about to inspect a raw `build.log`.
- The user asks why verification consumes too many tokens.

## Agent Rules

- Never read full raw `xcodebuild` logs by default.
- Never paste large build logs into the conversation.
- Prefer `diagnostics.json` first.
- Then read `build-summary.txt`.
- Then read `test-summary.json`.
- Inspect `.xcresult` only through a compact summary command or pre-generated summary file.
- Do not recursively read `DerivedData`.
- Do not open full `.xcresult` dumps unless the user explicitly asks or summaries are insufficient.
- Fix only the first real blocking error before requesting another verification.
- Do not request another build without a code change or a clear reason.

## Preferred Inputs

Read files in this order:

1. `diagnostics.json`
2. `build-summary.txt`
3. `test-summary.json`
4. `xcresult-summary.json`
5. Small targeted source file around the reported error location

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

## Build-Queue Integration

The build-queue daemon should emit compact files:

```text
build-results/
  latest/
    diagnostics.json
    build-summary.txt
    test-summary.json
```

Agents should consume only these files unless escalation is justified.
