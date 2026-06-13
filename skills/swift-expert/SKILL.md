---
name: swift-expert
description: Swift 进阶设计 Skill。用于复杂并发隔离、actor / Sendable、取消传播、重入策略、PAT、复杂泛型、类型擦除、跨平台可用性、条件编译和高阶 API 设计；不要用于常规 iOS 业务实现、普通 SwiftUI/UIKit 页面、性能取证或一般重构。
---

# Swift 进阶开发

## Purpose

Design or review advanced Swift language, concurrency, abstraction, and API boundary decisions without introducing unnecessary complexity into normal iOS feature implementation.

## 中文说明

该 Skill 是 Swift 进阶专项 Skill。

负责：
- actor 隔离。
- `Sendable` / `@unchecked Sendable` 判断。
- structured concurrency、取消传播、任务生命周期。
- 重入风险与共享状态设计。
- PAT / associatedtype / opaque type / existential。
- 类型擦除。
- 复杂泛型约束。
- public/open API 设计。
- 跨 iOS / macOS / watchOS / tvOS 可用性策略。
- 条件编译与平台边界。

不负责：
- 常规业务实现。
- 普通 SwiftUI/UIKit 页面落地。
- 性能 profiling / benchmark。
- 构建配置。
- 运行时 crash 排障。

## When to Use

Use this Skill when the task involves:

- Complex Swift concurrency model.
- `actor`, `@MainActor`, global actor, isolation boundary.
- `Sendable`, `nonisolated`, `Task`, cancellation, reentrancy.
- Protocol with associated types.
- Type erasure.
- Opaque return types and existential design.
- Complex generic constraints.
- Cross-platform availability and conditional compilation.
- Public framework API surface and binary/source compatibility.
- High-risk abstraction used across multiple modules.

## When Not to Use

Do not use this Skill when:

- The task is normal service/repository/view model implementation; use `ios-feature-implementation`.
- The task is SwiftUI page layout or view refactor; use `swiftui-feature-implementation`.
- The task is UIKit page implementation; use `uikit-feature-implementation`.
- The task is performance measurement, Instruments, `xctrace`, or benchmark; use `ios-performance`.
- The task is runtime crash/leak/hang; use `debugging`.
- The task is build/signing/CI; use `xcode-build`.
- The proposed abstraction is only for one small local use case and a simple concrete type is enough.

## Agent Rules

### Design Rules

- Prefer simple concrete types unless abstraction is justified.
- Do not introduce protocols, generic layers, or type erasure only for style.
- Make API boundaries explicit and testable.
- Keep concurrency ownership clear.
- Keep failure, cancellation, and side-effect semantics visible.
- Prefer compile-time safety over runtime casting when practical.
- Avoid leaking implementation details through public API.

### Concurrency Rules

- Define the owner of mutable state.
- Define actor/main-thread isolation explicitly.
- Avoid unstructured tasks unless lifecycle is clear.
- Propagate cancellation when parent work is cancelled.
- Avoid data races with shared mutable state.
- Analyze actor reentrancy when state can change across suspension points.
- Use `@unchecked Sendable` only with documented invariants.
- Do not silence Sendable warnings without explaining why it is safe.

### Abstraction Rules

- For PAT or associatedtype designs, define why a simple protocol or generic is insufficient.
- For type erasure, document boxing cost and lost static information.
- For existentials, document dynamic dispatch and type identity implications.
- For opaque return types, keep caller needs and API evolution in mind.
- For public/open APIs, document source compatibility and availability expectations.

### Availability Rules

- State minimum supported platform versions.
- Use `#available` and conditional compilation deliberately.
- Avoid accidentally introducing APIs unavailable on the project deployment target.
- Keep platform-specific code isolated.
- Do not mix availability strategy with product behavior changes without stating it.

### Documentation Rules

- Add `///` documentation for public/open APIs, cross-module reusable types, protocols, and abstractions.
- Documentation must include input, output, failure semantics, concurrency semantics, side effects, and availability when relevant.
- Add `why` comments for non-obvious abstractions or concurrency invariants.
- Do not add comments that merely restate Swift syntax.

### File Header Rules

When adding `.swift`, `.h`, `.m`, `.mm` files and the project requires headers:

