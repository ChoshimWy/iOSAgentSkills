---
name: ios-feature-implementation
description: 统一 iOS 实施 Skill。作为所有 iOS 代码实施、页面落地和结构重构的单一实现入口；根据本地项目事实自动选择 business、swiftui、uikit、mixed-ui、advanced-swift、refactor 或 sdk-contract 模式，覆盖 service/repository/use case/view model/coordinator/router、SwiftUI/UIKit 页面与组件、复杂 Swift 并发/Sendable/泛型/类型擦除、行为保持型重构、跨模块 API 接线；不要再把普通 SwiftUI/UIKit/Swift 进阶实施拆到独立实现 Skill，构建配置、运行时调试、性能取证、Apple 官方事实检索和纯测试编写仍路由到对应专项 Skill。
---

# iOS Feature 实施统一入口

## Purpose

Implement iOS / Apple-platform code through one implementation Skill that first detects the project technology stack and task shape, then applies the right internal mode without forcing the user or upstream orchestrator to choose SwiftUI, UIKit, business logic, advanced Swift, or refactoring manually.

## 中文说明

该 Skill 是 iOS 实施类任务的唯一默认实现入口。它把原先分散在通用业务实现、SwiftUI 页面、UIKit 页面、Swift 进阶设计和通用重构里的实施规则合并为内部模式：

| Mode | 适用场景 | 重点输出 |
| --- | --- | --- |
| `business` | service / repository / use case / domain model / view model / coordinator / router / DI / async 业务流程 | 行为、契约、依赖、错误语义 |
| `swiftui` | SwiftUI 页面结构、`NavigationStack`、sheet、状态归属、组件、列表、表单、动画、预览、SwiftUI 视图重构 | view structure、state ownership、navigation |
| `uikit` | `UIViewController`、`UIView`、Auto Layout、SnapKit、table / collection、cell 复用、事件绑定 | UI 结构、布局、生命周期 / 内存 |
| `mixed-ui` | SwiftUI + UIKit 桥接、hosting/controller 包装、跨技术栈导航接线 | 桥接边界、ownership、生命周期 |
| `advanced-swift` | actor、`Sendable`、取消传播、重入、PAT、复杂泛型、类型擦除、跨平台可用性、public/open API | API 边界、并发不变量、可用性 |
| `refactor` | 长方法、重复逻辑、深层嵌套、回调地狱、God Object、行为保持型整理 | refactoring pattern、行为保持证据 |
| `sdk-contract` | SDK / framework public API、configuration、模块边界、二进制/源码兼容接线 | public contract、availability、migration |

不负责：构建设置/签名/Archive/CI、运行时 crash/leak/hang 定位、性能 profiling / benchmark、纯测试补写、Apple 官方事实检索。这些仍交给 `xcode-build`、`debugging`、`ios-performance`、`testing`、`apple-docs` 等专项 Skill。

## When to Use

Use this Skill when the user asks to implement, modify, wire, or refactor iOS code and the work is primarily code implementation rather than pure diagnosis or build/release configuration. Typical triggers include:

- Service、Repository、UseCase、Domain model、DTO / mapper、ViewModel、Coordinator、Router、DI。
- SwiftUI screen/component/state/navigation/refactor/previews。
- UIKit ViewController/View/layout/list/cell/event binding。
- SwiftUI 与 UIKit 混合接线。
- Complex Swift concurrency, `Sendable`, actor isolation, cancellation, reentrancy, type erasure, generics, or availability when implementation is required.
- Behavior-preserving code refactoring where touched code belongs to an iOS / Apple project.
- Public/open API or cross-module reusable implementation that is not a full SDK architecture design task.

## When Not to Use

Do not use this Skill as the main route when:

- The task is pure code review or PR review; use an independent reviewer subAgent running `code-review`.
- The task is pure test writing, mock/stub/spy design, or targeted XCTest execution; use `testing`.
- The task is Xcode Build Settings, signing, Archive/Export, scheme, xcconfig, CI/CD, or XCFramework packaging; use `xcode-build`.
- The task is runtime crash, exception, leak, hang, watchdog, or incorrect runtime behavior diagnosis before implementation; use `debugging`.
- The task is frame drops, startup, CPU/memory pressure, `xctrace`, Instruments, or benchmark; use `ios-performance`.
- The task is Apple API / availability / WWDC fact lookup; use `apple-docs` first.
- The task is product UI visual exploration without code; use design/product skills before implementation.

