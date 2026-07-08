---
name: codex-subagent-orchestration
description: 默认优先使用的 iOS 主 Skill 入口；先按任务复杂度选择 lite / standard / full 档位，再协调 coder / reviewer / tester / reporter / main agent 分工；所有 iOS 生产代码与测试代码实施统一路由到 ios-feature-implementation 的内部模式，验证统一路由到 ios-verification，正式 HTML 文档生成统一路由到 html-docs，调试、性能、审查与构建配置仍路由到专项模块；除实现后的 code-review 必须由独立 reviewer subAgent 执行外，其它 subAgent 使用不做仓库级限制。
---

# Codex 多 Agent 编排

## Purpose

Coordinate iOS development tasks through an adaptive orchestration workflow while keeping verification narrow, evidence-based, and low-token by default. The repository does not add extra restrictions on coder, tester, pm, reporter, or other non-review subAgent usage; implementation closure still requires an independent reviewer subAgent for `code-review`.

## 中文说明

该 Skill 是本仓库默认 iOS 主入口。它不直接替代实现、测试、审查、构建或调试 Skill，而是负责：

- 判断任务类型与复杂度。
- 选择 `lite` / `standard` / `full` 编排档位。
- 协调 coder / reviewer / tester / reporter / main agent 的职责边界。
- 决定何时把代码实施路由到 `ios-feature-implementation` 的 `business` / `swiftui` / `liquid-glass` / `uikit` / `mixed-ui` / `advanced-swift` / `refactor` / `sdk-contract` 内部模式。
- 决定何时路由到验证、调试、性能、审查与构建模块。
- 在主 Agent 串行实现或自主拉起的多 Agent 场景下保证写入前 CP0 最小计划、checkpoint、fail-fix-report、低 token 验证纪律，以及独立 reviewer subAgent 审查纪律。

默认完成态必须由主 Agent 基于定向测试 / 必要验证与独立 reviewer subAgent 的 `code-review` 结论裁决；任何 subAgent 都不能替代主 Agent 宣告完成。
只有定向测试 / 必要验证已完成，且独立 reviewer subAgent 执行的 `code-review` 无 `阻塞问题` 时，主 Agent 才能宣告实现任务完成。

## When to Use

Use this skill when:

- The task is an iOS / Apple platform development task and does not clearly belong to one single specialized Skill.
- The task contains implementation, review, testing, debugging, performance, Apple API, or optional evidence verification steps.
- The task may benefit from adaptive role splitting; non-review subAgent usage is unrestricted by this repository policy, while implementation closure always requires an independent reviewer subAgent.
- The task involves multiple files, unclear risk, or a need to coordinate implementation and verification.
- The user explicitly asks to use the iOS Agent workflow, multi-agent Codex workflow, subAgent, parallel agent, or delegation workflow.

## When Not to Use

Do not use this Skill as the first route when the task is clearly one of these single-purpose tasks:

- Pure code review: route to an independent reviewer subAgent running `code-review`.
- Pure test writing: route directly to `ios-feature-implementation` with `test-implementation` mode.
- Pure Xcode build setting, signing, archive, or export task: route directly to `xcode-build`.
- Pure validation routing, final evidence decision, or explicit project build verification: route to `ios-verification`.
- Pure Apple API / availability / WWDC lookup: route to `apple-docs`.
- Pure runtime crash or debugging request: route to `debugging`.
- Pure performance profiling or benchmark request: route to `ios-performance`.
- Pure formal documentation generation: route to `html-docs`.
- Pure documentation or rule edit that does not need role splitting.

## Agent Rules

### Hard Boundaries