- `Created by` must use local `whoami`.
- Do not write `Codex`.
- Date format: `YYYY/M/D`.

### Validation Handoff Rules

- Advanced Swift changes still require targeted validation / necessary verification and `code-review` when code changes are made.
- Prefer focused compile/test validation around the abstraction boundary.
- If no low-cost test exists, testing must provide `no_test_reason` and `suggested_validation`.
- `final-evidence-gate` / `verify-ios-build` are optional escalation paths only when user asks or risk requires it.

### Token Budget

- Do not paste large full files for abstract design review.
- Prefer concise API surfaces, invariants, and tradeoff summaries.
- Do not read full build logs; use diagnostics summaries when needed.
- Avoid long theoretical explanations unless needed to justify a design decision.

## Inputs

Expected input contract:

```json
{
  "goal": "Design advanced Swift abstraction or concurrency boundary",
  "target_files": [],
  "language_topic": "concurrency | generics | type-erasure | availability | public-api | unknown",
  "minimum_platforms": {},
  "public_api": false,
  "constraints": [],
  "existing_architecture": "optional"
}
```

## Outputs

Return compact structured output:

```json
{
  "status": "completed | partial | blocked",
  "language_topic": "concurrency | generics | type-erasure | availability | public-api",
  "changed_files": [],
  "summary": [],
  "api_boundary_changes": [],
  "concurrency_invariants": [],
  "availability_notes": [],
  "tradeoffs": [],
  "known_risks": [],
  "test_impact": "...",
  "no_test_reason": null,
  "suggested_next_skill": "testing | code-review | ios-feature-implementation | ios-performance | blocked",
  "next_action": "run-targeted-tests | code-review | ask-user | blocked"
}
```

## Exit Conditions

Return `completed` when:

- Advanced Swift design or implementation is complete.
- API/concurrency/availability boundaries are explicit.
- Tradeoffs and risks are summarized.
- Test impact or `no_test_reason` is provided.
- Next validation/review step is clear.

Return `partial` when:

- A design direction is established but platform requirements, public API constraints, or integration context are incomplete.

Return `blocked` when:

- Required deployment target, public API requirements, concurrency ownership, dependency context, or product constraints are missing.
- The task does not require advanced Swift and should be handled by another Skill.

## Escalation Rules

Escalate to `ios-feature-implementation` when:

- The advanced design decision is settled and normal business implementation is next.

Escalate to `swiftui-feature-implementation` when:

- The task becomes SwiftUI page/state/view implementation.

Escalate to `uikit-feature-implementation` when:

- The task becomes UIKit page implementation.

Escalate to `testing` after code/design changes when:

- Targeted validation or test coverage must be assessed.

Escalate to `code-review` after testing/validation when:

- Static review of API, abstraction, concurrency, and verification story is needed.

Escalate to `ios-performance` when:

- The task becomes benchmark, memory/performance tradeoff measurement, Instruments, or xctrace.

Escalate to `debugging` when:

- The task is driven by runtime crash/hang/leak symptoms.

Escalate to `apple-docs` when:

- Official Apple API availability or semantic facts are needed.

## Reporting Format

```text
Swift expert status: completed | partial | blocked
Topic: concurrency | generics | type-erasure | availability | public-api
Changed files:
- ...
API boundary changes:
- ...
Concurrency invariants:
- ...
Availability notes:
- ...
Tradeoffs:
- ...
Known risks:
- ...
Test impact: ...
No test reason: none | ...
Next: testing -> code-review
```

## Reference Resources

- `references/async-concurrency.md`
- `references/memory-performance.md`
- `references/protocol-oriented.md`
- `references/swiftui-patterns.md`

## Relationship to Other Skills

- Normal iOS feature implementation: `ios-feature-implementation`.
- SwiftUI page implementation: `swiftui-feature-implementation`.
- UIKit page implementation: `uikit-feature-implementation`.
- Performance baseline, benchmark, xctrace, Instruments: `ios-performance`.
- Runtime crash/leak/hang: `debugging`.
- Official Apple API facts: `apple-docs`.
- Use this Skill only when complexity, abstraction, concurrency isolation, or cross-platform strategy justifies it.
