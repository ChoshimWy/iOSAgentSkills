---
name: uikit-feature-implementation
description: UIKit 常规页面实现 Skill。用于 ViewController、UIView、Auto Layout、SnapKit、UITableView、UICollectionView、列表复用、事件绑定、页面状态展示与 UIKit 组件装配；不要把通用业务建模、SwiftUI 页面、构建配置、设备自动化、性能取证或 Apple 官方文档检索误判到本 Skill。
---

# UIKit Feature 实现

## Purpose

Implement UIKit screens and components with clear lifecycle organization, layout ownership, event binding, reuse behavior, and handoff to targeted testing and code review.

## 中文说明

该 Skill 是 UIKit 页面与组件实现专项 Skill。

负责：
- `UIViewController`。
- `UIView`。
- Auto Layout / SnapKit 布局。
- `UITableView` / `UICollectionView`。
- cell / supplementary view 复用。
- 页面状态展示。
- 事件绑定与 UI 交互。
- UIKit 页面与现有 ViewModel / Service / Router 接线。

不负责：
- 通用业务建模。
- SwiftUI 页面模式与实现。
- Build Settings、签名、Archive/Export、CI。
- Simulator / 真机自动化。
- 性能 profiling / benchmark。
- Apple 官方 API 事实检索。

## When to Use

Use this Skill when:

- Page responsibility, architecture boundary, and business inputs are already clear.
- The task is primarily `UIViewController`, `UIView`, layout, list, interaction, or UIKit wiring.
- Existing UIKit screen needs maintenance or small refactor.
- Existing ViewModel / service / router already exists and only UIKit binding is needed.
- The task involves table/collection view data source, delegate, cell registration, or reusable views.

## When Not to Use

Do not use this Skill when:

- Service, repository, use case, domain model, coordinator, or router needs to be designed first; use `ios-feature-implementation`.
- The task is SwiftUI page structure, state, or view refactor; use `swiftui-feature-implementation`.
- The task is build/signing/archive/CI; use `xcode-build`.
- The task is simulator/device automation; use `ios-automation`.
- The task is crash/leak/hang diagnosis; use `debugging`.
- The task is performance profiling or scrolling benchmark; use `ios-performance`.
- The task is Apple API fact lookup; use `apple-docs`.

## Agent Rules

### UIKit Structure Rules

- Organize ViewController in this order when consistent with project style:
  1. Properties
  2. UI Components
  3. Lifecycle
  4. Setup
  5. Public
  6. Private
  7. Actions
- Keep business logic in service / model / coordinator / view model, not in ViewController.
- Keep UIKit code focused on rendering, layout, binding, and interaction.
- Prefer project conventions over introducing a new page pattern.
- Do not rewrite unrelated page architecture.

### Layout Rules

- Reuse existing layout tools and conventions.
- If the project uses SnapKit, follow existing SnapKit style.
- Avoid ambiguous constraints.
- Keep constraints grouped by ownership.
- Prefer layout code that is easy to update for iPad, rotation, Dynamic Type, and safe areas.
- Do not hardcode magic layout constants without naming or context when they affect reuse.

### List / Reuse Rules

- Register cells and supplementary views clearly.
- Keep cell configuration idempotent.
- Reset reusable state in `prepareForReuse` when needed.
- Keep diffable data source / traditional data source consistent with existing project style.
- Avoid retaining index paths across async boundaries without validation.
- Avoid heavy work in `cellForRow` / `cellForItem`.

### Lifecycle and Memory Rules

- Use weak captures where closures can outlive the ViewController/View.
- Cancel subscriptions, tasks, timers, notifications, and observers when lifecycle requires it.
- Avoid retain cycles between ViewController, ViewModel, delegates, cells, and callbacks.
- Keep UI updates on the main thread.
- Do not start long-running work in lifecycle methods without cancellation strategy.

### Comment / Documentation Rules

- Add `///` documentation for public/open UIKit components or reusable APIs.
- Document concurrency boundary, side effects, and failure state semantics when relevant.
- Add `why` comments for complex compatibility, layout, or business branches.
- Do not add comments that only restate UIKit syntax.

### File Header Rules

When adding `.swift`, `.h`, `.m`, `.mm` files and the project requires headers:

- `Created by` must use local `whoami`.
- Do not write `Codex`.
- Date format: `YYYY/M/D`.

