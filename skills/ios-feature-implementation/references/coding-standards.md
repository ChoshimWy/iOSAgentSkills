# iOS Coding Standards Reference

This reference is the shared coding-standard source for implementation and review. Load it when a task touches public API, comments, concurrency, UI ownership, reusable components, or style-sensitive refactors. For tiny local fixes, follow the summary in `SKILL.md` without loading this file.

## Priority

Use this priority order when rules conflict:

```text
correctness > safety > concurrency / memory > project consistency > readability > style preference
```

Prefer existing project conventions over introducing a new style unless the existing style is unsafe or unclear.

## Swift Style

- Use the narrowest practical access control: `private`, `fileprivate`, `internal`, `public`, `open`.
- Prefer value types for simple immutable data and final classes for identity/lifecycle owners.
- Mark classes `final` unless inheritance is required.
- Prefer explicit dependency injection over hidden global mutable state for new behavior.
- Use `guard` for early exits when it clarifies failure paths.
- Keep methods focused; extract helpers when branching, mapping, or side effects obscure intent.
- Avoid broad renames, formatting-only churn, and directory moves unless they are the actual task.

## Public API and Documentation

Add `///` documentation for:

- `public` / `open` declarations.
- Cross-module reusable types, protocols, and configuration objects.
- SDK-facing models, entry points, delegates, and callbacks.
- Non-obvious concurrency or lifecycle boundaries.

Public documentation should state:

- Inputs and outputs.
- Throws / error codes / fallback behavior.
- Side effects: database, cache, disk, network, device state, notifications, or navigation.
- Actor, main-thread, callback queue, and cancellation assumptions.
- Availability or platform restrictions when relevant.

Do not add comments that only restate syntax. Add `why` comments for compatibility branches, degraded fallbacks, concurrency invariants, and business rules that are not obvious from code.

## Concurrency and Lifecycle

- Keep UI-facing observable state on the main actor or otherwise make actor/thread ownership explicit.
- Avoid unstructured `Task` unless lifecycle, cancellation, and ownership are clear.
- Propagate cancellation for child async work where the parent operation can cancel.
- Avoid sharing mutable state across actors/threads without a clear owner.
- Use `@unchecked Sendable` only with documented invariants.
- Avoid retaining view controllers, views, cells, delegates, tasks, timers, observers, or subscriptions longer than their lifecycle.

## Error and State Semantics

- Model loading/success/empty/error states explicitly for UI-facing async flows.
- Keep fallback behavior visible; silent fallback must have a reason and a validation story.
- Preserve existing user data unless the task explicitly changes persistence semantics.
- When behavior changes affect persisted data, networking, cache, or navigation, report it as `contract_changes`.

## SwiftUI Boundaries

- Keep heavy work and business side effects out of `body`.
- Make state ownership explicit: View, ViewModel, router/store, environment, or domain layer.
- Respect the project's minimum deployment target before adopting newer state APIs.
- Prefer focused subviews over oversized `body` implementations.
- Keep `List` / `ForEach` identity stable.
- Avoid unnecessary `AnyView`; justify type erasure when used.

## UIKit Boundaries

- Keep `UIViewController` / `UIView` focused on rendering, layout, binding, interaction, and lifecycle.
- Keep business rules in service, model, coordinator, or view model layers.
- Follow the existing layout system; use SnapKit only when the project already does or the task asks for it.
- Keep cell configuration idempotent and reset reusable state in `prepareForReuse` when needed.
- Avoid retaining index paths or cells across async boundaries without validation.
- Cancel tasks/subscriptions/timers/observers at the lifecycle owner that created them.

## Private Dependencies and Generated Code

- If CocoaPods/private components are involved, inspect `Podfile`, `Podfile.lock`, and `Pods/Manifest.lock` first.
- If a dependency is a local `:path` Pod, modify the real component repository, not `Pods/<LibraryName>`.
- Treat vendored `Pods/` snapshots, generated files, and build artifacts as forbidden ownership unless the user explicitly scopes them in.
- Do not commit local `:path` dependency references unless explicitly requested.

## File Headers

When adding `.swift`, `.h`, `.m`, or `.mm` files and the target project uses headers:

- `Created by` must use the local `whoami` value.
- Do not write `Codex`.
- Use date format `YYYY/M/D`.

## Review Classification

Blocking findings include:

- Correctness regression, data loss, or broken user-visible behavior.
- Unsafe concurrency, missing actor/main-thread boundary, or unsound `Sendable` handling.
- Retain cycle or lifecycle leak with credible ownership evidence.
- Public/open API missing required semantics documentation.
- Missing failure/side-effect/cancellation documentation where callers depend on it.
- Changes in vendored `Pods/` snapshots when the real source repo should be edited.

Non-blocking findings include:

- Naming or wording improvements.
- Local readability/style suggestions that do not affect safety or contracts.
- Optional extraction or cleanup that can be deferred.
