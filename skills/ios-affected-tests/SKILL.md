# iOS Affected Tests

## Purpose

Map changed iOS source files to the smallest useful test set and avoid unnecessary full test runs.

中文说明：该 skill 用于让 Agent 在请求验证前根据 diff 推断最小测试面，优先生成 `-only-testing`，避免每次都跑完整 `xcodebuild test`。

## When to Use

Use this skill when:

- Swift, Objective-C, ViewModel, Service, Repository, StoreKit, BLE, database, or UI code changed.
- The user asks to reduce verification time.
- A build-queue request needs `only_testing` suggestions.
- Tests exist but full test execution is too expensive.

## Agent Rules

- Never default to full test for normal feature changes.
- Prefer the narrowest `-only-testing` target that gives useful signal.
- Prefer test class over whole test bundle.
- Prefer test method only when the changed behavior maps clearly to a single test case.
- If no meaningful low-cost test exists, provide `no_test_reason` and `suggested_validation` instead of escalating automatically.
- Do not run UI tests unless the change directly affects UI behavior and targeted UI tests are available or explicitly requested.
- If only production code changed and matching tests exist, request targeted unit tests plus build.
- If only tests changed, run only the changed tests.

## Mapping Rules

| Changed File Pattern | Suggested Test Scope |
| --- | --- |
| `*ViewModel.swift` | `*ViewModelTests` |
| `*Service.swift` | `*ServiceTests` |
| `*Repository.swift` | `*RepositoryTests` |
| `*UseCase.swift` | `*UseCaseTests` |
| `*Manager.swift` | matching manager tests, or integration build if no tests |
| `*StoreKit*`, `*Purchase*`, `*Subscription*` | subscription / purchase / receipt tests |
| `*Database*`, `*CoreData*`, `*WCDB*`, `*Persistence*` | persistence tests |
| `*Bluetooth*`, `*Mesh*`, `*BLE*`, `*Provision*` | mesh / BLE parser / state-machine tests; avoid real-device tests by default |
| `*Network*`, `*API*`, `*Client*` | network client / mock transport tests |
| `SwiftUI View` or `UIViewController` only | build; snapshot/UI tests only if targeted and cheap |
| `*.xcodeproj`, `Package.resolved`, `Podfile` | full build or dependency validation |
| `Tests/*` only | changed test class or method |

## Search Strategy

When proposing affected tests:

1. Identify changed production files.
2. Search for test files with matching basename.
3. Search for tests referencing the changed type name.
4. Search for tests in the same feature folder.
5. Prefer exact test class matches.
6. If no tests exist, report `no_test_reason`.

## Output Shape

Return a compact verification request:

```json
{
  "mode": "unit",
  "reason": "Changed SubscriptionService and PurchaseViewModel; matching unit tests exist.",
  "only_testing": [
    "AppTests/SubscriptionServiceTests",
    "AppTests/PurchaseViewModelTests"
  ],
  "also_build": true,
  "allow_full_build": false,
  "allow_full_log": false
}
```

If no targeted tests exist:

```json
{
  "mode": "build",
  "reason": "Changed BLE provisioning state machine; no low-cost deterministic unit tests found.",
  "no_test_reason": "No matching test class or stable simulator/device-independent test path exists.",
  "suggested_validation": "Run build plus code-review; add state-machine unit tests if this area changes repeatedly.",
  "allow_full_build": false,
  "allow_full_log": false
}
```

## Xcode Command Guidance

Prefer wrapper-level requests instead of raw `xcodebuild`:

```bash
./codex_verify.sh --mode unit \
  --only-testing AppTests/SubscriptionServiceTests \
  --only-testing AppTests/PurchaseViewModelTests
```

If the project wrapper is missing:

```bash
~/.codex/bin/codex_verify --mode unit \
  --only-testing AppTests/SubscriptionServiceTests
```

## Escalation Rules

Escalate from affected tests to full verification only when:

- Project or dependency configuration changed.
- A release, merge, or archive confidence gate is explicitly requested.
- Targeted tests passed but integration risk remains high and cannot be reviewed statically.
- The changed code crosses multiple modules with no reliable narrow test boundary.

## Reporting

Keep reporting concise:

```text
Affected tests selected:
- AppTests/SubscriptionServiceTests
- AppTests/PurchaseViewModelTests

Full test skipped: no project/dependency config changed.
```
