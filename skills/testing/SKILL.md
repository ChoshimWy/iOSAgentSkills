---
name: testing
description: iOS/macOS 测试编写与定向测试策略 Skill。只在需要编写或补充单元测试、UI 测试、Mock/Stub/Spy、async 测试代码，或为实现链路选择最窄定向测试面时使用；不要把一次性编译验证、构建门禁、性能 benchmark、代码审查或运行时排障误判到本 Skill。
---

# iOS 测试编写

## Purpose

Design, add, or refine iOS/macOS tests and targeted validation plans while keeping the default execution scope as narrow, deterministic, and low-token as possible.

## 中文说明

该 Skill 是测试编写与定向测试策略专项 Skill。它负责：

- 为业务逻辑补单元测试。
- 为 UI 流程补 `XCUITest` 或 Page Object。
- 设计 `Mock`、`Stub`、`Spy`、fixture 与 async 测试结构。
- 在实现链路中选择最窄可执行测试面。
- 在无法新增测试或无法低成本执行测试时，输出 `no_test_reason` 与 `suggested_validation`。

该 Skill 不负责完整项目环境构建验证、最终门禁裁决、性能 benchmark、完整代码审查或运行时 crash 排障。

## When to Use

Use this Skill when:

- Existing iOS/macOS production code needs unit tests.
- UI flows need `XCUITest`, Page Object, accessibility identifier, or wait strategy.
- A feature needs `Mock`, `Stub`, `Spy`, fake service, fixture, or deterministic async testing.
- An implementation task enters the default sequence: implementation -> testing / targeted validation -> code-review.
- The Agent needs to choose affected tests or `-only-testing` for a code change.
- A test failure needs compact attribution related to the current change.
- The task requires deciding whether new test code is useful, feasible, or too expensive.

## When Not to Use

Do not use this Skill when:

- The user only asks to run a final compile check, build verification, or `xcodebuild` gate; use `final-evidence-gate` / `verify-ios-build`.
- The user asks for signing, Archive, Export, CI, Build Settings, xcconfig, build scripts, or destination design; use `xcode-build`.
- The task is pure code quality review or PR review; use `code-review`.
- The task is runtime crash, memory leak, hang, or behavior debugging; use `debugging`.
- The task is performance benchmark, `measure(metrics:)`, startup regression, `xctrace`, or Instruments evidence; use `ios-performance`.
- The task is simulator/device install, launch, screenshot, navigation, or automation workflow; use `ios-automation`.

## Agent Rules

### Test Design Rules

- Use test names in the format `test_[method]_[condition]_[expected]`.
- Cover happy path, error path, boundary conditions, and async behavior when relevant.
- Tests must be independent and deterministic.
- Do not rely on real network, uncontrolled file system state, arbitrary `sleep`, wall-clock timing, or external services.
- Prefer public API behavior testing over direct private method testing.
- Use dependency injection to provide mocks, stubs, spies, fake clocks, fake queues, fake network clients, and fake persistence layers.
- For async tests, prefer structured expectations, deterministic callbacks, async/await, injected schedulers, or controlled clocks.
- For UI tests, use Page Object, `accessibilityIdentifier`, and `waitForExistence(timeout:)`.

### Narrow Validation Rules

- If this task changed code, prefer the narrowest meaningful XCTest path.
- Selection order: single test method -> single test class -> smallest affected test file / bundle.
- Prefer `-only-testing` over full test bundle execution.
- Use `ios-affected-tests` when mapping changed files to test classes is non-trivial.
- Keep `ios-affected-tests` as a selection helper only; this Skill still owns actual targeted validation execution and `no_test_reason` decisions.
- Do not automatically expand to UI tests, simulator navigation, or real-device validation.
- Real-device / simulator verification is not part of default testing execution scope.
- If no low-cost test exists, output `no_test_reason` and `suggested_validation`; do not auto-escalate to full build or device testing.

### Xcode Execution Rules