- For iOS development tasks, this Skill is the default first route unless the task is clearly a doc-only / rule-only change or clearly belongs to one single-purpose Skill.
- Always classify task type before selecting `lite` / `standard` / `full`.
- Repair or implementation tasks do not depend on a manual Plan mode. The Main Agent may do minimal read-only discovery first, but before the first file write or patch it must publish or maintain a concise CP0 plan covering goal, impact scope, implementation steps, and validation / review path. Do not jump directly from code search to implementation.
- Do not add repository-level restrictions for coder / tester / pm / reporter subAgent usage; always use an independent reviewer subAgent for implementation-chain `code-review`.
- Let the Main Agent choose whether non-review roles run locally or as subAgents according to the current task and runtime; this repository policy adds no extra gate for those roles.
- Main-Agent implementation must still preserve targeted validation / `no_test_reason` and then hand off `code-review` to an independent reviewer subAgent.
- Do not use `multi_tool_use.parallel` when tools may touch the same write set, `apply_patch`, Git state, build queue, or project files.
- Do not introduce external orchestrators. Reviewer subAgent spawning is the required implementation review path; other subAgent usage is not restricted by this repository policy.
- Use only built-in `worker` and `explorer` agent types unless the runtime provides additional official types.
- Do not invent new low-level Agent types.

### Boundary Precedence

- `ios-feature-implementation` owns all production and test-code implementation modes, including `test-implementation`.
- `ios-verification` owns validation routing, affected-test selection, targeted execution, build/test digest, project-environment verification, and final evidence judgement.
- `debugging` owns runtime symptom diagnosis; `ios-performance` only owns performance evidence and benchmark workflows.
- `html-docs` owns final generation and style governance for formal HTML docs, including proposals, PRDs, reviews, reports, task lists, API docs, and handoff docs. Other Skills provide source packets, conclusions, and evidence paths instead of crafting the final HTML.

### Token Budget

- Prefer `rg` and precise file reads over broad scans.
- Do not paste large diffs, full files, full build logs, full `.xcresult` dumps, or recursive `DerivedData` output.
- Build / test / log output should be summarized as key error sections, filtered summaries, or the last 80-120 relevant lines.
- Long logs should be written to files and digested before being read by Agents.
- For build failures, prefer script-generated `verification-report.json`, then `diagnostics.json`, then `build-summary.txt`.
- Default raw log policy: forbidden unless summaries are insufficient or the user explicitly asks.

### Verification Discipline

- Implementation tasks must close through targeted validation / necessary validation and independent reviewer subAgent `code-review`.
- `ios-verification` is the unified validation path; stronger project-environment verification is still optional, not default mandatory closure.
- Use `ios-verification` before broad test execution, project-environment verification, raw log reading, or final evidence decisions.
- 真机 / 模拟器验证不属于默认验证执行面；只有用户显式要求、发布前自检、高风险或证据不足时才按需升级。
- Any local `xcodebuild` verification must go through the target project wrapper `./codex_verify.sh` when available, otherwise `~/.codex/bin/codex_verify`.
- Verification stdout must stay evidence-first and low-noise: the wrapper should print `verification-report.json` by default; Agents should not stream raw logs unless `CODEX_VERIFY_STREAM_LOG=1` is explicitly justified.
- Shared build-queue daemon remains the default path for validation-type `xcodebuild`.
- Reuse the same workspace / scheme / destination baseline when a task already ran targeted build or test validation.

### Private Pod / Local Path Rules

- If the target project uses CocoaPods and the task touches private components or dependency integration, inspect `Podfile`, `Podfile.lock`, and `Pods/Manifest.lock` before implementation.
- If a local `:path` private Pod is active, modify the real component repository, not the `Pods/<LibraryName>` vendored copy.
- During local integration, keep the main project on the local `:path` dependency for development, verification, and independent `code-review`; switch to local `:path` only when the project is not already pointing at the local source and the private-library source change must be validated. After modifying the real private library repository, validate and review through the main project with that local dependency.
- After validation passes, keep the local `:path` dependency state by default for review and reporting; do not switch back to a versioned dependency or commit local `:path` dependency references unless the user explicitly asks or a main-project dependency-file commit requires it.

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
- Preserve targeted validation and independent reviewer subAgent `code-review` for implementation tasks.
- Use reviewer subAgent only when a rule change needs risk review or when the task is an implementation-chain closure.

### `standard`

