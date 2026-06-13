---
name: codex-subagent-orchestration
description: 默认优先使用的 iOS 主 Skill 入口；先按任务复杂度选择 lite / standard / full 档位，再协调 coder / reviewer / tester / reporter / main agent 分工，并在内部路由到实现、调试、性能、测试、审查与按需验证模块；Codex CLI 原生 subAgent 可用时按档位自动使用，仅在工具不可用、策略禁止或写集不适合并行时临时回退单 Agent。
---

# Codex 多 Agent 编排

## Purpose

Coordinate iOS development tasks through an adaptive multi-agent workflow while keeping verification narrow, evidence-based, and low-token by default.

## 中文说明

该 Skill 是本仓库默认 iOS 主入口。它不直接替代实现、测试、审查、构建或调试 Skill，而是负责：

- 判断任务类型与复杂度。
- 选择 `lite` / `standard` / `full` 编排档位。
- 协调 coder / reviewer / tester / reporter / main agent 的职责边界。
- 决定何时内部路由到实现、调试、性能、测试、审查与按需验证模块。
- 在多 Agent 场景下保证 checkpoint、fail-fix-report 与低 token 验证纪律。

默认完成态必须由主 Agent 基于定向测试 / 必要验证与 `code-review` 结论裁决；任何 subAgent 都不能替代主 Agent 宣告完成。

## When to Use

Use this skill when:

- The task is an iOS / Apple platform development task and does not clearly belong to one single specialized Skill.
- The task contains implementation, review, testing, debugging, performance, Apple API, or optional evidence verification steps.
- The task may benefit from adaptive role splitting.
- The task involves multiple files, unclear risk, or a need to coordinate implementation and verification.
- The user explicitly asks to use the iOS Agent workflow or multi-agent Codex workflow.

## When Not to Use

Do not use this Skill as the first route when the task is clearly one of these single-purpose tasks:

- Pure code review: route directly to `code-review`.
- Pure test writing: route directly to `testing`.
- Pure Xcode build setting, signing, archive, or export task: route directly to `xcode-build`.
- Pure final evidence decision or explicit project build verification: route to `final-evidence-gate` / `verify-ios-build`.
- Pure Apple API / availability / WWDC lookup: route to `apple-docs`.
- Pure runtime crash or debugging request: route to `debugging`.
- Pure performance profiling or benchmark request: route to `ios-performance`.
- Pure documentation or rule edit that does not need role splitting.

## Agent Rules

### Hard Boundaries

- Always classify task type before selecting `lite` / `standard` / `full`.
- Do not upgrade all tasks to full multi-agent execution.
- Use Codex native subAgent tools only when available and useful.
- If runtime subAgent tools are unavailable, policy-forbidden, or unsuitable for the current write set, fall back to single Agent execution.
- Single Agent fallback must still preserve testing / targeted validation and `code-review` closure for implementation tasks.
- Do not let subAgents share unsafe write ownership.
- Do not use `multi_tool_use.parallel` when tools may touch the same write set, `apply_patch`, Git state, build queue, or project files.
- Do not introduce external orchestrators unless the user explicitly asks.
- Use only built-in `worker` and `explorer` agent types unless the runtime provides additional official types.
- Do not invent new low-level Agent types.

### Token Budget

- Prefer `rg` and precise file reads over broad scans.
- Do not paste large diffs, full files, full build logs, full `.xcresult` dumps, or recursive `DerivedData` output.
- Build / test / log output should be summarized as key error sections, filtered summaries, or the last 80-120 relevant lines.
- Long logs should be written to files and digested before being read by Agents.
- For build failures, prefer `diagnostics.json` then `build-summary.txt`.
- Default raw log policy: forbidden unless summaries are insufficient or the user explicitly asks.

### Verification Discipline

- Implementation tasks must close through targeted testing / necessary validation and `code-review`.
- `final-evidence-gate` and `verify-ios-build` are optional strengthening paths, not default mandatory closure.
- For low-token build routing, use `ios-verification-router` before optional project-environment verification.
- For test selection, use `ios-affected-tests` before requesting broad test execution.
- For build failure attribution, use `ios-build-log-digest` before reading raw logs.
- Any local `xcodebuild` verification must go through the target project wrapper `./codex_verify.sh` when available, otherwise `~/.codex/bin/codex_verify`.
- Shared build-queue daemon remains the default path for validation-type `xcodebuild`.
- Reuse the same workspace / scheme / destination baseline when a task already ran targeted build or test validation.