- When actually executing project-environment XCTest or build/test commands, use the target project root.
- If validation-type `xcodebuild` is needed, prefer target project `./codex_verify.sh`.
- If project wrapper is absent, use `~/.codex/bin/codex_verify`.
- Wrapper must submit validation-type `xcodebuild` to shared build-queue daemon.
- Reuse Xcode system DerivedData via daemon; do not expose or reintroduce `XCODE_DERIVED_DATA_*` / `CODEX_DERIVED_DATA_SLOT` public configuration.
- If those deprecated variables exist, wrapper should fail fast.
- If a later `final-evidence-gate` / `verify-ios-build` step is needed, reuse the same workspace / scheme / destination baseline unless there is a clear reason to change.

### Scheme and Dependency Rules

- If the user does not specify scheme, prefer schemes bound to unit test targets / bundles such as `*Tests`.
- If no unit test scheme exists, fall back to other test schemes such as `*UITests` or `*_TEST`.
- If both `.xcworkspace` and `.xcodeproj` exist, prefer `.xcworkspace` for iOS projects.
- For private Pod / private component changes, run targeted validation with the main project using local `:path` dependency when required.
- Do not switch to online versioned dependency or `Pods/` vendored snapshot as validation baseline unless the user explicitly asks.

### File Header Rules

When creating new `.swift`, `.h`, `.m`, or `.mm` files and the project requires file headers:

- `Created by` must use the local user name from `whoami`.
- Do not write `Codex` as creator.
- Date format should be `YYYY/M/D`, for example `Created by $(whoami) on 2026/4/11.`.

### Token Budget

- Do not paste full test logs.
- Do not paste full build logs.
- Do not dump full `.xcresult` JSON.
- Prefer compact test summaries.
- Prefer script-generated `verification-report.json`, then `diagnostics.json`, `test-summary.json`, and `build-summary.txt` when available.
- For failures, report only the first real failure relevant to the current change.
- Avoid scanning unrelated test suites when affected tests are sufficient.

## Common Patterns

| Pattern | Use For | Notes |
| --- | --- | --- |
| `Mock` | Verify call count, parameters, or collaboration | Use `callCount`, `lastParams`, or recorded calls. |
| `Stub` | Control return value or error | Use `result`, `error`, or fixture payload. |
| `Spy` | Record call history | Store inputs in arrays for assertions. |
| `Fake` | Deterministic replacement for external dependency | Useful for clocks, queues, network, persistence. |
| Page Object | UI test readability and stability | Wrap UI queries and actions. |

## Inputs

Expected input contract:

```json
{
  "goal": "Add tests or choose targeted validation",
  "changed_files": [],
  "production_files": [],
  "test_files": [],
  "known_test_targets": [],
  "workspace": "App.xcworkspace",
  "scheme": "AppTests",
  "constraints": ["narrowest validation", "do not run full build"],
  "allow_ui_tests": false,
  "allow_device_validation": false
}
```

Minimal input when used in an implementation chain:

```json
{
  "changed_files": [],
  "goal": "Select targeted tests and report no_test_reason if no low-cost path exists"
}
```

## Outputs

Return compact structured output:

```json
{
  "status": "passed | failed | skipped | blocked | proposed",
  "test_changes": {
    "added_or_modified_tests": [],
    "test_doubles": [],
    "fixtures": []
  },
  "suggested_validation": [],
  "executed_validation": [],
  "affected_tests": [
    "AppTests/SubscriptionServiceTests/test_purchase_withValidProduct_succeeds"
  ],
  "failure_attribution": "none | current_change | pre_existing | environment | unknown",
  "failure_attribution_type": "none | compile | test_assertion | timeout | simulator | device | dependency | signing | unknown",
  "first_failure": null,
  "needs_test_code": "yes | no",
  "no_test_reason": null,
  "suggested_next_skill": "code-review | ios-affected-tests | ios-build-log-digest | final-evidence-gate | verify-ios-build | none",
  "next_action": "code-review | ios-affected-tests | verify-ios-build | blocked | none"
}
```

Field rules:

- `suggested_validation`: next narrow validation to run.
- `executed_validation`: validations actually executed in this turn with result summaries.
- `affected_tests`: exact `-only-testing` candidates when known.
- `failure_attribution`: evidence-backed attribution only; do not guess.
- `first_failure`: first real failure relevant to this change, or `null`.
- `needs_test_code`: `yes` only when new/modified test code is necessary and feasible.
- `no_test_reason`: required when no test code was added or no low-cost test path exists.

## Exit Conditions

Return `passed` when:

- Test code was added/updated successfully and relevant targeted tests passed, or
- Existing targeted validation passed and no new test code was required.