Use for normal code or workflow changes with clear boundaries.

Default behavior:

- `coder worker` for implementation when the Main Agent chooses to delegate; otherwise the main Agent performs the implementation role.
- `reviewer explorer` using `code-review` for every implementation task after targeted validation / necessary validation; do not run implementation-chain review in the main Agent.
- Main Agent aggregates and decides closure.
- Start `tester explorer` when the Main Agent chooses to delegate validation planning or failure attribution; otherwise the main Agent applies the tester contract.

### `full`

Use for high-risk or cross-module tasks.

Default behavior:

- `coder worker` for implementation when the Main Agent chooses to delegate; otherwise the main Agent owns implementation.
- `reviewer explorer` using `code-review` is mandatory for implementation-chain closure; if it cannot be started, report blocked / pending review instead of self-reviewing.
- `tester explorer` for test surface, validation advice, and failure attribution when the Main Agent chooses to delegate; otherwise the main Agent follows tester output requirements.
- Main Agent controls checkpoint, loop count, and final closure.
- Use stronger `ios-verification` execution only when risk or user request justifies it.

## Role Activation Matrix

Default minimum logical role set: `explorer + builder + reporter`. These roles may be handled by the main Agent in single-Agent mode, but implementation-chain `reviewer explorer` is a required independent subAgent and is not optional.

Activate additional roles only when justified:

| Role | Activate When | Default Skill Reuse |
| --- | --- | --- |
| `pm` | Requirements are unclear, acceptance criteria are missing, or goals conflict | planning / requirement clarification |
| `coder worker` | Production or test implementation is needed | `ios-feature-implementation` with `business` / `swiftui` / `liquid-glass` / `uikit` / `mixed-ui` / `advanced-swift` / `refactor` / `sdk-contract` / `test-implementation` mode |
| `reviewer explorer` | Any implementation task; risky rule changes | `code-review` |
| `tester explorer` | Test surface exists, failure attribution is needed, or task is `code-risky` | `ios-verification` |
| `tester worker` | Test code must be added or updated | `ios-feature-implementation(test-implementation)` |
| `reporter` | Delivery summary, acceptance matrix, residual risk; if the deliverable must be a formal HTML document, prepare a compact source packet and route to `html-docs` | this Skill / `html-docs` |
| `main agent` | Always active for aggregation, control, and final decision | this Skill |

## Workflow

1. Main Agent performs only the minimum read-only discovery needed to avoid guessing.
2. Main Agent determines intent, ownership, success criteria, risk level, and task type, then completes CP0 with a concise pre-implementation plan even when the runtime is not in Plan mode.
3. Main Agent freezes relevant workspace / scheme / destination baseline when verification may be needed.
4. Main Agent checks private Pod / local `:path` ownership if dependencies are involved.
5. Main Agent selects `lite` / `standard` / `full`.
6. Main Agent may choose whether coder / tester / pm / reporter roles run locally or as subAgents; this repository policy adds no extra gate for non-review roles. For implementation-chain closure, Main Agent must spawn an independent reviewer subAgent for `code-review`; if unavailable, stop with blocked / pending review.
7. Use `spawn_agent` / `send_input` / `wait_agent` / `close_agent` sparingly; `wait_agent(...)` is used only when the result is needed to advance the next step. Reviewer subAgent receives only the frozen diff, validation story, and review contract, not implementation rationale that would bias review.
8. If reviewer or tester finds a blocking issue, Main Agent decides whether to fix locally or route the precise issue back to an active coder subAgent with `send_input(..., interrupt=true)`.
9. If tester determines test code is required, Main Agent decides whether to handle test edits locally or start `tester worker`.
10. Main Agent applies fail-fix-report discipline until resolved or blocked.
11. Main Agent performs final closure only when targeted validation / necessary verification is current and independent reviewer subAgent `code-review` has no `阻塞问题`.
12. Only if requested or high-risk, Main Agent routes to `ios-verification` for stronger evidence.
13. If the task needs a shareable / archived HTML document, Main Agent routes the final source packet to `html-docs`; this Skill does not duplicate HTML templates or visual styling.

