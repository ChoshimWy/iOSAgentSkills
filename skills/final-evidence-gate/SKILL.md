---
name: final-evidence-gate
description: Apple Xcode 项目改动的按需最终证据裁决 Skill。用于用户显式要求、发布前自检或高风险场景下，在 testing 与独立 reviewer subAgent code-review 放行后判断现有验证证据是否足够；必要时才升级到 verify-ios-build 执行项目环境验证。
---

# Final Evidence Gate（条件化可选证据验证）

## Purpose

Decide whether existing targeted validation, build/test evidence, and code-review findings are sufficient for final acceptance of an Apple Xcode project change, or whether the task must escalate to `verify-ios-build`.

## 中文说明

该 Skill 是最终证据裁决层，不是默认构建执行器。

负责：
- 判断现有 testing / build / code-review 证据是否足够。
- 判断是否需要补一次真实项目环境 `xcodebuild` 验证。
- 统一输出 `verification_story` 与 `final_evidence_gate` 结论。
- 避免每次任务结束都重复跑 `verify-ios-build`。
- 不替代 `ios-verification-router` 的执行前模式选择，也不替代 `verify-ios-build` 的实际执行。

不负责：
- 编写测试。
- 静态代码审查。
- 执行具体项目环境 build/test。
- 设计 Build Settings、签名、Archive、CI。

## When to Use

Use this Skill when:

- The user explicitly asks for final confidence or final evidence.
- The user asks whether current validation evidence is enough.
- The task is release / merge / preflight self-check.
- The change is high-risk and may need stronger project-environment evidence.
- `testing` and `code-review` are complete, but the main Agent needs a final evidence decision.
- There is uncertainty about whether to run `verify-ios-build`.

## When Not to Use

Do not use this Skill when:

- The user directly asks to run project-environment build verification; use `verify-ios-build`.
- The task still has blocking `code-review` findings.
- `testing` has not produced executed validation, suggested validation, or `no_test_reason`.
- The task is build configuration design; use `xcode-build`.
- The task is device/simulator automation; use `ios-automation`.
- The task is runtime debugging or performance profiling.

## Agent Rules

### Gate Rules

- Do not run `verify-ios-build` by default.
- Prefer accepting same-or-stronger existing evidence when valid.
- Only escalate when evidence is insufficient, stale, mismatched, or risk requires it.
- If `code-review` has blocking findings, do not accept evidence; return blocked.
- If testing evidence happened before the latest code/config/resource/dependency change, treat it as stale.
- If validation baseline does not match final delivery baseline, treat it as insufficient unless it is clearly stronger.
- If evidence is insufficient and verification cannot run, return blocked with residual risk.

### Existing Evidence Acceptance Rules

Existing evidence can be accepted only when all are true:

1. Evidence happened after the latest repo-tracked code/config/resource/dependency change.
2. Evidence came from the target project root environment when project-environment evidence is claimed.
3. Evidence covers final delivery target, consumer app scheme, or a clearly stronger baseline.
4. Workspace/project, scheme, configuration, and destination match the final delivery baseline or are stricter.
5. `testing` recorded `executed_validation`, or gave a clear `no_test_reason` and `suggested_validation`.
6. `code-review` reviewed the verification story and has no blocking findings.
7. No high-risk change category requires stronger evidence.

For `code-small` / `code-medium` pure logic changes, a successful narrow targeted unit test after the latest code change may be enough when `code-review` finds no integration, project, dependency, signing, resource, or device-capability risk.

### Escalation Triggers

Escalate to `verify-ios-build` when any are true:

- `.xcodeproj`, `.xcworkspace`, scheme, xctestplan, xcconfig, Build Settings, or build scripts changed.
- Signing, certificates, entitlements, plist, capabilities, App Extensions, or device capability configuration changed.
- `Podfile`, `Podfile.lock`, `Pods/Manifest.lock`, private Pod version, or dependency baseline changed.
- Local `:path` dependency was switched back to online versioned dependency.
- Resources, Storyboard, XIB, Assets, target membership, InfoPlist.strings, or bundle packaging changed.
- Targeted tests only cover a sub-library and do not prove consumer app integration.
- Testing produced only `no_test_reason` and risk is not low enough to accept static evidence.
- Code/config/resource/dependency changed after validation.
- `code-review` says verification baseline is inconsistent or insufficient.
- User requests release/merge confidence.

### Private Dependency Rules

- Private library / component integration evidence must come from the main project using local `:path` dependency when that is the development baseline.
- Do not accept online versioned dependency or `Pods/` vendored snapshot evidence unless the user explicitly asked for that validation baseline.

### Token Budget

- Do not read raw build logs by default.
- Use summaries from `testing`, `code-review`, `verify-ios-build`, and `ios-build-log-digest`.
- Only include the evidence decision, baseline, risk, and next action.
- Do not duplicate full command outputs.

