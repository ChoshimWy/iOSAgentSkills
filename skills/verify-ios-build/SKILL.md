---
name: verify-ios-build
description: Apple Xcode 工程的按需项目环境构建验证执行器。由用户显式要求或 final-evidence-gate 在现有 xcodebuild test/build 证据不足、高风险场景下调用；通过 codex_verify wrapper 接入 shared build-queue daemon 执行一次项目环境 xcodebuild 验证，并优先输出 verification-report.json / diagnostics.json / build-summary.txt 等低 token 证据。
---

# Verify iOS Build（项目环境构建验证执行器）

## Purpose

Execute one on-demand project-environment Xcode verification for Apple platform projects while preserving build-queue serialization, stable validation baselines, structured diagnostics, and low-token failure reporting.

## 中文说明

该 Skill 是按需项目环境验证执行器，不是所有 iOS / Xcode 改动的默认收尾步骤。

它负责在用户显式要求、发布前检查、或 `final-evidence-gate` 判定现有证据不足 / 风险较高时，执行一次真实项目环境 `xcodebuild` 验证。验证必须通过项目 wrapper 或全局 wrapper 接入 shared build-queue daemon，避免多个 Agent 并发裸跑 `xcodebuild`。

本 Skill 不负责：

- 默认 testing 后继步骤。
- 判断低风险任务是否可接受已有证据。
- 编写测试代码。
- 构建系统设计、签名配置、Archive、Export、CI/CD 策略。
- 全量 diff / PR 审查。

这些分别由 `testing`、`final-evidence-gate`、`xcode-build`、`code-review` 等 Skill 负责。

## When to Use

Use this Skill when:

- The user explicitly asks for build verification, `xcodebuild`, final compile check, or project-environment verification.
- `final-evidence-gate` escalates because existing `xcodebuild build/test` evidence is insufficient.
- The change is high-risk and needs one real project-environment build/test signal.
- The change touches project configuration, scheme, xctestplan, xcconfig, Build Settings, build scripts, plist, entitlements, capabilities, assets, target membership, dependency configuration, or consumer app integration.
- The last successful validation evidence is older than the latest code change.
- A release / merge confidence gate requires project-environment evidence.

## When Not to Use

Do not use this Skill when:

- The task only needs unit test authoring or test scope selection; use `testing` or `ios-affected-tests`.
- The task is build system design, signing, certificate, Archive, Export, CI, xcconfig, build script, or destination policy work; use `xcode-build`.
- The task only requires code review; use `code-review`.
- The task only requires simulator / device automation, install, launch, screenshots, or UI flow validation; use `ios-automation`.
- A same-or-stronger successful project-environment build/test already exists after the latest code change, and `testing` plus `code-review` already passed.
- The repository is not an Xcode project.
- The user has not asked for full verification and the diff is low-risk with adequate targeted evidence.

## Agent Rules

### Execution Boundaries

- Treat this Skill as an on-demand executor, not the default final step for every Apple platform change.
- Confirm preceding `testing` and `code-review` status when this Skill is used as a final gate executor.
- If invoked by `final-evidence-gate`, record the escalation reason.
- Do not bypass `testing` / `code-review` by changing `.codex/xcodebuild.env`.
- Do not review the entire diff inside this Skill; that belongs to `code-review`.
- Do not design signing, archive, export, CI, or build setting strategies inside this Skill; route to `xcode-build`.
- Do not write or modify test code inside this Skill; route to `testing`.

### Wrapper and Build Queue Rules

- Never run validation-type `xcodebuild` directly.
- Always prefer the target project repo-tracked wrapper: `./codex_verify.sh`.
- If the target project wrapper is absent, use the shared fallback wrapper: `~/.codex/bin/codex_verify`.
- The wrapper must submit validation-type `xcodebuild` to the shared build-queue daemon.
- The wrapper / build-check script must own formatter selection, missing-tool installation, structured parsing, redaction, and artifact generation. Agents must not manually install or invoke `xcbeautify`, `xcpretty`, `xcprint`, `xcresulttool`, or similar formatter/parser tools.
- External formatter/parser output is an intermediate input only. The Agent-facing contract is still `verification-report.json` -> `diagnostics.json` -> summaries.
- Formatter bootstrap must preserve the real `xcodebuild` exit code; formatter success must never turn a failing verification into success.
- The daemon serializes `xcodebuild` and reuses Xcode system DerivedData（Xcode 系统 DerivedData）: `~/Library/Developer/Xcode/DerivedData`.
- Do not reintroduce public `XCODE_DERIVED_DATA_*` or `CODEX_DERIVED_DATA_SLOT` configuration. If those variables are present, wrapper should fail fast.
- Project-environment verification must run in the target project root, not in a sandbox copy.
- For Codex, use non-sandbox project execution with required escalation when necessary.