## Checkpoints

Default checkpoints:

| Checkpoint | Meaning |
| --- | --- |
| `CP0 Intent Lock` | Confirm intent, constraints, success criteria, non-goals, and a pre-implementation plan before any write. |
| `CP1 Anchor Slice` | Complete and inspect the first meaningful slice before expanding parallel work. |
| `CP2 Validation Baseline Freeze` | Freeze validation baseline, affected tests, wrapper path, and log policy. |
| `CP3 Final Gate` | Decide completion based on evidence and `阻塞问题`. |

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
  "success_criteria": ["targeted validation passes", "code-review has no 阻塞问题"],
  "preferred_validation": "auto"
}
```

Optional runtime inputs:

```json
{
  "workspace": "App.xcworkspace",
  "scheme": "App",
  "destination": "platform=iOS Simulator,id=<selected-simulator-id>",
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
    "阻塞问题": [],
    "非阻塞建议": []
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
- `reviewer explorer`: `阻塞问题`, `非阻塞建议`。
- `tester explorer`: `suggested_validation`, `executed_validation`, `failure_attribution`, `failure_attribution_type`, `needs_test_code`.
- `reporter`: `acceptance_matrix`, `residual_risks`, `completion_status`.

## Exit Conditions

A task may be marked `completed` only when:

- User goal is satisfied or explicitly scoped down.
- Changed files are summarized.
- Targeted validation / necessary verification is executed or a clear `no_test_reason` is provided.
- `code-review` has no `阻塞问题`.
- Known risks are disclosed.
- No subAgent has unresolved blocking output when native subAgents were used.
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

Escalate to stronger `ios-verification` execution only when:

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
- `reviewer explorer`: `gpt-5.3-codex-spark` by default for fast reading/review.
- `tester explorer`: quality-priority model with medium reasoning when failure attribution is complex.

Do not hardcode other model names in this Skill. Available model names depend on runtime and account state. If the reviewer default model or another requested model is unavailable, omit the model parameter and inherit the Main Agent default.

## Plan Output Template

For every repair or implementation task, complete a compact CP0 plan before the first write even when the user did not manually enter Plan mode. If the user explicitly asks for a plan, use the same structure with more detail:

```text
Step 1 Main Agent: intent, boundaries, success criteria, level, baseline, fallback conditions.
Step 2 Coder Worker: implementation ownership and forbidden changes.
Step 3 Verification: suggested_validation, executed_validation, failure_attribution, no_test_reason.
Step 4 Code Review: 阻塞问题 and 非阻塞建议.
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
  "validation_route": "ios-verification + targeted build",
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
  "raw_log_policy": "verification-report.json first"
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

- `references/coding-standards.md`: role output rules and pointer to shared iOS coding standards.
- `references/checkpoint-contract.md`: CP0 / CP1 / CP2 / CP3 and fail-fix-report contract.
- `references/tool-routing.md`: role-to-tool routing matrix.
- `references/model-selection.md`: role-based model selection and fallback strategy.
- `references/role-contracts.md`: role input/output contracts.
- `references/prompt-templates.md`: coder / reviewer / tester prompt templates.
- `references/handoff-loop.md`: failure loop, handoff, and stop conditions.
- `references/apple-gate-rules.md`: Apple / Xcode optional evidence verification constraints.

## Relationship to Other Skills

- This Skill is the default iOS main entry and decides when to call other Skills.
- Implementation routes to `ios-feature-implementation`; select its internal mode instead of switching among separate implementation Skills.
- Debugging routes to `debugging`.
- Performance routes to `ios-performance`.
- Apple documentation routes to `apple-docs`.
- Test code implementation routes to `ios-feature-implementation(test-implementation)`.
- Validation, build/test failure attribution, project-environment verification, and optional final evidence judgement route to `ios-verification`.
- Formal HTML documentation routes to `html-docs`; this includes proposals, PRDs, review reports, run reports, task lists, API docs, and handoff docs.