### Validation Handoff Rules

- Do not jump directly to full project verification by default.
- Default chain: `uikit-feature-implementation -> testing/targeted validation -> code-review`.
- UI-only changes may have no low-cost unit test; `testing` must provide `no_test_reason` and `suggested_validation`.
- Simulator/device UI smoke is optional and only used when user asks or risk requires it.
- `final-evidence-gate` / `verify-ios-build` are optional escalation paths.

### Token Budget

- Do not paste entire large ViewController files when only sections changed.
- Summarize layout/list/lifecycle changes instead of dumping full code.
- Avoid full build logs; use diagnostics summaries when needed.
- Keep output focused on UI behavior, ownership, lifecycle, and validation impact.

## Inputs

Expected input contract:

```json
{
  "goal": "Implement or modify UIKit screen",
  "target_files": [],
  "page_type": "view-controller | view | table | collection | custom-component | unknown",
  "existing_architecture": "MVVM | MVC | Coordinator | VIPER | unknown",
  "layout_system": "Auto Layout | SnapKit | frame | mixed | unknown",
  "business_inputs": [],
  "navigation_requirements": [],
  "accessibility_requirements": [],
  "constraints": []
}
```

## Outputs

Return compact structured output:

```json
{
  "status": "completed | partial | blocked",
  "changed_files": [],
  "summary": [],
  "ui_structure_changes": [],
  "layout_changes": [],
  "event_binding_changes": [],
  "lifecycle_or_memory_notes": [],
  "contract_changes": [],
  "known_risks": [],
  "test_impact": "...",
  "no_test_reason": null,
  "suggested_next_skill": "testing | code-review | ios-feature-implementation | ios-automation | blocked",
  "next_action": "run-targeted-tests | code-review | ask-user | blocked"
}
```

## Exit Conditions

Return `completed` when:

- Requested UIKit screen/component behavior is implemented.
- Layout, event binding, and lifecycle impact are summarized.
- Changed files are listed.
- Test impact or `no_test_reason` is provided.
- Next validation/review step is clear.

Return `partial` when:

- Useful UIKit implementation progress was made but assets, copy, API, design, or product decisions are missing.

Return `blocked` when:

- Page ownership, business input, layout convention, asset, API contract, or navigation decision is missing.
- The task actually belongs to business layer, SwiftUI, build, automation, debugging, or performance Skills.

## Escalation Rules

Escalate to `ios-feature-implementation` when:

- Service, repository, use case, domain model, coordinator, router, or navigation wiring must be designed first.

Escalate to `swiftui-feature-implementation` when:

- The task becomes SwiftUI page implementation or SwiftUI view refactor.

Escalate to `testing` after implementation when:

- Targeted validation or UI test impact must be assessed.

Escalate to `code-review` after testing/validation when:

- Static risk review and verification story review are needed.

Escalate to `ios-automation` when:

- UI smoke, screenshot, accessibility tree, install/launch, or device/simulator evidence is required.

Escalate to `debugging` when:

- The issue is runtime crash, leak, hang, or object lifecycle failure.

Escalate to `ios-performance` when:

- The issue is scrolling performance, dropped frames, excessive layout passes, startup, memory, xctrace, or Instruments.

Escalate to `xcode-build` when:

- Build Settings, signing, Archive/Export, CI, or scheme configuration becomes the main issue.

## Reporting Format

```text
UIKit status: completed | partial | blocked
Changed files:
- ...
UI structure changes:
- ...
Layout changes:
- ...
Event binding changes:
- ...
Lifecycle/memory notes:
- ...
Known risks:
- ...
Test impact: ...
No test reason: none | ...
Next: testing -> code-review
```

## Reference Resources

- `references/uikit.md`

## Relationship to Other Skills

- UIKit page implementation uses this Skill when page boundary and business inputs are clear.
- Business layer and navigation wiring route to `ios-feature-implementation`.
- SwiftUI page work routes to `swiftui-feature-implementation`.
- Build configuration routes to `xcode-build`.
- Device automation routes to `ios-automation`.
- Runtime failures route to `debugging`.
- Performance profiling routes to `ios-performance`.
- After implementation, route to `testing` then `code-review`.
- Optional final evidence routes to `final-evidence-gate` / `verify-ios-build` only when needed.
