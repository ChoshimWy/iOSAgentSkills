---
name: swiftui-feature-implementation
description: SwiftUI 页面实现统一入口。覆盖模式选型、常规实现和视图重构三种子模式，用于新页面结构、NavigationStack、sheet、状态归属、组件拆分、列表、表单、状态绑定、动画、预览和已有大 View 拆分；不要把 Liquid Glass 专项、性能取证、UIKit 页面、构建配置或 Apple 官方文档检索误判到本 Skill。
---

# SwiftUI Feature 实现

## Purpose

Implement, structure, or refactor SwiftUI screens and components while preserving stable view trees, explicit state ownership, clear navigation, and predictable handoff to testing and code review.

## 中文说明

该 Skill 是 SwiftUI 页面开发统一入口，覆盖三种子模式：

- 模式选型：新页面结构、导航层级、状态归属、组件拆分方案。
- 常规实现：在既定架构下落地 SwiftUI 页面、组件、列表、表单、状态绑定与交互。
- 视图重构：整理已有 SwiftUI 文件，抽离子视图，稳定根视图结构，减少 `body` 复杂度。

不负责：

- Liquid Glass 专项设计。
- UIKit 页面实现。
- 性能 profiling / benchmark。
- 构建配置、签名、Archive、CI。
- Apple 官方 API 事实检索。

## When to Use

Use this Skill when the user asks about:

- SwiftUI 页面结构。
- `NavigationStack`、`TabView`、`sheet`、`popover`。
- `List`、`Grid`、`Form`、自定义组件。
- `@State`、`@Binding`、`@Observable`、`@Bindable`、`@Environment` 状态归属。
- SwiftUI 页面交互、动画、过渡、预览。
- 大型 SwiftUI View 拆分。
- `body` 过长、副作用堆叠、状态错位。
- SwiftUI 与现有 ViewModel / Service / Router 接线。

## When Not to Use

Do not use this Skill when:

- The task is UIKit ViewController / UIView / Auto Layout / collection/table view; use `uikit-feature-implementation`.
- The task is business service, repository, use case, or domain model; use `ios-feature-implementation`.
- The task is Liquid Glass 专项；use `swiftui-liquid-glass`.
- The task is frame drops, redraws, startup, xctrace, or Instruments; use `ios-performance`.
- The task is build/signing/archive/CI; use `xcode-build`.
- The task is runtime crash/leak/hang debugging; use `debugging`.
- The task is Apple API fact lookup; use `apple-docs`.

## Agent Rules

### Submode Rules

Select one submode at the beginning and keep the chain in that submode unless the task clearly changes.

| Submode | Use When |
| --- | --- |
| `mode-selection` | New screen structure, navigation hierarchy, state ownership, or component split is unclear. |
| `implementation` | Page structure and state ownership are known; SwiftUI code needs to be implemented. |
| `view-refactor` | Existing SwiftUI file is too large, `body` is complex, side effects are in views, or state is misplaced. |

### SwiftUI Structure Rules

- Keep root view structure stable.
- Avoid heavy side effects inside `body`.
- Move business logic to service / view model / model layers.
- Keep UI-only state in View when appropriate.
- Keep app/business state in ViewModel or domain layer.
- Prefer explicit dependency injection over hidden global dependencies.
- Use small focused subviews when `body` becomes hard to read.
- Avoid unnecessary `AnyView` unless type erasure is justified.
- Keep identity stable in lists and dynamic collections.

### State Rules

- For iOS 17+ projects, prefer `@Observable`, `@State`, `@Bindable`, and explicit dependencies when consistent with the project.
- Respect existing architecture and minimum deployment target.
- Do not introduce iOS 17-only state mechanisms into projects that need lower deployment support unless guarded or already adopted.
- Use `@MainActor` for UI-facing observable state when needed.
- Keep async state transitions explicit: loading, success, empty, error.

### Navigation Rules

- Keep route identity explicit.
- Prefer a single owner for navigation state.
- Do not scatter sheet/navigation booleans across unrelated subviews.
- For deep links or cross-feature navigation, coordinate with `ios-feature-implementation`.

### Comment / Documentation Rules

- Add `///` documentation for public/open SwiftUI components or reusable types.
- Document concurrency boundary, side effects, and failure state semantics when relevant.
- When editing existing code, review touched declarations and branches for missing or stale comments.
- Add `why` comments for complex UI compatibility or business branches.
- Update comments when behavior changes; remove or fix misleading comments.
- Do not add comments that merely restate SwiftUI syntax.

### File Header Rules

When adding `.swift` files and the project requires headers:

- `Created by` must use local `whoami`.
- Do not write `Codex`.
- Date format: `YYYY/M/D`.

### Validation Handoff Rules

- Do not jump directly to full build verification by default.
- Default chain: `swiftui-feature-implementation -> testing/targeted validation -> reviewer subAgent(code-review)`; the implementation Agent must not self-review.
- UI-only changes may have no low-cost unit test; in that case `testing` must provide `no_test_reason` and `suggested_validation`.
- UI smoke, simulator, or device evidence is optional and only used when requested or risk requires it.
- `final-evidence-gate` / `verify-ios-build` are optional escalation paths.

