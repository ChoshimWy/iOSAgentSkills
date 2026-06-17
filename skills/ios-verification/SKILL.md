---
name: ios-verification
description: iOS / Apple Xcode 项目统一验证 Skill。用于验证前路由、最窄 XCTest / -only-testing 选择、通过 codex_verify wrapper 接入 shared build-queue daemon 执行项目环境 build/test、读取 agent-summary.json / verification-report.json / diagnostics.json 做低 token 失败归因，以及在定向验证和独立 code-review 后裁决最终证据是否足够；替代原先分散的验证路由、受影响测试选择、定向验证执行、构建日志摘要、最终证据裁决与项目环境构建验证入口。
---

# iOS Verification（统一验证入口）

## Purpose

Select, execute, digest, and judge the cheapest sufficient iOS / Apple-platform verification path without scattering the workflow across multiple verification Skills.

## 中文说明

该 Skill 是 Apple Xcode 项目验证链路的唯一入口，内部按 `verification_mode` 分流：

| Mode | 负责内容 | 说明 |
| --- | --- | --- |
| `route` | 根据 diff 选择最低有效验证等级 | 验证前决策 |
| `affected-tests` | 推导最窄 XCTest / `-only-testing` 范围 | 测试面选择 |
| `execute` | 通过 `codex_verify` / build-queue 执行项目环境验证 | 定向或项目环境执行 |
| `digest` | 读取结构化 artifact，定位第一个 blocking failure | 失败归因 |
| `final-gate` | 在定向验证和独立 `code-review` 后裁决证据是否足够 | 最终证据裁决 |

不负责：生产/测试代码实现、Mock / Stub / Spy / fixture / Page Object 编写、构建配置设计、签名、Archive / Export、CI/CD、运行时 crash 调试、性能 profiling、设备导航自动化。

## When to Use

Use this Skill when:

- An iOS / macOS / Apple-platform code change needs targeted validation, `no_test_reason`, or `suggested_validation`.
- An Agent is about to request Xcode build/test and the cheapest valid mode is unclear.
- Swift / Objective-C / test / UI / resource / project / dependency files changed and verification routing is needed.
- Matching XCTest / `-only-testing` candidates must be selected.
- The user explicitly asks to run build verification, compile check, `xcodebuild`, or project-environment verification.
- A build/test command failed and compact artifacts such as `agent-summary.json`, `verification-report.json`, or `diagnostics.json` exist.
- The user asks whether existing evidence is enough for merge/release/final confidence.
- Multiple Agents share the build-queue daemon and duplicate verification must be suppressed.

## When Not to Use

Do not use this Skill when:

- Production or test code must be written or modified; use `ios-feature-implementation` (`test-implementation` for test code).
- The task is pure code review or PR review; use independent reviewer subAgent `code-review`.
- The task is Build Settings, signing, Archive, Export, CI/CD, scheme design, xcconfig, or packaging mechanics; use `xcode-build`.
- The task is install, launch, navigation, screenshot, accessibility tree, simulator lifecycle, or device automation; use `ios-automation`.
- The issue is runtime crash, hang, leak, watchdog, or behavior debugging; use `debugging`.
- The issue is frame drops, startup, CPU / memory, benchmark, `xctrace`, or Instruments; use `ios-performance`.
- The repository is not an Xcode / Apple-platform project and no Xcode verification is relevant.

## Agent Rules

### Mode Selection

- Use `route` first when validation level is unclear.
- Use `affected-tests` when unit test mapping is non-trivial.
- Use `execute` only when targeted validation or project-environment verification should actually run.
- Use `digest` after a failed verification or when raw log inspection is being considered.
- Use `final-gate` only after targeted validation / `no_test_reason` and independent `code-review` evidence are available, or when the user explicitly asks for final confidence.
- Do not run full verification by default.
- Do not read full raw build logs by default.
- Do not implement code or tests in this Skill.

### Diff Classification

Classify changed files before verification:

| Diff Type | Examples | Default Verification |
| --- | --- | --- |
| `doc-only` | `*.md`, docs, comments only | none / lint |
| `rule-only` | `AGENTS.md`, `SKILL.md`, policy docs | policy lint or no Xcode |
| `asset-only` | images, colors, json fixtures with no runtime loader change | no Xcode or resource check |
| `test-only` | XCTest / XCUITest files only | targeted `-only-testing` |
| `swift-small` | narrow Swift / ObjC logic change | affected tests or targeted build |
| `swift-risky` | persistence, networking, BLE, DB, concurrency, subscription | affected tests + build |
| `ui-only` | SwiftUI/UIKit view/layout files | build; UI smoke only if justified |
| `project-config` | `.xcodeproj`, `.xcworkspace`, scheme, xctestplan, xcconfig | project-environment build/test |
| `dependency` | `Podfile`, lockfiles, `Package.resolved`, private Pod version | project-environment build/test |
| `release` | signing, entitlements, Archive / Export | route to `xcode-build` + stronger evidence |

### Verification Levels

Use the smallest sufficient level:

| Level | Meaning |
| --- | --- |
| `none` | No Xcode verification; explain why. |
| `lint` | Static policy/schema check only. |
| `typecheck` | Lightweight source validation where supported. |
| `unit` | Targeted XCTest with `-only-testing`. |
| `build` | Build affected target or app integration baseline. |
| `ui` | Targeted UI smoke / UI test only when justified. |
| `full` | Release, dependency, project config, or explicit confidence gate. |

### Affected Test Selection

- Prefer exact test method -> test class -> smallest test file / bundle.
- Prefer matching basename, changed type references, and nearest feature-folder tests.
- For `*ViewModel.swift`, prefer `*ViewModelTests`.
- For `*Service.swift`, `*Repository.swift`, `*UseCase.swift`, or `*Manager.swift`, prefer matching unit tests.
- For StoreKit / purchase / subscription, prefer purchase / receipt / entitlement tests.
- For database / persistence / CoreData / WCDB, prefer persistence tests.
- For BLE / mesh / provisioning, prefer parser or state-machine tests; avoid real-device tests by default.
- For SwiftUI / UIKit view-only changes, prefer build unless targeted UI tests are cheap and explicit.
- If no deterministic low-cost path exists, return `no_test_reason` and `suggested_validation` instead of escalating automatically.

### Wrapper and Build Queue Rules

- Never run validation-type `xcodebuild` directly.
- Always prefer target project `./codex_verify.sh`.
- If absent, use `~/.codex/bin/codex_verify`.
- The wrapper must submit validation-type `xcodebuild` to shared build-queue daemon.
- Project-environment verification must run from the target project root.
- For Codex, use `functions.exec_command`; when target-project execution requires non-sandbox access, request escalation rather than running a sandbox copy.
- The wrapper / script owns formatter selection, tool bootstrap, parsing, redaction, artifact generation, and preserving the real `xcodebuild` exit code.
- Agents must not manually install or invoke `xcbeautify`, `xcpretty`, `xcprint`, `xcresulttool`, or equivalent parser tools.
- Reuse Xcode 系统 DerivedData (`~/Library/Developer/Xcode/DerivedData`) via daemon; do not reintroduce `XCODE_DERIVED_DATA_*` or `CODEX_DERIVED_DATA_SLOT` public configuration.

### Baseline Rules

- If `.codex/xcodebuild.env` sets workspace/project/scheme/configuration/destination, respect it.
- If both `.xcworkspace` and `.xcodeproj` exist, prefer `.xcworkspace`.
- Prefer schemes bound to unit test targets / bundles such as `*Tests`; otherwise consider `*UITests` or `*_TEST`.
- Workspace/project priority and scheme test binding selection are script-owned decisions; Agents should read `project_selection` and `scheme_selection` from `agent-summary.json` instead of re-deriving them from the file tree.
- Reuse earlier workspace / scheme / destination in the same task unless a clear reason exists.
- For private Pod / component changes, validate through the main project using local `:path` dependency after modifying the real private library repository when that is the development baseline.
- After validation passes, keep the current local `:path` state by default; do not switch to online versioned dependency or `Pods/` vendored snapshot unless explicitly requested or required for an authorized main-project dependency-file commit.
- For iOS with no explicit destination, prefer connected physical iOS device; if none exists, fall back to simulator; for macOS use host build.
- Do not treat paired but disconnected devices as default final verification targets.

### Execution and Fingerprint Rules

