---
name: ios-feature-implementation
description: 统一 iOS 实施 Skill。作为所有 iOS 代码实施、测试代码编写、页面落地、SDK/Framework 架构契约和结构重构的单一实现入口；根据本地项目事实自动选择 business、swiftui、uikit、mixed-ui、advanced-swift、refactor、sdk-contract、liquid-glass 或 test-implementation 模式，覆盖 service/repository/use case/view model/coordinator/router、SwiftUI/UIKit 页面与组件、XCTest/XCUITest/Mock/Stub/Spy/Fake/fixture/Page Object、iOS 26+ SwiftUI Liquid Glass、复杂 Swift 并发/Sendable/泛型/类型擦除、行为保持型重构、跨模块 Public API、SDK 模块边界、Configuration、分发与版本演进；不要再把普通 SwiftUI/UIKit/Swift 进阶/SDK 架构/Liquid Glass 或测试代码编写拆到独立实现 Skill，构建配置、运行时调试、性能取证、Apple 官方事实检索和验证执行/证据裁决仍路由到对应专项 Skill。
---

# iOS Feature 实施统一入口

## Purpose

Implement iOS / Apple-platform production and test code through one implementation Skill that first detects the project technology stack and task shape, then applies the right internal mode without forcing the user or upstream orchestrator to choose SwiftUI, UIKit, business logic, advanced Swift, refactoring, SDK architecture, Liquid Glass, or test implementation manually.

## 中文说明

该 Skill 是 iOS 实施类任务的唯一默认实现入口。它把原先分散在通用业务实现、SwiftUI 页面、UIKit 页面、Swift 进阶设计、通用重构、SDK 架构、SwiftUI Liquid Glass 和测试代码编写里的实施规则合并为内部模式：

| Mode | 适用场景 | 重点输出 |
| --- | --- | --- |
| `business` | service / repository / use case / domain model / view model / coordinator / router / DI / async 业务流程 | 行为、契约、依赖、错误语义 |
| `swiftui` | SwiftUI 页面结构、`NavigationStack`、sheet、状态归属、组件、列表、表单、动画、预览、SwiftUI 视图重构 | view structure、state ownership、navigation |
| `liquid-glass` | iOS 26+ SwiftUI `glassEffect`、`GlassEffectContainer`、玻璃按钮样式、形态过渡、兼容回退 | API 选型、视觉层级、fallback |
| `uikit` | `UIViewController`、`UIView`、Auto Layout、Swift + SnapKit、Objective-C + Masonry、table / collection、cell 复用、事件绑定 | UI 结构、布局、生命周期 / 内存 |
| `mixed-ui` | SwiftUI + UIKit 桥接、hosting/controller 包装、跨技术栈导航接线 | 桥接边界、ownership、生命周期 |
| `advanced-swift` | actor、`Sendable`、取消传播、重入、PAT、复杂泛型、类型擦除、跨平台可用性、public/open API | API 边界、并发不变量、可用性 |
| `refactor` | 长方法、重复逻辑、深层嵌套、回调地狱、God Object、行为保持型整理 | refactoring pattern、行为保持证据 |
| `sdk-contract` | SDK / Framework public API、模块边界、入口类、Configuration、依赖方向、可测试性、SPM/XCFramework 分发、版本演进 | public surface、module boundaries、distribution、versioning |
| `test-implementation` | 单元测试、UI 测试、Mock / Stub / Spy / Fake、fixture、Page Object、async 测试、为测试补最小 seam / DI | deterministic tests、test doubles、fixtures、testability seam |

不负责：构建设置/签名/Archive/CI、运行时 crash/leak/hang 定位、性能 profiling / benchmark、验证执行/证据裁决、Apple 官方事实检索、纯视觉方向探索。这些仍交给 `xcode-build`、`debugging`、`ios-performance`、验证链路 Skill、`apple-docs`、`ui-ux-design-system` 等专项 Skill。

## When to Use

Use this Skill when the user asks to implement, modify, wire, design, or refactor iOS code and the work is primarily code implementation or SDK/API architecture rather than pure diagnosis or build/release configuration. Typical triggers include:

- Service、Repository、UseCase、Domain model、DTO / mapper、ViewModel、Coordinator、Router、DI。
- SwiftUI screen/component/state/navigation/refactor/previews。
- iOS 26+ SwiftUI Liquid Glass implementation or review, including `glassEffect`, `GlassEffectContainer`, `.buttonStyle(.glass)`, `.buttonStyle(.glassProminent)`, morphing, and compatibility fallback.
- UIKit ViewController/View/layout/list/cell/event binding。
- SwiftUI 与 UIKit 混合接线。
- Complex Swift concurrency, `Sendable`, actor isolation, cancellation, reentrancy, type erasure, generics, or availability when implementation is required.
- Behavior-preserving code refactoring where touched code belongs to an iOS / Apple project.
- Public/open API, cross-module reusable implementation, SDK / Framework module boundaries, entry types, configuration, distribution strategy, or versioning strategy.
- XCTest / XCUITest code authoring, Mock / Stub / Spy / Fake / fixture / Page Object design, deterministic async tests, or minimal production seams needed for testability.

## When Not to Use

Do not use this Skill as the main route when:

- The task is pure code review or PR review; use an independent reviewer subAgent running `code-review`.
- The task is targeted XCTest execution, build/test failure digest, or final verification evidence without editing production or test code; use `ios-verification`.
- The task is Xcode Build Settings, signing, Archive/Export, scheme, xcconfig, CI/CD, or packaging mechanics; use `xcode-build`.
- The task is runtime crash, exception, leak, hang, watchdog, or incorrect runtime behavior diagnosis before implementation; use `debugging`.
- The task is frame drops, startup, CPU/memory pressure, `xctrace`, Instruments, or benchmark; use `ios-performance`.
- The task is Apple API / availability / WWDC fact lookup; use `apple-docs` first.
- The task is product UI visual exploration, design-system direction, branding, color, or typography without code; use design/product skills before implementation.

## Agent Rules

### Entry and Mode Selection

1. Inspect local project facts before choosing mode: target files, imports (`SwiftUI`, `UIKit`, `AppKit`, `XCTest`), SDK/framework packaging, existing architecture, deployment target hints, tests, project conventions, and user constraints.
2. Select exactly one primary `implementation_mode`; add `secondary_modes` only when the change genuinely crosses boundaries.
3. Do not ask the user to choose UIKit vs SwiftUI when the repository already makes it clear.
4. Do not switch to removed standalone implementation Skills; this Skill owns all implementation modes, including SDK architecture, Liquid Glass, and test code implementation.
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
- Use `liquid-glass` mode, not generic `swiftui`, when the main problem is iOS 26+ glass API choice, fallback, or review.
- Read `references/swiftui/components-index.md` first when selecting detailed SwiftUI guidance.

#### `liquid-glass`

- Confirm Liquid Glass is actually needed before introducing the API surface; do not apply it as a full-page decoration by default.
- Prefer `glassEffect`, `GlassEffectContainer`, `.buttonStyle(.glass)`, and `.buttonStyle(.glassProminent)` where semantically appropriate.
- Always define compatibility fallback for non-iOS 26 paths when the deployment target or product surface requires it.
- Review fallback completeness, modifier ordering, interactive-only usage, shape consistency, and hierarchy consistency.
- Use `.interactive()` only for actionable/focusable elements, not passive decorative backgrounds.
- Keep related glass elements in the same `GlassEffectContainer` when they should share rendering, highlight, and morphing behavior.
- Document non-obvious availability guards, fallback rationale, visual hierarchy constraints, and interaction side effects in touched code.
- Read `references/swiftui/liquid-glass.md` when detailed API usage, examples, or review checks are needed.

#### `uikit`

- Keep UIKit code focused on rendering, layout, binding, reuse, lifecycle, and interaction.
- 新增或重写 UIKit 纯代码布局时：Swift 默认使用 SnapKit，Objective-C 默认使用 Masonry。
- 先检查目标 target 的依赖与同目录既有写法；若 SnapKit / Masonry 未集成，不得静默新增依赖，报告依赖缺口并遵循用户决定。
- 不为统一风格重构无关的既有 `NSLayoutConstraint` / 其他布局系统；在同一页面内避免混用多套约束 DSL。
- 仅在目标库不可用、系统 API 特殊要求或既有局部约定明确时，使用 `NSLayoutConstraint.activate([])`，并保持批量激活。
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

