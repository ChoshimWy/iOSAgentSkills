---
name: ios-feature-implementation
description: 默认 iOS feature 通用业务实现 Skill。用于 service、repository、use case、domain model、view model、coordinator、router、依赖注入、导航接线和常规 async/await 落地；不要把 SwiftUI/UIKit 页面专项实现、构建配置、设备自动化、性能取证或 Apple 官方文档检索误判到本 Skill。
---

# iOS Feature 实现

## Purpose

Implement general iOS feature business logic and application-layer wiring while preserving clear ownership, test handoff, review handoff, and minimal unrelated changes.

## 中文说明

该 Skill 是通用 iOS feature 业务实现入口。

负责：
- service / repository / use case。
- domain model / DTO / mapper。
- view model / state management。
- coordinator / router / navigation wiring。
- dependency injection。
- 常规 async/await 与错误流转。
- 业务层内存安全与并发边界。

不负责：
- SwiftUI 页面结构、布局、`body` 重构。
- UIKit ViewController / UIView 专项页面实现。
- Build Settings、签名、Archive/Export、CI。
- 设备自动化、安装启动、截图。
- 性能 profiling / benchmark。
- Apple 官方 API 事实检索。

## When to Use

Use this Skill when the user asks to implement or modify:

- Service。
- Repository。
- Use case。
- Domain model。
- View model。
- Coordinator / Router。
- Dependency injection。
- Navigation wiring。
- Business error flow。
- State synchronization。
- General async/await business flow。

## When Not to Use

Do not use this Skill as the main Skill when:

- The task is primarily SwiftUI view structure, `NavigationStack`, `TabView`, `sheet`, `body`, layout, or View refactor; use `swiftui-feature-implementation`.
- The task is primarily UIKit page, `UIViewController`, `UIView`, collection/table view, or Auto Layout; use `uikit-feature-implementation`.
- The task is complex Swift language design, protocols, type erasure, actor isolation, or cross-platform availability strategy; use `swift-expert`.
- The task is build configuration, signing, Archive/Export, or CI; use `xcode-build`.
- The task is simulator/device automation; use `ios-automation`.
- The task is performance profiling or benchmark; use `ios-performance`.
- The task is runtime debugging; use `debugging`.
- The task is Apple API / availability / WWDC fact lookup; use `apple-docs`.

## Agent Rules

### Implementation Rules

- Prefer value types where appropriate.
- Use strict access control.
- Use `guard` for early exits.
- Keep business logic in service / model / coordinator / view model, not directly in view or view controller.
- Keep UI updates on the main thread or under `@MainActor`.
- Keep changes minimal and scoped to the requested feature.
- Do not rewrite unrelated code.
- Do not roll back user or other Agent changes.
- Split oversized files, methods, or types instead of stacking complexity.

### Architecture Rules

- Separate domain logic from networking, persistence, and UI.
- Prefer dependency injection over hidden singletons when adding testable behavior.
- Keep side effects explicit.
- Keep error semantics visible and typed where practical.
- Avoid introducing global mutable state.
- For async flows, define cancellation, threading, and lifecycle expectations.

### Private Dependency Rules

- If the project uses CocoaPods and the task involves private components or local integration, inspect `Podfile`, `Podfile.lock`, and `Pods/Manifest.lock`.
- If local `:path` Pod is active, modify the real component repository, not `Pods/<LibraryName>`.
- Treat `Pods/<LibraryName>` as forbidden write scope when it is a vendored snapshot.
- For private library/component implementation, keep or switch the main project to local `:path` dependency for development and validation unless the user explicitly asks otherwise.
- Do not switch validation baseline to online versioned dependency unless explicitly requested.

### Documentation / Comment Rules

- Add `///` documentation for public/open APIs, cross-module reusable types, and reusable protocols.
- Public API documentation should describe input, output, failure semantics, and important side effects.
- For concurrency boundaries, document actor/main-thread/callback queue assumptions.
- For side effects, document state, database, cache, disk, network, or notification impact.
- For failure paths, document throws/error-code/fallback semantics.
- Add `why` comments for complex business branches; do not only restate code.
- File header alone is not enough.

### File Header Rules

When adding `.swift`, `.h`, `.m`, `.mm` files and the project requires headers:

- `Created by` must use local `whoami`.
- Do not write `Codex`.
- Date format: `YYYY/M/D`, for example `Created by $(whoami) on 2026/4/11.`.

### Validation Handoff Rules