## Agent Rules

### Entry and Mode Selection

1. Inspect local project facts before choosing mode: target files, imports (`SwiftUI`, `UIKit`, `AppKit`), existing architecture, deployment target hints, tests, project conventions, and user constraints.
2. Select exactly one primary `implementation_mode`; add `secondary_modes` only when the change genuinely crosses boundaries.
3. Do not ask the user to choose UIKit vs SwiftUI when the repository already makes it clear.
4. Do not switch to removed standalone implementation Skills; this Skill owns all implementation modes.
5. If the task was routed from `codex-subagent-orchestration`, preserve its task type, checkpoint, validation baseline, and reviewer handoff requirements.

### Shared Implementation Rules

- Keep changes minimal and scoped to the requested behavior.
- Prefer existing project architecture and naming over introducing a new pattern.
- Keep business logic out of SwiftUI `body` and UIKit view controllers when a service / view model / model layer is available.
- Use strict access control and value types where appropriate.
- Use `guard` for early exits when it improves readability.
- Keep UI updates on the main thread or under `@MainActor` isolation.
- Keep side effects explicit: state, database, cache, disk, network, notification, device, or dependency changes.
- Avoid hidden global mutable state and unnecessary singletons.
- Do not rewrite unrelated code, rename files broadly, or move directories without a task reason.
- Do not roll back user or other Agent changes.

### Mode-Specific Rules

#### `business`

- Separate domain logic from networking, persistence, and UI.
- Prefer dependency injection over hidden singletons for newly testable behavior.
- Make error, cancellation, retry, and fallback semantics visible.
- For navigation/deep links, keep route identity and ownership clear.
- Read `references/navigation.md` and `references/memory-management.md` when routing or lifecycle details are non-trivial.

#### `swiftui`

- Keep root view structure stable and avoid heavy side effects inside `body`.
- Decide state ownership explicitly: View, ViewModel, router/store, environment, or domain layer.
- Respect minimum deployment target; do not introduce iOS 17-only `@Observable` patterns into lower-target projects unless guarded or already adopted.
- Prefer small focused subviews when `body` becomes hard to read; avoid unnecessary `AnyView`.
- Keep list identity stable and async state transitions explicit: loading, success, empty, error.
- Read `references/swiftui/components-index.md` first when selecting detailed SwiftUI guidance.

#### `uikit`

- Keep UIKit code focused on rendering, layout, binding, reuse, lifecycle, and interaction.
- Follow existing layout conventions; if the project uses SnapKit, follow local SnapKit style.
- Avoid ambiguous constraints and unnamed magic layout constants when they affect reuse.
- Keep cell configuration idempotent and reset reusable state in `prepareForReuse` when needed.
- Avoid retaining index paths across async boundaries without validation.
- Cancel subscriptions, tasks, timers, notifications, and observers according to lifecycle ownership.
- Read `references/uikit/uikit.md` when page structure or list/reuse behavior is central.

#### `mixed-ui`

- State which side owns navigation, presentation, lifecycle, and observable state.
- Keep hosting wrappers thin; do not duplicate business state between UIKit and SwiftUI.
- Document bridge side effects such as delegate callbacks, Combine/async streams, notifications, and dismissal ownership.

#### `advanced-swift`

- Prefer simple concrete types unless abstraction is justified.
- Define mutable state ownership and actor/main-thread isolation.
- Avoid unstructured tasks unless lifecycle and cancellation are explicit.
- Propagate cancellation where parent work is cancelled.
- Analyze actor reentrancy across suspension points.
- Use `@unchecked Sendable` only with documented invariants.
- For protocols with associated types, type erasure, existentials, or opaque returns, document why a simpler concrete/generic design is insufficient.
- Read `references/swift-advanced/async-concurrency.md`, `references/swift-advanced/protocol-oriented.md`, or related files only when that topic is active.

#### `refactor`

- Preserve behavior by default; do not mix unrelated feature work into a refactor-only change.
- Move in small steps and keep rollback scope obvious.
- Prefer seams that improve readability, ownership, and testability without over-abstracting.
- If behavior changes become necessary, report them as `contract_changes` and update the selected mode.
- Read `references/refactoring.md` when the task is primarily structural cleanup.

#### `sdk-contract`

- Treat public/open API, cross-module reusable types, protocols, and configuration objects as contracts.
- Document availability, source/binary compatibility expectations, failure semantics, side effects, and concurrency boundaries.
- If the task becomes broader SDK architecture or distribution strategy, escalate to `ios-sdk-architecture`.

