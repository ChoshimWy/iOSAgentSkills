---
name: ui-ux-design-system
description: UI/UX 设计系统与开放式设计探索 Skill。用于视觉方向、设计系统、交互规则、色板、字体、无障碍、设计评审、原型方向、HTML review 优先的设计交付建议；不要用于 SwiftUI/UIKit API 级落地实现、构建配置、性能取证或外部 Open Design 工具安装流程。
---

# UI/UX Design System

## Purpose

Guide UI/UX direction, design systems, design exploration, accessibility, prototype planning, and design-review decisions before implementation or artifact generation.

## 中文说明

该 Skill 是 UI/UX 设计系统与开放式设计探索专项 Skill。

负责：
- 视觉方向。
- 设计系统。
- 色板、字体、间距、圆角、阴影、图标规则。
- 交互规则。
- 无障碍和可读性建议。
- 原型方向选择。
- HTML review / 设计文档优先的交付建议。
- 设计评审与风险提示。

不负责：
- SwiftUI / UIKit API 级代码实现。
- Liquid Glass API 级实现。
- 构建配置、签名、Archive、CI。
- 性能 profiling / benchmark。
- 外部 Open Design 工具安装和运行维护。

## When to Use

Use this Skill when the user asks for:

- Visual direction.
- Design system.
- Color palette.
- Typography.
- Spacing and layout rhythm.
- Interaction rules.
- Accessibility guidance.
- Design critique or review.
- Prototype planning before implementation.
- Product UI direction for iOS, web, dashboard, landing page, or docs.
- HTML review first, then optional PDF/PPTX/export discussion.

## When Not to Use

Do not use this Skill when:

- The user needs SwiftUI page code, `NavigationStack`, state ownership, or modifiers; use `swiftui-feature-implementation`.
- The user needs UIKit ViewController/View/layout implementation; use `uikit-feature-implementation`.
- The task is Liquid Glass API implementation; use `swiftui-liquid-glass`.
- The task is build/signing/archive/CI; use `xcode-build`.
- The task is device automation or screenshot capture; use `ios-automation`.
- The task is runtime debugging or performance profiling.
- The user only asks for App Store release notes; use `app-store-changelog`.

## Agent Rules

### Design Mode Rules

Choose the smallest design mode that fits the request:

| Mode | Use When |
| --- | --- |
| `design-exploration` | Visual direction, product style, mood, design references, or broad concept. |
| `design-system` | Tokens, components, typography, colors, spacing, accessibility, consistency. |
| `design-review` | Existing UI or mock needs critique and improvement suggestions. |
| `prototype-planning` | User wants a prototype direction before SwiftUI/UIKit implementation. |
| `artifact-guidance` | User wants HTML review, design doc, PDF/PPTX/export direction. |

### Discovery Rules

Before giving a full design direction, capture the smallest useful packet:

- Product type.
- Target users.
- Platform: iOS / iPadOS / macOS / web / mixed.
- Visual keywords: minimal, bold, playful, enterprise, dark, Apple-like, editorial, data-heavy.
- Primary screens or flows.
- Brand constraints.
- Accessibility constraints.
- Output format: discussion, HTML review, PRD, prototype plan, or implementation handoff.

If the user already provided enough context, do not ask again.

### Design System Rules

- Prefer one coherent design system per artifact.
- Avoid mixing multiple unrelated visual languages.
- Define tokens before component details when designing from scratch.
- For iOS, respect HIG-style clarity, depth, hierarchy, and platform conventions.
- For data-heavy apps, define chart, table, empty state, and error state rules.
- For subscription/paywall screens, keep comparison clarity and restore-purchase affordance visible.
- For accessibility, consider contrast, Dynamic Type, hit targets, VoiceOver labels, and motion sensitivity.

### Prototype / Artifact Rules