- Expose the minimum necessary public API and keep implementation details internal.
- Default dependency direction: `Public API Layer -> Feature Layer -> Core Layer -> Platform Layer`.
- Keep public API layer independent from concrete platform implementation details.
- Entry types own initialization, lifecycle, configuration validation, and high-level coordination only; do not put business implementation detail into the entry type.
- Public/open APIs must document input, output, failure semantics, availability, concurrency/actor assumptions, and side effects.
- Avoid leaking implementation types through public signatures; prefer stable value types for configuration.
- Keep callbacks, async streams, delegates, and closures lifecycle-safe.
- Define seams for network, persistence, BLE, device, clock, queue, logger, metrics, and transport dependencies when they affect deterministic tests.
- Prefer SPM source distribution unless binary distribution is required; use XCFramework for binary distribution and document platform, architecture, resource, sample app, and SemVer strategy.
- Read `references/sdk-architecture.md` when SDK boundaries, distribution, public API, testability, or versioning are central.

#### `test-implementation`

- Treat test code as implementation: keep it minimal, deterministic, and aligned with the production contract under test.
- Use test names in the format `test_[method]_[condition]_[expected]` unless the project already uses a different clear convention.
- Cover happy path, error path, boundary conditions, cancellation, and async behavior when relevant; do not add broad tests that do not assert the changed behavior.
- Prefer public API behavior testing over direct private method testing.
- Do not rely on real network, uncontrolled file system state, arbitrary `sleep`, wall-clock timing, external services, or device-only state unless the task explicitly targets that integration.
- Use dependency injection to provide `Mock`, `Stub`, `Spy`, `Fake`, fake clock, fake queue, fake network client, fake persistence, and fixture data.
- Keep test doubles local to the test target unless they are already shared by project convention.
- For async tests, prefer `async/await`, structured expectations, deterministic callbacks, injected schedulers, or controlled clocks.
- For UI tests, prefer Page Object structure, `accessibilityIdentifier`, and `waitForExistence(timeout:)`; screenshots are supporting evidence, not the assertion model.
- If production seams are required for testability, add the smallest DI or visibility seam that also improves the production design; do not expose internals only for tests unless the project already permits it.
- Keep fixtures small, explicit, and close to the test that owns them unless reuse is already established.
- If no useful test can be written without invasive seams, do not force a poor test; return `no_test_reason` and `suggested_validation`.
- Actual targeted XCTest execution, build/test failure digest, and final evidence sufficiency belong to the validation route after test code is written.

### Private Dependency Rules

- If the target project uses CocoaPods and the task involves private components or local integration, inspect `Podfile`, `Podfile.lock`, and `Pods/Manifest.lock`.
- If a local `:path` Pod is active, modify the real component repository, not `Pods/<LibraryName>`.
- Treat `Pods/<LibraryName>` as forbidden write scope when it is a vendored snapshot.
- For private library/component implementation, keep the main project on local `:path` dependency for development, validation, and independent `code-review` unless the user explicitly asks otherwise; switch to local `:path` only when the project is not already pointing at the local source and the private-library source change must be validated. After modifying the real private library repository, validate and review through the main project using the local dependency.
- After validation passes, keep the current local `:path` state by default for review and reporting; switch back to an online versioned dependency only when the user explicitly asks or when preparing main-project dependency files for commit.

### Coding Standards

- Follow `references/coding-standards.md` as the shared iOS coding-standard source when touched code involves public API, comments, concurrency, UI ownership, reusable components, or style-sensitive refactors.
- For tiny local fixes, apply the summary rules below without loading the reference unless uncertainty remains.

### Documentation / Comment Rules

- Add Chinese `///` documentation for public/open APIs, cross-module reusable types, reusable protocols, and SDK-facing abstractions.
- Public API documentation and inline comments must use Chinese by default, while keeping API names, type names, error codes, keywords, and log/error literals in their original spelling.
- Public API documentation must describe input, output, failure semantics, important side effects, and concurrency/actor assumptions when relevant.
- Add Chinese `why` comments for complex business branches, compatibility logic, concurrency invariants, side effects, or fallback paths.
- Update stale comments when behavior changes; remove misleading comments.
- Do not add comments that merely restate Swift / UIKit / SwiftUI syntax.

### File Header Rules

When adding `.swift`, `.h`, `.m`, or `.mm` files and the project requires headers:

- Before writing the new file, inspect sibling source files to confirm the local header style and target/project name.
- Resolve the real local author with `whoami` or `id -un`; insert that value in `Created by` immediately when creating the file.
- Do not write `Codex`, literal `$(whoami)`, `<user>`, or any other placeholder.
- Date format: `YYYY/M/D`.
- After edits, re-open each newly added Apple source file and verify the header before reporting completion.