### Private Dependency Rules

- If the target project uses CocoaPods and the task involves private components or local integration, inspect `Podfile`, `Podfile.lock`, and `Pods/Manifest.lock`.
- If a local `:path` Pod is active, modify the real component repository, not `Pods/<LibraryName>`.
- Treat `Pods/<LibraryName>` as forbidden write scope when it is a vendored snapshot.
- For private library/component implementation, keep or switch the main project to local `:path` dependency for development and validation unless the user explicitly asks otherwise.
- Do not switch validation baseline to an online versioned dependency unless explicitly requested.

### Coding Standards

- Follow `references/coding-standards.md` as the shared iOS coding-standard source when touched code involves public API, comments, concurrency, UI ownership, reusable components, or style-sensitive refactors.
- For tiny local fixes, apply the summary rules below without loading the reference unless uncertainty remains.

### Documentation / Comment Rules

- Add `///` documentation for public/open APIs, cross-module reusable types, reusable protocols, and SDK-facing abstractions.
- Public API documentation must describe input, output, failure semantics, important side effects, and concurrency/actor assumptions when relevant.
- Add `why` comments for complex business branches, compatibility logic, concurrency invariants, side effects, or fallback paths.
- Update stale comments when behavior changes; remove misleading comments.
- Do not add comments that merely restate Swift / UIKit / SwiftUI syntax.

### File Header Rules

When adding `.swift`, `.h`, `.m`, or `.mm` files and the project requires headers:

- `Created by` must use local `whoami`.
- Do not write `Codex`.
- Date format: `YYYY/M/D`.

### Validation Handoff Rules

- Implementation does not jump to full project verification by default.
- Default implementation closure remains: implementation Skill, then `testing` / targeted validation, then independent reviewer subAgent running `code-review`.
- UI-only changes may have no low-cost unit test; provide `no_test_reason` and `suggested_validation` instead of silently skipping validation.
- `final-evidence-gate` / `verify-ios-build` are optional escalation paths only when user asks, release confidence is needed, project/dependency configuration changed, or risk/evidence requires it.
- The implementation Agent must not self-review its own implementation.

### Token Budget

- Prefer precise `rg` and targeted file reads over broad scans.
- Do not paste large diffs, full files, full build logs, full `.xcresult` dumps, or recursive `DerivedData` output.
- Summaries should focus on behavior, contracts, mode decision, risk, and validation impact.
- For build/test failures, prefer script-generated `verification-report.json`, then `diagnostics.json`, then `build-summary.txt` / `test-summary.json`.

## Inputs

Expected input contract:

```json
{
  "goal": "Implement, modify, wire, or refactor iOS code",
  "implementation_mode": "auto | business | swiftui | uikit | mixed-ui | advanced-swift | refactor | sdk-contract",
  "target_files": [],
  "ownership": [],
  "forbidden_paths": ["Pods/"],
  "constraints": [],
  "success_criteria": [],
  "existing_architecture": {
    "pattern": "MVVM | MVC | Coordinator | Store | SDK | unknown",
    "dependencies": []
  },
  "minimum_platforms": {},
  "preferred_validation": "auto"
}
```

## Outputs

Return compact structured output:

```json
{
  "status": "completed | partial | blocked",
  "implementation_mode": "business | swiftui | uikit | mixed-ui | advanced-swift | refactor | sdk-contract",
  "secondary_modes": [],
  "changed_files": [],
  "summary": [],
  "contract_changes": [],
  "ui_structure_changes": [],
  "state_ownership": null,
  "navigation_changes": [],
  "api_boundary_changes": [],
  "concurrency_invariants": [],
  "refactoring_patterns": [],
  "known_risks": [],
  "test_impact": "...",
  "no_test_reason": null,
  "suggested_validation": [],
  "suggested_next_skill": "testing | code-review | debugging | ios-performance | xcode-build | apple-docs | ios-sdk-architecture | blocked",
  "next_action": "run-targeted-tests | code-review | ask-user | blocked"
}
```

Field rules:

- `changed_files`: only files changed by this implementation.
- `summary`: behavior and implementation outcome, not raw diff.
- `contract_changes`: public API, model, error, persistence, navigation, dependency, side-effect, or availability contract changes.
- `test_impact` or `no_test_reason` must be present.
- Mode-specific arrays may be empty when not applicable; do not invent noise.
- `known_risks` should include real residual risk only; use `[]` when none.