### Token Budget

- Do not paste huge SwiftUI files when only a section changed.
- Summarize view structure changes instead of dumping full bodies.
- Avoid reading build logs directly; use diagnostics summaries.
- Keep output focused on structure, state, navigation, and validation impact.

## Submode Workflows

### Mode Selection

1. Identify screen type: `TabView`, `NavigationStack`, `sheet`, `List`, `Grid`, `Form`, or custom layout.
2. Decide state ownership: View, ViewModel, shared store, router, environment, or domain layer.
3. Decide navigation and presentation ownership.
4. Decide component split and reusable subviews.
5. Reference component guidance from `references/components-index.md` when useful.

### Implementation

1. Connect existing ViewModel, service, router, or dependency.
2. Bind business state into SwiftUI view state.
3. Implement view hierarchy, interactions, animations, transitions, and previews.
4. Keep business behavior outside `body`.
5. Report test impact and UI validation suggestions.

### View Refactor

1. Preserve behavior first.
2. Stabilize root view structure.
3. Extract subviews by responsibility.
4. Move actions and side effects out of `body`.
5. Keep existing ViewModel unless change is clearly required.
6. Avoid unrelated visual redesign.

## Inputs

Expected input contract:

```json
{
  "goal": "Implement or refactor SwiftUI screen",
  "submode": "mode-selection | implementation | view-refactor | auto",
  "target_files": [],
  "minimum_ios": "optional",
  "existing_architecture": "MV | MVVM | Coordinator | Store | unknown",
  "state_sources": [],
  "navigation_requirements": [],
  "visual_constraints": [],
  "accessibility_requirements": [],
  "constraints": []
}
```

## Outputs

Return compact structured output:

```json
{
  "status": "completed | partial | blocked",
  "submode": "mode-selection | implementation | view-refactor",
  "changed_files": [],
  "summary": [],
  "view_structure_changes": [],
  "state_ownership": "...",
  "navigation_changes": [],
  "contract_changes": [],
  "known_risks": [],
  "test_impact": "...",
  "no_test_reason": null,
  "suggested_next_skill": "testing | code-review | ios-feature-implementation | ios-performance | blocked",
  "next_action": "run-targeted-tests | code-review | ask-user | blocked"
}
```

## Exit Conditions

Return `completed` when:

- Requested SwiftUI screen/component/refactor is complete.
- State ownership and navigation impact are clear.
- Changed files and behavior summary are provided.
- Test impact or `no_test_reason` is provided.
- Next validation/review step is clear.

Return `partial` when:

- Structural progress was made but some UI states, assets, copy, API, or product decisions are missing.

Return `blocked` when:

- Required design, product behavior, deployment target, asset, API contract, or architecture decision is missing.
- The task belongs to UIKit, build, performance, or debugging instead.

## Escalation Rules

Escalate to `ios-feature-implementation` when:

- Business logic, service, repository, use case, router, or deep-link wiring must be changed.

Escalate to `uikit-feature-implementation` when:

- The task becomes UIKit page or UIKit integration work.

Escalate to `swiftui-liquid-glass` when:

- The task is specifically about Liquid Glass visual language.

Escalate to `ios-performance` when:

- The problem is redraw, excessive body invalidation, scrolling performance, startup, or Instruments evidence.

Escalate to `testing` after implementation when:

- Targeted validation or UI test impact must be assessed.

Escalate to `code-review` after testing/validation when:

- Static risk review and verification story review are needed.

Escalate to `ios-automation` when:

- Simulator/device UI smoke, screenshot, accessibility tree, or navigation evidence is required.

Escalate to `xcode-build` when:

- Build settings, signing, Archive/Export, or CI become the main issue.

## Reporting Format

```text
SwiftUI status: completed | partial | blocked
Submode: mode-selection | implementation | view-refactor
Changed files:
- ...
View structure changes:
- ...
State ownership:
- ...
Navigation changes:
- ...
Known risks:
- ...
Test impact: ...
No test reason: none | ...
Next: testing -> reviewer subAgent(code-review)
```

## Reference Resources

- `references/components-index.md`: component index.
- `references/swiftui.md`: SwiftUI general guidance.
- `references/app-wiring.md`: app wiring.
- `references/async-state.md`: async state.
- `references/navigationstack.md`: navigation stack.
- `references/sheets.md`: sheet patterns.
- `references/previews.md`: previews.
- `references/mv-patterns.md`: MV patterns for refactor mode.

## Relationship to Other Skills

- Liquid Glass: `swiftui-liquid-glass`.
- Performance profiling / redraws / dropped frames: `ios-performance`.
- General code smells not specific to SwiftUI: `refactoring`.
- Business layer, service, navigation wiring: `ios-feature-implementation`.
- UIKit page implementation: `uikit-feature-implementation`.
- Visual design system, color, accessibility design guidance: `ui-ux-design-system`.
- After implementation: `testing` then independent reviewer subAgent `code-review`.
- Optional final evidence: `final-evidence-gate` / `verify-ios-build` only when needed.