### Validation Handoff Rules

- Implementation does not jump to full project verification by default.
- Default implementation closure remains: implementation Skill, targeted validation, independent reviewer subAgent running `code-review`.
- Test code writing is handled by this Skill through `test-implementation`; targeted test selection/execution and evidence handling happen after implementation.
- UI-only or architecture-only changes may have no low-cost unit test; provide `no_test_reason` and `suggested_validation` instead of silently skipping validation.
- `ios-verification` is the optional escalation path when the user asks, release confidence is needed, project/dependency configuration changed, or risk/evidence requires it.
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
  "goal": "Implement, modify, wire, design, or refactor iOS code",
  "implementation_mode": "auto | business | swiftui | liquid-glass | uikit | mixed-ui | advanced-swift | refactor | sdk-contract | test-implementation",
  "target_files": [],
  "production_files": [],
  "test_files": [],
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
  "implementation_mode": "business | swiftui | liquid-glass | uikit | mixed-ui | advanced-swift | refactor | sdk-contract | test-implementation",
  "secondary_modes": [],
  "changed_files": [],
  "file_header_check": "not-applicable | passed | blocked",
  "summary": [],
  "test_changes": {
    "added_or_modified_tests": [],
    "test_doubles": [],
    "fixtures": [],
    "testability_seams": []
  },
  "contract_changes": [],
  "ui_structure_changes": [],
  "state_ownership": null,
  "navigation_changes": [],
  "api_boundary_changes": [],
  "concurrency_invariants": [],
  "refactoring_patterns": [],
  "public_api_surface": [],
  "module_boundaries": [],
  "distribution_plan": [],
  "versioning_plan": [],
  "recommended_api_usage": [],
  "fallback_strategy": [],
  "review_findings": [],
  "known_risks": [],
  "test_impact": "...",
  "no_test_reason": null,
  "suggested_validation": [],
  "suggested_next_skill": "ios-verification | code-review | debugging | ios-performance | xcode-build | apple-docs | ui-ux-design-system | blocked",
  "next_action": "run-targeted-tests | code-review | ask-user | blocked"
}
```

Field rules:

- `changed_files`: only files changed by this implementation.
- `file_header_check`: use `passed` when newly added `.swift`, `.h`, `.m`, or `.mm` files have compliant headers; use `not-applicable` when no such files were added; use `blocked` when the project requires headers but the header could not be made compliant.
- `summary`: behavior and implementation outcome, not raw diff.
- `contract_changes`: public API, model, error, persistence, navigation, dependency, side-effect, or availability contract changes.
- `test_impact` or `no_test_reason` must be present.
- `test_changes` may be empty outside `test-implementation`; fill it when adding or modifying tests.
- Mode-specific arrays may be empty when not applicable; do not invent noise.
- `known_risks` should include real residual risk only; use `[]` when none.

## Exit Conditions

Return `completed` when:

- Requested implementation/refactor/SDK contract behavior is implemented or explicitly scoped down.
- Primary mode and any secondary modes are stated.
- Changes are scoped and summarized.
- Newly added `.swift`, `.h`, `.m`, or `.mm` files pass the file header check, or `file_header_check` is explicitly `not-applicable`.
- Contract, UI, concurrency, SDK, Liquid Glass, and refactoring impact fields are filled as applicable.
- Test implementation impact is filled when tests, fixtures, test doubles, or testability seams changed.
- `test_impact` or `no_test_reason` is provided.
- Next validation/review step is clear.

Return `partial` when:

- Useful implementation progress was made but some requested behavior is intentionally deferred.
- Missing assets, product decisions, deployment target facts, API contracts, distribution constraints, or validation access prevent full completion without invalidating completed work.

Return `blocked` when:

- Required project context, dependency source, API contract, product decision, credentials, distribution/platform matrix, or ownership is missing.
- Ownership would require modifying forbidden paths such as vendored `Pods/` snapshots.
- The task is actually build/release/debug/performance/doc-only work and cannot be safely handled as implementation.
- Independent reviewer handoff is required for completion but unavailable after implementation.

## Escalation Rules

Use `test-implementation` within this Skill when tests, mocks, stubs, spies, fakes, fixtures, Page Objects, or testability seams must be written or modified.

Escalate to `ios-verification` when exact `-only-testing` selection is non-trivial.

Escalate to `code-review` after targeted validation or a documented `no_test_reason` when static risk review and verification story review are needed; use an independent reviewer subAgent for implementation-chain closure.

Escalate to `debugging` when the task is driven by runtime crash, hang, leak, watchdog, incorrect object lifetime, or runtime-only symptoms.

Escalate to `ios-performance` when the task becomes frame drops, excessive layout/body invalidation, startup, CPU/memory regression, benchmark, `xctrace`, or Instruments.

Escalate to `xcode-build` when Build Settings, signing, Archive/Export, CI, scheme, xcconfig, packaging mechanics, or concrete XCFramework build steps become the main issue.

Escalate to `apple-docs` when official Apple API facts, availability, WWDC guidance, or sample code is required.

Escalate to `ui-ux-design-system` when the task becomes visual direction, design-system language, branding, color, typography, or product design exploration before implementation.

Escalate to `design-context-compiler` when implementation originates from Figma / Sketch evidence but lacks a validated Canonical UI IR, iOS binding set, or task-scoped Agent Packet. Consume the validated packet when present; do not read full design-tool JSON as implementation context.

Escalate to `ios-automation` when simulator/device UI smoke, screenshot, accessibility tree, installation, launch, or navigation evidence is required.

Escalate to `ios-verification` when targeted validation execution, build/test failure digest, final evidence judgement, release/high-risk evidence, or exact `-only-testing` selection is needed.

## Reporting Format

```text
Implementation status: completed | partial | blocked
Mode: business | swiftui | liquid-glass | uikit | mixed-ui | advanced-swift | refactor | sdk-contract | test-implementation
Changed files:
- ...
Summary:
- ...
File header check: not-applicable | passed | blocked
Contract changes:
- ...
Test changes:
- ...
Mode-specific notes:
- UI/state/navigation/API/concurrency/refactoring/SDK/Liquid Glass notes as applicable
Known risks:
- ...
Test impact: ...
No test reason: none | ...
Suggested validation:
- ...
Next: targeted validation / independent reviewer subAgent(code-review)
```

## Reference Resources

Read only the reference files needed by the selected mode:

- `references/coding-standards.md`: shared Swift/iOS coding standards for implementation and review.
- `references/navigation.md`: business navigation, coordinator, and deep-link organization.
- `references/memory-management.md`: retain-cycle and lifecycle prevention.
- `references/swiftui/components-index.md`: SwiftUI reference router for screens, components, state, previews, navigation, and performance.
- `references/swiftui/liquid-glass.md`: Liquid Glass API usage, fallback, hierarchy, and review checks for `liquid-glass` mode.
- `references/uikit/uikit.md`: UIKit page, layout, list/reuse, lifecycle, and memory guidance.
- `references/swift-advanced/async-concurrency.md`: async/await, actors, structured concurrency, cancellation.
- `references/swift-advanced/protocol-oriented.md`: protocols, PAT, associated types, type erasure, generics.
- `references/swift-advanced/memory-performance.md`: memory/performance tradeoffs in advanced Swift designs.
- `references/swift-advanced/swiftui-patterns.md`: SwiftUI-related advanced Swift patterns.
- `references/swift-advanced/testing-patterns.md`: async and advanced Swift testing patterns.
- `references/refactoring.md`: behavior-preserving refactoring mode guidance.
- `references/sdk-architecture.md`: SDK / Framework module boundaries, public API, testability, distribution, and versioning guidance for `sdk-contract` mode.

## Relationship to Other Skills

- `codex-subagent-orchestration` remains the default iOS main entry and decides when this implementation Skill is needed.
- Test code writing is internal to `test-implementation`.
- Targeted validation, affected-test selection, build/test failure digest, and final evidence judgement route to `ios-verification`.
- Static review routes to independent reviewer subAgent `code-review`.
- Runtime diagnosis routes to `debugging`.
- Performance evidence routes to `ios-performance`.
- Build/release configuration routes to `xcode-build`.
- Device/simulator automation routes to `ios-automation`.
- Apple official facts route to `apple-docs`.
- Visual/product design direction routes to `ui-ux-design-system` before implementation.
- Figma / Sketch Design Evidence, Canonical UI IR, iOS bindings and task-scoped Agent Packet route through `design-context-compiler` before implementation.
- SDK architecture and SwiftUI Liquid Glass are internal modes/references of this Skill, not standalone implementation Skills.
- Optional final evidence routes to `ios-verification` only when required.