### Baseline Selection Rules

- If `.codex/xcodebuild.env` explicitly sets `XCODE_DESTINATION`, use that destination.
- If an iOS project has both `.xcworkspace` and `.xcodeproj`, prefer `.xcworkspace`.
- If earlier validation in the same task already used a workspace / scheme / destination, reuse that baseline unless there is a clear reason to change.
- For private Pod / private component changes, keep the main project on the local `:path` dependency for project-environment verification unless the user explicitly asks to restore versioned dependency.
- If no `XCODE_SCHEME` is explicit, prefer a scheme bound to unit test targets / bundles such as `*Tests`.
- If no test-bound scheme exists, fall back to another test-related scheme such as `*UITests` or `*_TEST`.
- For iOS projects with no explicit destination, prefer connected physical iOS devices.
- If no connected physical iOS device exists, fall back to simulator.
- For macOS Xcode projects, use host `xcodebuild build` and do not force iOS destinations.

### Device Selection Rules

- Real-device selection must be based on `xcodebuild -showdestinations` and `xcrun devicectl list devices`.
- Only `connected` devices can be selected by default.
- Do not treat paired but disconnected devices as default final verification targets.
- If simulator verification fails, switch to real device only when the first real failure matches a known simulator-only third-party dependency/linking allowlist issue.
- If the simulator failure is a real implementation error, do not switch to real device.
- If real-device fallback is required but no connected iOS destination exists, report a blocked state with the reason.

### UI Smoke Rules

Run UI smoke only when all conditions are met:

- First build verification succeeded.
- `XCODE_UI_SMOKE_MODE=auto|required`.
- The diff touches UI-sensitive files: View, ViewController, Router, Coordinator, Storyboard, XIB, Assets.
- First destination is simulator.
- `XCODE_UI_SMOKE_SPEC` exists. Default: `.codex/ui-smoke.yml`.

UI smoke must be text-first:

- Prefer structured accessibility tree assertions.
- Use screenshots only as visual evidence or failure artifacts.
- Screenshots must not be the only state assertion.

### Token Budget

- Prefer structured output from wrapper / daemon.
- Prefer script-generated artifacts over formatter output. Do not inspect `formatted-build.log` unless `verification-report.json` asks for it.
- Read `verification-report.json` first.
- Then read `diagnostics.json`.
- Then read `build-summary.txt`.
- Then read `test-summary.json` or `xcresult-summary.json` if available.
- Do not read full raw `build.log` by default.
- Do not dump full `.xcresult` JSON by default.
- Do not recursively inspect `DerivedData`.
- Report only the first real blocking error when verification fails.
- Do not paste large build logs into the conversation.

## Core Workflow

1. Confirm trigger source: user explicit request, `final-evidence-gate` escalation, release / merge confidence, or high-risk project-environment evidence need.
2. Confirm preceding `testing` and `code-review` status if this is a final verification path.
3. Determine target project root and confirm it is an Xcode project.
4. Determine wrapper path: `./codex_verify.sh` first, then `~/.codex/bin/codex_verify`.
5. Determine verification mode and baseline: workspace/project, scheme, configuration, destination.
6. Let the wrapper / script bootstrap formatter tooling if needed; do not let the Agent choose or install tools.
7. Compute or request verification fingerprint if supported by wrapper / daemon.
8. If the same fingerprint already has a same-or-stronger successful result, skip duplicate build and report cached evidence.
9. If the same fingerprint already has a failed result, read cached `verification-report.json` before requesting another build.
10. Submit one verification request through wrapper / daemon.
11. Read structured result artifacts, starting with `verification-report.json`.
12. If failed, report first real blocking error and next action.
13. If succeeded and UI smoke conditions are met, run UI smoke through the supported wrapper path.
14. Return compact verification evidence and residual risk.

## Verification Fingerprint

When wrapper / daemon supports fingerprinting, use a stable key based on:

```text
sha256(diff + workspace/project + scheme + configuration + destination + verification mode + xcode version if available)
```

Rules:

- Same fingerprint + successful same-or-stronger evidence: do not rebuild.
- Same fingerprint + failed evidence: do not rebuild until code, config, destination, or mode changes; read cached diagnostics first.
- Different destination or scheme means a different fingerprint.
- Changing from simulator to real device creates a different fingerprint.
- Fingerprint is advisory if wrapper / daemon does not support it yet; do not fake success.

## Inputs

Expected input contract:

```json
{
  "mode": "auto | build | unit | ui | full",
  "trigger": "user_requested | final_evidence_gate | release_check | high_risk",
  "target_project_root": "/path/to/project",
  "changed_files": [],
  "workspace": "App.xcworkspace",
  "project": null,
  "scheme": "App",
  "configuration": "Debug",
  "destination": "platform=iOS,id=...",
  "allow_full_build": true,
  "allow_full_log": false,
  "fingerprint": "optional-existing-fingerprint",
  "previous_validation": {
    "testing_status": "passed | failed | skipped | unknown",
    "code_review_blocking_findings": []
  }
}
```

Minimal input when invoked manually:

```json
{
  "mode": "auto",
  "target_project_root": ".",
  "trigger": "user_requested"
}
```

## Outputs

Return compact output using this contract:

```json
{
  "status": "passed | failed | skipped | blocked",
  "mode": "auto | build | unit | ui | full",
  "verification_route": "wrapper -> build-queue daemon -> xcodebuild",
  "fingerprint": "abc123",
  "cached": false,
  "schema_version": 1,
  "parser": "builtin-digest-parser",
  "formatter": "xcbeautify | xcpretty | xcprint | null",
  "workspace_or_project": "App.xcworkspace",
  "scheme": "App",
  "configuration": "Debug",
  "destination": "platform=iOS,id=...",
  "selected_device_reason": "connected physical iOS device preferred",
  "verification_report_path": "build-results/latest/verification-report.json",
  "diagnostics_path": "build-results/latest/diagnostics.json",
  "summary_path": "build-results/latest/build-summary.txt",
  "formatted_log_path": "build-results/latest/formatted-build.log",
  "source_context_path": "build-results/latest/source-context.txt",
  "tool_bootstrap": {
    "formatter": "xcbeautify",
    "status": "available | installed | fallback_builtin_parser | required_formatter_unavailable | missing_install_disabled | disabled | dry_run",
    "install_attempted": false,
    "install_succeeded": false
  },
  "first_blocking_error": {
    "kind": "swift_compile_error",
    "file": "App/File.swift",
    "line": 10,
    "message": "..."
  },
  "ui_smoke": {
    "executed": false,
    "spec": ".codex/ui-smoke.yml",
    "result": "skipped | passed | failed"
  },
  "summary": "...",
  "residual_risk": [],
  "next_action": "none | fix_first_error | connect_device | inspect_environment | run_final_evidence_gate"
}
```

## Exit Conditions

Return `passed` when:

- Wrapper / daemon completed the requested project-environment verification successfully.
- The selected workspace/project, scheme, configuration, and destination are reported.
- If UI smoke was required, it passed.
- Evidence is available through compact artifact paths or summaries.

Return `failed` when:

- `xcodebuild` ran and produced a real project, compile, link, test, signing, destination, or UI smoke failure.
- The first real blocking error is identified from `verification-report.json` / summaries.
- The next action is specific, usually `fix_first_error`.

Return `blocked` when:

- Target project root is unavailable.
- The repository is not an Xcode project.
- Wrapper is unavailable and raw `xcodebuild` is not allowed.
- Required device / destination is unavailable.
- Dependency, certificate, permission, or environment access prevents verification.
- Required UI smoke spec is missing while `XCODE_UI_SMOKE_MODE=required`.

Return `skipped` when:

- Same-or-stronger successful evidence exists after the latest change.
- The task is low-risk and `final-evidence-gate` decides existing evidence is enough.
- The user did not ask for project-environment verification and targeted evidence is sufficient.

## Escalation Rules

Escalate to `xcode-build` when:

- Signing, certificates, provisioning, Archive, Export, CI, xcconfig, build scripts, or destination strategy must be designed or changed.

Escalate to `ios-automation` when:

- The task becomes install, launch, navigation, screenshot, accessibility, simulator lifecycle, or real-device automation.

Escalate to `testing` when:

- New or modified unit/UI tests are required.
- Test scope selection is the primary task.