- Prefer HTML review before final export when design direction is still uncertain.
- Use a prototype plan before generating many screens.
- Keep prototype scope small for first iteration.
- Do not over-specify implementation APIs unless handing off to SwiftUI/UIKit Skills.
- If the output becomes a formal HTML document, hand off to `html-docs`.

### Token Budget

- Do not include huge visual inventories.
- Use concise tables for tokens and component states.
- Prefer design decisions and rationale over long generic design theory.
- For review, list the top blocking UI/UX issues first.

## Inputs

Expected input contract:

```json
{
  "goal": "Design direction | design system | design review | prototype planning",
  "product_type": "optional",
  "platform": "iOS | iPadOS | macOS | web | mixed | unknown",
  "target_users": [],
  "visual_keywords": [],
  "screens_or_flows": [],
  "brand_constraints": [],
  "accessibility_requirements": [],
  "output_format": "discussion | html-review | prototype-plan | implementation-handoff | document"
}
```

## Outputs

Return compact structured output:

```json
{
  "status": "completed | partial | blocked",
  "mode": "design-exploration | design-system | design-review | prototype-planning | artifact-guidance",
  "design_direction": [],
  "tokens": {
    "color": [],
    "typography": [],
    "spacing": [],
    "radius": [],
    "elevation": []
  },
  "component_guidelines": [],
  "interaction_guidelines": [],
  "accessibility_notes": [],
  "prototype_scope": [],
  "implementation_handoff": "swiftui-feature-implementation | uikit-feature-implementation | html-docs | none",
  "known_risks": [],
  "next_action": "prototype | implement | document | review | blocked"
}
```

## Exit Conditions

Return `completed` when:

- Design mode is selected.
- Visual direction or design-system guidance is clear.
- Accessibility and implementation handoff are addressed when relevant.
- Next action is clear.

Return `partial` when:

- A useful direction is provided but brand, audience, assets, or screen list is incomplete.

Return `blocked` when:

- Required product, platform, audience, or output constraints are missing and cannot be reasonably inferred.

## Escalation Rules

Escalate to `swiftui-feature-implementation` when:

- Design direction is ready and SwiftUI implementation is next.

Escalate to `uikit-feature-implementation` when:

- Design direction is ready and UIKit implementation is next.

Escalate to `swiftui-liquid-glass` when:

- The task specifically needs Liquid Glass design and implementation details.

Escalate to `html-docs` when:

- The output should become a formal HTML design spec, PRD, or review document.

Escalate to `ios-automation` when:

- The task needs screenshot capture, accessibility tree evidence, or device/simulator UI smoke.

Escalate to `ios-performance` when:

- The issue is rendering, scrolling, animation performance, or Instruments-based evidence.

## Reporting Format

```text
UI/UX status: completed | partial | blocked
Mode: design-exploration | design-system | design-review | prototype-planning | artifact-guidance
Design direction:
- ...
Tokens:
- color: ...
- typography: ...
- spacing: ...
Component guidelines:
- ...
Interaction guidelines:
- ...
Accessibility notes:
- ...
Implementation handoff: swiftui-feature-implementation | uikit-feature-implementation | html-docs | none
Next action: prototype | implement | document | review | blocked
```

## Reference Resources

- `scripts/search.py`
- `scripts/design_system.py`
- `data/products.csv`
- `data/styles.csv`
- `data/colors.csv`
- `data/typography.csv`
- `data/charts.csv`
- `data/ux-guidelines.csv`
- `data/ui-reasoning.csv`

## Relationship to Other Skills

- Visual direction, design exploration, design review, tokens, typography, color, accessibility: use this Skill.
- SwiftUI implementation: `swiftui-feature-implementation`.
- UIKit implementation: `uikit-feature-implementation`.
- Liquid Glass: `swiftui-liquid-glass`.
- Formal HTML design docs: `html-docs`.
- Screenshots / device UI evidence: `ios-automation`.
- Rendering and animation performance: `ios-performance`.