## Inputs

Expected input contract:

```json
{
  "task_type": "code-small | code-medium | code-risky | project-config | dependency | release",
  "latest_change_time": "optional",
  "changed_files": [],
  "testing": {
    "executed_validation": [],
    "suggested_validation": [],
    "no_test_reason": null,
    "failure_attribution": "none"
  },
  "code_review": {
    "blocking_findings": [],
    "verification_story": "accepted | needs-final-evidence-gate | needs-verify-ios-build | insufficient",
    "unreviewed_changes": "none"
  },
  "existing_evidence": [
    {
      "type": "xcodebuild test | xcodebuild build | targeted unit test | ui smoke",
      "workspace_or_project": "App.xcworkspace",
      "scheme": "App",
      "configuration": "Debug",
      "destination": "platform=iOS Simulator,name=iPhone 16",
      "status": "passed | failed",
      "time": "optional",
      "after_latest_change": true
    }
  ],
  "user_request": "optional"
}
```

## Outputs

Return compact structured output:

```json
{
  "status": "accepted | escalated | blocked",
  "final_evidence_gate": "accepted_existing_evidence | needs_verify_ios_build | blocked_insufficient_evidence",
  "verification_story": "accepted | needs-verify-ios-build | insufficient",
  "accepted_evidence": [],
  "rejected_evidence": [],
  "escalation_reason": null,
  "required_next_skill": "none | verify-ios-build | testing | code-review | xcode-build",
  "residual_risk": [],
  "next_action": "complete | run-verify-ios-build | fix-blocking-review | collect-evidence | blocked"
}
```

## Exit Conditions

Return `accepted` when:

- Existing evidence is fresh, relevant, and sufficient.
- `code-review` has no blocking findings.
- Validation baseline matches final delivery baseline or is stronger.
- Residual risk is low and disclosed.

Return `escalated` when:

- Evidence is insufficient but project-environment verification can be run.
- Output clearly routes to `verify-ios-build` with escalation reason.

Return `blocked` when:

- `code-review` has blocking findings.
- Evidence is insufficient and verification cannot run.
- Validation baseline is unknown or stale and cannot be corrected.
- Required target project, scheme, device, dependency, or credentials are unavailable.

## Escalation Rules

Escalate to `verify-ios-build` when final project-environment evidence is needed.

Escalate to `testing` when no targeted validation or `no_test_reason` exists.

Escalate to `code-review` when verification story has not been reviewed or blocking findings are unresolved.

Escalate to `xcode-build` when the missing piece is signing, Build Settings, Archive, Export, CI, scheme, or destination strategy.

Escalate to `ios-automation` when UI/device evidence is required rather than build evidence.

## Reporting Format

```text
final_evidence_gate: accepted_existing_evidence | needs_verify_ios_build | blocked_insufficient_evidence
verification_story: accepted | needs-verify-ios-build | insufficient
accepted_evidence:
- ...
rejected_evidence:
- ...
escalation_reason: none | ...
residual_risk:
- ...
next_action: complete | run-verify-ios-build | blocked
```

## Examples

### Accept Existing Targeted Unit Test

```json
{
  "status": "accepted",
  "final_evidence_gate": "accepted_existing_evidence",
  "verification_story": "accepted",
  "accepted_evidence": ["AppTests/SubscriptionServiceTests passed after latest change"],
  "residual_risk": [],
  "next_action": "complete"
}
```

### Escalate to Verify iOS Build

```json
{
  "status": "escalated",
  "final_evidence_gate": "needs_verify_ios_build",
  "verification_story": "needs-verify-ios-build",
  "escalation_reason": "Podfile.lock changed; existing targeted tests do not prove consumer app integration.",
  "required_next_skill": "verify-ios-build",
  "next_action": "run-verify-ios-build"
}
```

### Blocked Insufficient Evidence

```json
{
  "status": "blocked",
  "final_evidence_gate": "blocked_insufficient_evidence",
  "verification_story": "insufficient",
  "rejected_evidence": ["Validation ran before latest resource change"],
  "residual_risk": ["Consumer app packaging not verified"],
  "next_action": "blocked"
}
```

## Relationship to Other Skills

- `testing` records targeted validation, `no_test_reason`, and suggested validation.
- `code-review` reviews static risk and verification story.
- `verify-ios-build` executes project-environment verification when this gate escalates.
- `xcode-build` owns Build Settings, signing, Archive/Export, CI/CD design.
- `ios-automation` owns UI/device evidence when device-level automation is needed.
- `ios-build-log-digest` owns compact build failure attribution.
- `codex_verify.sh` / `~/.codex/bin/codex_verify` are verification execution wrappers, not evidence decision makers.