Escalate to `ios-build-log-digest` when:

- Verification fails and compact failure attribution is needed.
- Raw log analysis is being considered.

Escalate to raw log inspection only when:

- `verification-report.json` sets `needs_raw_log=true`, or `diagnostics.json`, `build-summary.txt`, `test-summary.json`, and compact `.xcresult` summaries are insufficient.
- The inspected section is narrowly targeted.
- The user explicitly asks for raw log analysis.

## Environment Controls

Supported target-project environment file:

```text
.codex/xcodebuild.env
```

It may specify:

- `XCODE_WORKSPACE`
- `XCODE_PROJECT`
- `XCODE_SCHEME`
- `XCODE_CONFIGURATION`
- `XCODE_DESTINATION`
- `XCODE_UI_SMOKE_MODE=off|auto|required`
- `XCODE_UI_SMOKE_SPEC=<relative-path>`
- `CODEX_VERIFY_ARTIFACT_DIR=<relative-or-absolute-path>`
- `CODEX_VERIFY_FORMATTER=auto|xcbeautify|xcpretty|xcprint|none`
- `CODEX_VERIFY_TOOL_INSTALL=auto|off|required`
- `CODEX_VERIFY_INSTALL_XCBEAUTIFY` / `CODEX_VERIFY_INSTALL_XCPRETTY` / `CODEX_VERIFY_INSTALL_XCPRINT` for script-owned custom install commands when defaults are not enough

It must not be used to bypass `testing`, `code-review`, wrapper routing, daemon serialization, or project-environment execution.
Formatter-related controls are consumed by scripts only. Agents should not set them ad hoc to avoid tool installation or parsing decisions unless the user explicitly requests a project policy change.

Deprecated / forbidden public configuration:

- `XCODE_DERIVED_DATA_*`
- `CODEX_DERIVED_DATA_SLOT`

## Reporting Format

Final response should be ordered as:

1. Precondition status: `testing`, `code-review`, and escalation reason.
2. Verification baseline: workspace/project, scheme, configuration, destination.
3. Selected device or simulator reason.
4. Result: passed / failed / skipped / blocked.
5. If failed: first real blocking error from `diagnostics.json` or summary.
6. If simulator fallback to real device happened: report both stages.
7. UI smoke status if triggered.
8. Evidence artifact paths.
9. Residual risk and next action.

Compact failed example:

```text
Verification failed.
Baseline: App.xcworkspace / App / Debug / iPhone 16 Simulator.
First blocking error: App/File.swift:10 cannot find `foo` in scope.
Evidence: build-results/latest/verification-report.json.
Raw log: skipped by policy.
Next action: fix_first_error.
```

## Examples

### Cached Success

```json
{
  "status": "skipped",
  "cached": true,
  "fingerprint": "abc123",
  "summary": "Same fingerprint already has successful build evidence after latest change.",
  "next_action": "none"
}
```

### Build Failure

```json
{
  "status": "failed",
  "cached": false,
  "fingerprint": "def456",
  "first_blocking_error": {
    "kind": "swift_compile_error",
    "file": "App/ViewModel.swift",
    "line": 82,
    "message": "Cannot find 'productID' in scope"
  },
  "verification_report_path": "build-results/latest/verification-report.json",
  "diagnostics_path": "build-results/latest/diagnostics.json",
  "next_action": "fix_first_error"
}
```

### Blocked Device

```json
{
  "status": "blocked",
  "summary": "Real-device verification required but no connected iOS destination is available.",
  "next_action": "connect_device"
}
```

## Reference Resources

- `scripts/build-check.sh`
- `references/override-config.md`
- `../ios-build-log-digest/references/verification-report-schema.md`
- `../ios-verification-router/SKILL.md`
- `../ios-build-log-digest/SKILL.md`
- `../../daemon/diagnostics.schema.json`

## Relationship to Other Skills

- `final-evidence-gate` decides whether this Skill is needed when evidence is insufficient.
- `ios-verification-router` should be used before this Skill for low-token verification route selection.
- `ios-affected-tests` should be used before broad test execution.
- `ios-build-log-digest` should be used after verification failure.
- `code-review` owns full diff / PR review and blocking findings.
- `testing` owns test writing and targeted test strategy.
- `ios-automation` owns install, launch, screenshot, accessibility, simulator, and device automation.
- `xcode-build` owns signing, archive, export, CI, build setting, and destination strategy design.