- Prefer wrapper `--mode auto` unless a narrower/stronger mode is justified.
- If the same fingerprint has successful same-or-stronger evidence after the latest change, skip duplicate verification and report cached evidence.
- If the same fingerprint failed, read cached `agent-summary.json` / `verification-report.json` before another run.
- Change code, config, destination, scheme, or mode before rerunning a failed fingerprint.
- Fingerprint should include diff + workspace/project + scheme + configuration + destination + mode + Xcode version when supported.
- If wrapper fingerprinting is unavailable, do not fake success.

### Digest Rules

- Read artifacts in this order:
  1. `agent-summary.json`
  2. `verification-report.json`
  3. `diagnostics.json`
  4. `build-summary.txt`
  5. `test-summary.json`
  6. `xcresult-summary.json`
  7. Small targeted source section around the reported location
- Do not read `build.log`, raw `xcodebuild.log`, full `.xcresult` JSON, recursive `DerivedData`, all warnings, or unrelated SwiftCompile sections by default.
- Inspect raw logs only when compact artifacts set `needs_raw_log=true`, summaries are insufficient, or the user explicitly asks.
- Report only the first real blocking error.
- Fix only the first real blocking error before rerunning verification.

### Final Evidence Gate Rules

Accept existing evidence only when all are true:

1. Evidence happened after the latest code/config/resource/dependency change.
2. Evidence came from the target project root when project-environment evidence is claimed.
3. Baseline matches final delivery target or is clearly stronger.
4. Targeted validation executed, or `no_test_reason` plus `suggested_validation` is explicit.
5. Independent `code-review` has no blocking findings and reviewed the verification story.
6. No project/dependency/signing/resource/device high-risk trigger requires stronger evidence.

Escalate to `execute` / stronger verification when any are true:

- `.xcodeproj`, `.xcworkspace`, scheme, xctestplan, xcconfig, Build Settings, or build scripts changed.
- Signing, entitlements, plist, capabilities, App Extensions, or device capability configuration changed.
- `Podfile`, lockfiles, private Pod version, Package resolution, or dependency baseline changed.
- Resources, Storyboard, XIB, Assets, target membership, InfoPlist strings, or packaging changed.
- Targeted tests only cover a sub-library and do not prove consumer app integration.
- Validation is stale, unknown, mismatched, or happened before the latest change.
- `code-review` says the verification baseline is insufficient.
- User requests release / merge / final confidence.

### Token Budget

- Keep verification decisions compact.
- Prefer structured artifacts over formatter output or raw logs.
- Do not paste large command outputs, logs, diffs, or `.xcresult` dumps.
- Include baseline, result, first blocking error, evidence paths, residual risk, and next action only.

## Inputs

```json
{
  "verification_mode": "route | affected-tests | execute | digest | final-gate | auto",
  "changed_files": [],
  "target_project_root": ".",
  "workspace": "optional",
  "project": "optional",
  "scheme": "optional",
  "configuration": "Debug",
  "destination": "optional",
  "requested_level": "none | lint | typecheck | unit | build | ui | full | auto",
  "only_testing": [],
  "previous_validation": {
    "executed_validation": [],
    "no_test_reason": null,
    "suggested_validation": [],
    "code_review_blocking_findings": []
  },
  "artifact_paths": {
    "agent_summary": "optional",
    "verification_report": "optional",
    "diagnostics": "optional",
    "build_summary": "optional",
    "test_summary": "optional",
    "xcresult_summary": "optional"
  },
  "constraints": ["narrowest validation", "no full log"]
}
```

## Outputs

```json
{
  "status": "passed | failed | skipped | blocked | accepted | escalated | proposed",
  "verification_mode": "route | affected-tests | execute | digest | final-gate",
  "verification_level": "none | lint | typecheck | unit | build | ui | full",
  "reason": "...",
  "changed_files": [],
  "only_testing": [],
  "also_build": false,
  "verification_route": "wrapper -> build-queue daemon -> xcodebuild",
  "workspace_or_project": "App.xcworkspace",
  "scheme": "App",
  "configuration": "Debug",
  "destination": "platform=iOS,id=...",
  "fingerprint": null,
  "cached": false,
  "executed_validation": [],
  "accepted_evidence": [],
  "rejected_evidence": [],
  "final_evidence_gate": "accepted_existing_evidence | needs_project_environment_verification | blocked_insufficient_evidence | null",
  "verification_story": "accepted | needs-project-environment-verification | insufficient | null",
  "agent_summary_path": null,
  "verification_report_path": null,
  "diagnostics_path": null,
  "summary_path": null,
  "first_blocking_error": null,
  "failure_attribution": "none | current_change | pre_existing | environment | unknown",
  "no_test_reason": null,
  "suggested_validation": [],
  "residual_risk": [],
  "next_action": "none | run-targeted-validation | run-project-verification | fix_first_error | code-review | xcode-build | blocked"
}
```