## Exit Conditions

Return `completed` when:

- Requested implementation/refactor behavior is implemented or explicitly scoped down.
- Primary mode and any secondary modes are stated.
- Changes are scoped and summarized.
- Contract, UI, concurrency, and refactoring impact fields are filled as applicable.
- `test_impact` or `no_test_reason` is provided.
- Next validation/review step is clear.

Return `partial` when:

- Useful implementation progress was made but some requested behavior is intentionally deferred.
- Missing assets, product decisions, deployment target facts, API contracts, or validation access prevent full completion without invalidating completed work.

Return `blocked` when:

- Required project context, dependency source, API contract, product decision, credentials, or ownership is missing.
- Ownership would require modifying forbidden paths such as vendored `Pods/` snapshots.
- The task is actually build/release/debug/performance/doc-only work and cannot be safely handled as implementation.
- Independent reviewer handoff is required for completion but unavailable after implementation.

## Escalation Rules

Escalate to `testing` after code changes when targeted validation, test impact, mocks/stubs, or test code must be assessed.

Escalate to `code-review` after testing/necessary validation when static risk review and verification story review are needed; use an independent reviewer subAgent for implementation-chain closure.

Escalate to `debugging` when the task is driven by runtime crash, hang, leak, watchdog, incorrect object lifetime, or runtime-only symptoms.

Escalate to `ios-performance` when the task becomes frame drops, excessive layout/body invalidation, startup, CPU/memory regression, benchmark, `xctrace`, or Instruments.

Escalate to `xcode-build` when Build Settings, signing, Archive/Export, CI, scheme, xcconfig, or packaging becomes the main issue.

Escalate to `apple-docs` when official Apple API facts, availability, WWDC guidance, or sample code is required.

Escalate to `ios-sdk-architecture` when SDK/module boundaries, public framework architecture, distribution, or long-term versioning strategy becomes the main task.

Escalate to `ios-automation` when simulator/device UI smoke, screenshot, accessibility tree, installation, launch, or navigation evidence is required.

Escalate to `final-evidence-gate` / `verify-ios-build` only when explicitly requested, release/high-risk evidence is needed, or targeted evidence is insufficient.

## Reporting Format

```text
Implementation status: completed | partial | blocked
Mode: business | swiftui | uikit | mixed-ui | advanced-swift | refactor | sdk-contract
Changed files:
- ...
Summary:
- ...
Contract changes:
- ...
Mode-specific notes:
- UI/state/navigation/API/concurrency/refactoring notes as applicable
Known risks:
- ...
Test impact: ...
No test reason: none | ...
Suggested validation:
- ...
Next: testing/targeted validation, then independent reviewer subAgent(code-review)
```

## Reference Resources

Read only the reference files needed by the selected mode:

- `references/coding-standards.md`: shared Swift/iOS coding standards for implementation and review.
- `references/navigation.md`: business navigation, coordinator, and deep-link organization.
- `references/memory-management.md`: retain-cycle and lifecycle prevention.
- `references/swiftui/components-index.md`: SwiftUI reference router for screens, components, state, previews, navigation, and performance.
- `references/uikit/uikit.md`: UIKit page, layout, list/reuse, lifecycle, and memory guidance.
- `references/swift-advanced/async-concurrency.md`: async/await, actors, structured concurrency, cancellation.
- `references/swift-advanced/protocol-oriented.md`: protocols, PAT, associated types, type erasure, generics.
- `references/swift-advanced/memory-performance.md`: memory/performance tradeoffs in advanced Swift designs.
- `references/swift-advanced/swiftui-patterns.md`: SwiftUI-related advanced Swift patterns.
- `references/swift-advanced/testing-patterns.md`: async and advanced Swift testing patterns.
- `references/refactoring.md`: behavior-preserving refactoring mode guidance.

## Relationship to Other Skills

- `codex-subagent-orchestration` remains the default iOS main entry and decides when this implementation Skill is needed.
- Testing and targeted validation route to `testing`; use `ios-affected-tests` only to select a narrower test surface.
- Static review routes to independent reviewer subAgent `code-review`.
- Runtime diagnosis routes to `debugging`.
- Performance evidence routes to `ios-performance`.
- Build/release configuration routes to `xcode-build`.
- Device/simulator automation routes to `ios-automation`.
- Apple official facts route to `apple-docs`.
- Optional final evidence routes to `final-evidence-gate` / `verify-ios-build` only when required.