### Private Pod / Local Path Rules

- If the target project uses CocoaPods and the task touches private components or dependency integration, inspect `Podfile`, `Podfile.lock`, and `Pods/Manifest.lock` before implementation.
- If a local `:path` private Pod is active, modify the real component repository, not the `Pods/<LibraryName>` vendored copy.
- During local integration, keep or switch the main project to local `:path` dependency when required for development and verification.
- Do not commit local `:path` dependency references unless the user explicitly asks.

## Task Classification

Classify into one of these types before selecting orchestration level:

| Type | Meaning | Default Level |
| --- | --- | --- |
| `doc-only` | Documentation rewrite, product notes, information organization | `lite` |
| `rule-only` | Rules, workflow, template, or lint policy changes | `lite` |
| `code-small` | Small code change, usually one module or a few files | `standard` |
| `code-medium` | Normal code change across multiple files with clear boundary | `standard` |
| `code-risky` | Cross-module, concurrency, availability, public contract, dependency, private library, or complex validation path | `full` |

## Orchestration Levels

### `lite`

Use for tiny, single-file, low-risk, doc-only, or rule-only tasks.

Default behavior:

- Prefer single Agent execution.
- Preserve targeted validation and `code-review` for implementation tasks.
- Do not spawn unnecessary tester or reviewer subAgents for pure documentation / rule changes.

### `standard`

Use for normal code or workflow changes with clear boundaries.

Default behavior:

- `coder worker` for implementation when useful.
- `reviewer explorer` using `code-review` for implementation tasks.
- Main Agent aggregates and decides closure.
- Start `tester explorer` only when there is a test surface, failure attribution need, or user asks.

### `full`

Use for high-risk or cross-module tasks.

Default behavior:

- `coder worker` for implementation.
- `reviewer explorer` using `code-review`.
- `tester explorer` for test surface, validation advice, and failure attribution.
- Main Agent controls checkpoint, loop count, and final closure.
- Use `final-evidence-gate` / `verify-ios-build` only when risk or user request justifies it.

## Role Activation Matrix

Default minimum role set: `explorer + builder + reporter`.

Activate additional roles only when justified:

| Role | Activate When | Default Skill Reuse |
| --- | --- | --- |
| `pm` | Requirements are unclear, acceptance criteria are missing, or goals conflict | planning / requirement clarification |
| `coder worker` | Code or test implementation is needed | `ios-feature-implementation`, `uikit-feature-implementation`, `swiftui-feature-implementation`, `swift-expert` |
| `reviewer explorer` | Any implementation task; risky rule changes | `code-review` |
| `tester explorer` | Test surface exists, failure attribution is needed, or task is `code-risky` | `testing`, `ios-affected-tests`, `ios-build-log-digest` |
| `tester worker` | Test code must be added or updated | `testing` |
| `reporter` | Delivery summary, acceptance matrix, residual risk | this Skill |
| `main agent` | Always active for aggregation, control, and final decision | this Skill |

## Workflow

1. Main Agent determines intent, ownership, success criteria, risk level, and task type.
2. Main Agent freezes relevant workspace / scheme / destination baseline when verification may be needed.
3. Main Agent checks private Pod / local `:path` ownership if dependencies are involved.
4. Main Agent selects `lite` / `standard` / `full`.
5. Main Agent spawns only the minimum required subAgents.
6. `wait_agent(...)` is used only when the result is needed to advance the next step; do not poll aggressively.
7. If reviewer or tester finds a blocking issue, Main Agent uses `send_input(..., interrupt=true)` to route the precise issue back to coder.
8. If tester determines test code is required, start `tester worker` with ownership limited to test files.
9. Main Agent applies fail-fix-report discipline until resolved or blocked.
10. Main Agent performs final closure using targeted validation / necessary verification and `code-review` findings.
11. Only if requested or high-risk, Main Agent routes to `final-evidence-gate` / `verify-ios-build`.