Field rules:

- `executed_validation` records only verification actually run in the target project environment or explicitly marked local/static validation.
- `failure_attribution` must be evidence-backed; use `unknown` rather than guessing when compact artifacts are insufficient.
- `first_blocking_error` is the first real compile, link, test, signing, destination, or UI-smoke blocker from compact artifacts.
- `no_test_reason` is required when code changed but no low-cost deterministic test path exists.

## Exit Conditions

Return `passed` when:

- A route/affected-test selection is complete, or
- Targeted/project verification ran and passed, or
- Digest found no blocking error.

Return `proposed` when verification was planned but not executed.

Return `skipped` when no Xcode verification is needed or fresh same-or-stronger cached evidence exists.

Return `failed` when verification ran and produced a real build/test/signing/destination/UI-smoke failure with first blocking error identified.

Return `accepted` when final-gate accepts existing evidence with no blocking review findings.

Return `escalated` when final-gate requires stronger project-environment verification.

Return `blocked` when required project root, wrapper, scheme, dependency, device, credentials, permission, compact artifacts, or user decision is unavailable.

## Escalation Rules

Escalate to `ios-feature-implementation` when production or test code must be written or modified.

Escalate to `code-review` when targeted validation / `no_test_reason` is ready and independent review is required.

Escalate to `xcode-build` when signing, Archive / Export, CI, Build Settings, scheme/destination strategy, or packaging design is the missing piece.

Escalate to `ios-automation` when install, launch, navigation, accessibility tree, screenshot, simulator lifecycle, or real-device automation evidence is required.

Escalate to `debugging` when a failure is a runtime crash, hang, leak, watchdog, or behavior issue rather than build/test failure.

Escalate to `ios-performance` when evidence requires benchmark, `measure(metrics:)`, `xctrace`, Instruments, startup, CPU, memory, or frame analysis.

## Reporting Format

```text
Verification status: passed | failed | skipped | blocked | accepted | escalated | proposed
Mode: route | affected-tests | execute | digest | final-gate
Level: none | lint | typecheck | unit | build | ui | full
Baseline: workspace/project / scheme / configuration / destination
Affected tests:
- ...
Executed validation:
- ...
Evidence:
- agent-summary.json: ...
- verification-report.json: ...
First blocking error: none | file:line message
Final gate: accepted_existing_evidence | needs_project_environment_verification | blocked_insufficient_evidence
No test reason: none | ...
Residual risk:
- ...
Next: none | run-targeted-validation | run-project-verification | fix_first_error | code-review | blocked
```

## Reference Resources

- `scripts/build-check.sh`: project-environment verification wrapper helper used by `codex_verify --build-check`.
- `scripts/build_check.py`: structured artifact generator / digest parser for Xcode build/test output.
- `references/override-config.md`: supported `.codex/xcodebuild.env` controls and forbidden deprecated variables.
- `references/verification-report-schema.md`: `agent-summary.json`, `verification-report.json`, and `diagnostics.json` schema and reading order.

## Relationship to Other Skills

- Replaces the previous separate verification routing, affected-test selection, targeted validation execution, build-log digest, final evidence gate, and project-environment verification entries.
- `ios-feature-implementation` owns production code and test code implementation, including `test-implementation`.
- `code-review` owns independent static review and verification-story review.
- `xcode-build` owns build/release configuration and signing/Archive/Export strategy.
- `ios-automation` owns device/simulator UI automation and screenshot/accessibility evidence.
- `debugging` owns runtime crash/hang/leak/behavior diagnosis.
- `ios-performance` owns performance profiling and benchmark evidence.