- Implementation does not directly jump to full verification by default.
- Default single-Agent chain: `ios-feature-implementation -> testing/targeted validation -> code-review`.
- `testing` should run or suggest the narrowest useful validation.
- If no low-cost test exists, `testing` must provide `no_test_reason` and `suggested_validation`.
- `final-evidence-gate` / `verify-ios-build` are optional escalation paths only when user asks or evidence/risk requires it.

### Token Budget

- Do not paste large diffs.
- Do not paste full files unless necessary.
- Summaries should focus on behavior and contract changes.
- Keep risk and validation impact compact.
- Do not read large build logs; use diagnostics summaries when needed.

## Inputs

Expected input contract:

```json
{
  "goal": "Implement feature behavior",
  "target_files": [],
  "ownership": [],
  "forbidden_paths": ["Pods/"],
  "constraints": [],
  "success_criteria": [],
  "existing_architecture": {
    "pattern": "MVVM | Coordinator | Service | Repository | unknown",
    "dependencies": []
  }
}
```

## Outputs

Return compact structured output:

```json
{
  "status": "completed | partial | blocked",
  "changed_files": [],
  "summary": [],
  "contract_changes": [],
  "known_risks": [],
  "test_impact": "...",
  "no_test_reason": null,
  "suggested_next_skill": "testing | code-review | swiftui-feature-implementation | uikit-feature-implementation | swift-expert | blocked",
  "next_action": "run-targeted-tests | code-review | ask-user | blocked"
}
```

Field rules:

- `changed_files`: only files changed by this implementation.
- `summary`: behavior and contract changes, not raw diff.
- `contract_changes`: public API, model, error, persistence, navigation, or dependency contract changes.
- `known_risks`: real remaining risks only; use `[]` when none.
- `test_impact` or `no_test_reason` must be present.

## Exit Conditions

Return `completed` when:

- Requested business behavior is implemented.
- Changes are scoped and summarized.
- `test_impact` or `no_test_reason` is provided.
- Next validation/review step is clear.

Return `partial` when:

- Useful implementation progress was made but some requested behavior is intentionally deferred.
- Missing context prevents full completion but does not invalidate completed work.

Return `blocked` when:

- Required project context, dependency source, API contract, product decision, or credentials are missing.
- Ownership would require modifying forbidden paths such as vendored `Pods/` snapshots.
- The task actually belongs to another Skill and cannot be safely handled here.

## Escalation Rules

Escalate to `swiftui-feature-implementation` when:

- The task becomes SwiftUI page structure, view layout, navigation presentation, or large SwiftUI view refactor.

Escalate to `uikit-feature-implementation` when:

- The task becomes UIKit ViewController / UIView / Auto Layout / table / collection implementation.

Escalate to `swift-expert` when:

- The task becomes complex Swift type system, actor isolation, Sendable, type erasure, protocol families, or availability design.

Escalate to `testing` after implementation when:

- Code changed and targeted validation or test impact must be assessed.

Escalate to `code-review` after testing/validation when:

- Static risk review and verification story review are needed.

Escalate to `debugging` when:

- The task is driven by runtime crash/hang/leak symptoms.

Escalate to `ios-performance` when:

- The task becomes performance profiling, benchmark, xctrace, Instruments, startup, scrolling, or memory regression.

Escalate to `xcode-build` when:

- Build Settings, signing, Archive/Export, CI, or scheme configuration is the main issue.

Escalate to `apple-docs` when:

- Official Apple API facts, availability, or WWDC references are required.

## Reporting Format

```text
Implementation status: completed | partial | blocked
Changed files:
- ...
Summary:
- ...
Contract changes:
- ...
Known risks:
- ...
Test impact: ...
No test reason: none | ...
Next: testing -> code-review
```

## Reference Resources

- `references/navigation.md`: navigation organization and deep links.
- `references/memory-management.md`: memory management and retain-cycle prevention.

## Relationship to Other Skills

- General iOS business implementation defaults to this Skill.
- SwiftUI page work routes to `swiftui-feature-implementation`.
- UIKit page work routes to `uikit-feature-implementation`.
- Advanced Swift design routes to `swift-expert`.
- After implementation, route to `testing` then `code-review` by default.
- Optional final evidence routes to `final-evidence-gate` / `verify-ios-build` only when required.
- Build configuration routes to `xcode-build`.
- Device automation routes to `ios-automation`.
- Runtime diagnosis routes to `debugging`.
- Performance evidence routes to `ios-performance`.
- Apple official facts route to `apple-docs`.