## Checkpoints

Default checkpoints:

| Checkpoint | Meaning |
| --- | --- |
| `CP0 Intent Lock` | Confirm intent, constraints, success criteria, and non-goals. |
| `CP1 Anchor Slice` | Complete and inspect the first meaningful slice before expanding parallel work. |
| `CP2 Validation Baseline Freeze` | Freeze validation baseline, affected tests, wrapper path, and log policy. |
| `CP3 Final Gate` | Decide completion based on evidence and blocking findings. |

Rules:

- Do not start unnecessary parallel expansion before `CP1` passes.
- `checkpoint_status` maintained by Main Agent is the single source of truth.
- See `references/checkpoint-contract.md` for detailed definitions.

## Fail-Fix-Report Discipline

- `fail`: identify the first real blocking failure and its impact scope.
- `fix`: if fixable, fix it and rerun only the necessary validation on the same baseline.
- `report`: report only when fixed and rerun, or when clearly blocked.
- Do not declare completion with known blocking issues.
- Default maximum loop count for the same issue class: 2.
- After loop limit is exceeded, `next_action` must be `blocked`.

## Inputs

Expected input from the user or upstream Agent:

```json
{
  "goal": "Implement or modify an iOS feature",
  "context": ["files", "directories", "logs", "screenshots", "constraints"],
  "constraints": ["minimal changes", "do not run full build", "use build queue"],
  "success_criteria": ["targeted validation passes", "code-review has no blocking findings"],
  "preferred_validation": "auto"
}
```

Optional runtime inputs:

```json
{
  "workspace": "App.xcworkspace",
  "scheme": "App",
  "destination": "platform=iOS Simulator,name=iPhone 16",
  "changed_files": [],
  "available_subagents": ["worker", "explorer"],
  "build_wrapper": "./codex_verify.sh"
}
```

## Outputs

Main Agent final output should follow this contract:

```json
{
  "status": "completed | blocked | partial",
  "task_type": "doc-only | rule-only | code-small | code-medium | code-risky",
  "orchestration_level": "lite | standard | full",
  "roles_used": ["main", "coder", "reviewer", "tester", "reporter"],
  "changed_files": [],
  "validation": {
    "executed": [],
    "skipped": [],
    "no_test_reason": null,
    "suggested_validation": null
  },
  "review": {
    "blocking_findings": [],
    "non_blocking_findings": []
  },
  "acceptance_matrix": [
    {
      "requirement": "...",
      "evidence": "...",
      "status": "passed | failed | skipped"
    }
  ],
  "known_risks": [],
  "next_action": "none | blocked | needs_user_input | needs_verification"
}
```

SubAgent outputs must stay compact:

- `coder worker`: `changed_files`, `summary`, `test_impact` or `no_test_reason`, `known_risks`.
- `reviewer explorer`: `blocking_findings`, `non_blocking_findings`.
- `tester explorer`: `suggested_validation`, `executed_validation`, `failure_attribution`, `failure_attribution_type`, `needs_test_code`.
- `reporter`: `acceptance_matrix`, `residual_risks`, `completion_status`.

## Exit Conditions

A task may be marked `completed` only when:

- User goal is satisfied or explicitly scoped down.
- Changed files are summarized.
- Targeted validation / necessary verification is executed or a clear `no_test_reason` is provided.
- `code-review` has no blocking findings.
- Known risks are disclosed.
- No subAgent has unresolved blocking output.
- Main Agent, not a subAgent, makes the final completion decision.

A task must be marked `blocked` when:

- Required context, credentials, project state, dependency access, device, or build environment is unavailable.
- The same failure class exceeded the default 2-loop fail-fix-report limit.
- A blocking review or validation issue remains unresolved.
- The user must decide between competing product or technical directions.

A task may be marked `partial` when:

- Useful work was completed but final validation or acceptance is intentionally deferred.
- The user asked for a partial refactor or staged migration.
- The implementation is complete but evidence is limited and disclosed.

## Escalation Rules

Escalate from `lite` to `standard` when:

- Code changes span more than one small ownership boundary.
- A reviewer is needed to inspect potential regression.
- Tests or validation decisions are non-trivial.

Escalate from `standard` to `full` when:

- The task is cross-module or high-risk.
- It touches concurrency, availability, public API contracts, dependency resolution, private libraries, subscriptions, BLE/Mesh, persistence, signing, or release paths.
- Failure attribution requires tester exploration.
- The user requests full validation or release confidence.

Escalate to `final-evidence-gate` / `verify-ios-build` only when:

- The user explicitly asks for final evidence or project-environment verification.
- Targeted validation is insufficient for risk level.
- Project or dependency configuration changed.
- Release, archive, signing, or merge confidence is required.

Escalate to raw logs only when:

- `diagnostics.json`, `build-summary.txt`, and `test-summary.json` are insufficient.
- The raw log section is narrowly targeted.
- The user explicitly requests raw log analysis.

## Model Selection Guidance

When runtime supports per-subAgent model selection:

- `coder worker`: quality-priority model.
- `reviewer explorer`: fast reading/review model.
- `tester explorer`: quality-priority model with medium reasoning when failure attribution is complex.

Do not hardcode model names in this Skill. Available model names depend on runtime and account state. If a requested model is unavailable, omit the model parameter and inherit the Main Agent default.

## Plan Output Template

When the user asks for a plan and the task includes implementation / verification:

```text
Step 1 Main Agent: intent, boundaries, success criteria, level, baseline, fallback conditions.
Step 2 Coder Worker: implementation ownership and forbidden changes.
Step 3 Testing: suggested_validation, executed_validation, failure_attribution, needs_test_code.
Step 4 Code Review: blocking_findings and non_blocking_findings.
Step 5 Main Agent: aggregate, loop control, final gate, residual risks.
```

For private library local debugging, add:

```text
- Resolve local :path dependency ownership.
- Modify and validate the private library source repository.
- Keep main project local :path validation unless the user asks to restore versioned dependency.
```

## Examples

### Standard Feature Change

```json
{
  "task_type": "code-medium",
  "orchestration_level": "standard",
  "roles_used": ["main", "coder", "reviewer"],
  "validation_route": "ios-affected-tests + targeted build",
  "final_gate": "targeted validation + code-review"
}
```

### Risky BLE / Mesh Change

```json
{
  "task_type": "code-risky",
  "orchestration_level": "full",
  "roles_used": ["main", "coder", "reviewer", "tester"],
  "validation_route": "affected tests first; real-device verification only if explicitly required",
  "raw_log_policy": "diagnostics.json first"
}
```

### Documentation-Only Change

```json
{
  "task_type": "doc-only",
  "orchestration_level": "lite",
  "roles_used": ["main"],
  "validation": {
    "executed": [],
    "no_test_reason": "Documentation-only change; no runtime behavior changed."
  }
}
```

## Reference Files

Read these only when needed:

- `references/coding-standards.md`: coder / reviewer / tester / main coding and output rules.
- `references/checkpoint-contract.md`: CP0 / CP1 / CP2 / CP3 and fail-fix-report contract.
- `references/tool-routing.md`: role-to-tool routing matrix.
- `references/model-selection.md`: role-based model selection and fallback strategy.
- `references/role-contracts.md`: role input/output contracts.
- `references/prompt-templates.md`: coder / reviewer / tester prompt templates.
- `references/handoff-loop.md`: failure loop, handoff, and stop conditions.
- `references/apple-gate-rules.md`: Apple / Xcode optional evidence verification constraints.

## Relationship to Other Skills

- This Skill is the default iOS main entry and decides when to call other Skills.
- Implementation routes to `ios-feature-implementation`, `swiftui-feature-implementation`, `uikit-feature-implementation`, or `swift-expert`.
- Debugging routes to `debugging`.
- Performance routes to `ios-performance`.
- Apple documentation routes to `apple-docs`.
- Testing routes to `testing` and may use `ios-affected-tests`.
- Build failure attribution routes to `ios-build-log-digest`.
- Verification routing uses `ios-verification-router`.
- Optional final evidence routes to `final-evidence-gate` / `verify-ios-build`.