Return `proposed` when:

- The task only requested test design or test plan and no code execution was expected.

Return `skipped` when:

- The change is doc-only, rule-only, or otherwise has no meaningful test surface.
- A clear `no_test_reason` and alternative validation basis are provided.

Return `failed` when:

- A targeted test or test compile step ran and produced a real failure.
- `first_failure` is identified and attributed where possible.

Return `blocked` when:

- Project, scheme, test target, dependency, device, environment, or permissions prevent targeted testing.
- Required fixture / credential / simulator state is unavailable.
- The user must decide whether to add test seams or accept no low-cost test path.

## Escalation Rules

Escalate to `ios-affected-tests` when:

- Changed files do not map clearly to test classes.
- Multiple modules changed and affected test selection is non-trivial.
- The Agent needs exact `-only-testing` suggestions.

Escalate to `ios-build-log-digest` when:

- Test/build execution fails and compact script evidence is missing or insufficient.
- Failure attribution needs compact diagnostics.

Escalate to `code-review` when:

- Tests or `no_test_reason` are ready and implementation risk must be reviewed.
- The task needs quality, architecture, availability, or regression review rather than more testing.

Escalate to `final-evidence-gate` when:

- Targeted tests passed but the risk profile may require stronger evidence.
- Full project-environment evidence may be needed but should be decided by a gate.

Escalate to `verify-ios-build` only when:

- The user explicitly asks for project-environment build verification.
- `final-evidence-gate` decides existing evidence is insufficient.

Escalate to `ios-automation` when:

- The task becomes install, launch, navigation, screenshots, accessibility tree, or device/simulator workflow.

Escalate to `ios-performance` when:

- The task becomes benchmark, `measure(metrics:)`, startup performance, `xctrace`, or Instruments evidence.

## Example XCTest Pattern

```swift
final class UserServiceTests: XCTestCase {
    private var sut: UserService!
    private var mockNetwork: MockNetworkClient!

    override func setUp() {
        super.setUp()
        mockNetwork = MockNetworkClient()
        sut = UserService(network: mockNetwork)
    }

    override func tearDown() {
        sut = nil
        mockNetwork = nil
        super.tearDown()
    }

    func test_fetchUser_withValidID_returnsUser() async throws {
        mockNetwork.result = User.mock()
        let user = try await sut.fetchUser(id: "1")
        XCTAssertEqual(user.name, "Test User")
    }
}
```

## Reporting Format

Use this compact text format when not returning JSON:

```text
Testing status: passed | failed | skipped | blocked
Affected tests:
- AppTests/SubscriptionServiceTests
Executed validation:
- AppTests/SubscriptionServiceTests: passed
No test reason: none
First failure: none
Next: code-review
```

If no low-cost test exists:

```text
Testing status: skipped
No test reason: no deterministic unit-level test seam exists for this UI-only layout change.
Suggested validation: build target + code-review; UI smoke only if final-evidence-gate escalates.
Next: code-review
```

## Final Evidence Handoff

For Apple Xcode project changes, default closure is:

```text
targeted testing / necessary validation + code-review no blocking findings
```

Rules:

- `final-evidence-gate` / `verify-ios-build` are optional strengthening steps.
- They are used only when the user explicitly asks or evidence/risk requires escalation.
- If this Skill executed `xcodebuild test/build`, evidence must come from the target project root environment.
- Sandbox build results cannot be treated as final project acceptance evidence.
- Later verification should reuse this Skill's workspace / scheme / destination baseline unless a switch is justified.

## Relationship to Other Skills

- In a non-orchestrated single-Agent implementation chain, this Skill is the default second step after implementation.
- After testing or `no_test_reason`, proceed to `code-review`.
- Use `ios-affected-tests` for affected test selection.
- Use `ios-build-log-digest` for compact failure attribution, starting from `verification-report.json`.
- Use `final-evidence-gate` for optional evidence sufficiency decisions.
- Use `verify-ios-build` only for explicit or escalated project-environment build verification.
- Use `debugging` for runtime crashes, leaks, hangs, or behavior investigation.
- Use `ios-performance` for benchmarks and Instruments workflows.
- Use `ios-feature-implementation` with `sdk-contract` mode when testability requires SDK-level boundary design.
