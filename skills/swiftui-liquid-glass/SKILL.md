---
name: swiftui-liquid-glass
description: 使用 iOS 26+ 的 Liquid Glass API 构建、审查或改进 SwiftUI 功能。只在问题核心是 `glassEffect`、`GlassEffectContainer`、玻璃按钮样式与兼容性回退时使用；不要把它当作通用 SwiftUI 页面模式、跨技术栈视觉设计、普通页面落地或性能审计技能；若任务产出修改了 Apple Xcode 项目相关内容，默认以定向测试/必要验证与独立 reviewer subAgent `code-review` 放行为收口；`final-evidence-gate` / `verify-ios-build` 仅在用户显式要求或需要补强完整项目环境证据时按需使用。
---

# SwiftUI Liquid Glass

## Purpose

Implement, review, or refine SwiftUI Liquid Glass usage on iOS 26+ with explicit compatibility fallback and clear visual hierarchy guidance.

## 中文说明

该 Skill 只在问题核心是 `glassEffect`、`GlassEffectContainer`、玻璃按钮样式或 iOS 26+ 兼容性回退时使用。

- 负责：Liquid Glass 视觉层级、API 选型、回退策略、用法审查。
- 不负责：普通 SwiftUI 页面模式、跨技术栈视觉设计、通用性能审计。

## When to Use

- 需要在 iOS 26+ 的 SwiftUI 界面中引入 Liquid Glass。
- 需要审查现有界面的 Liquid Glass 使用是否正确、统一且具备回退方案。
- 需要把按钮、卡片、胶囊、工具条等表面改造为玻璃化视觉。

## When Not to Use

- 问题只是普通 SwiftUI 页面结构、导航模式或组件组织；使用 `ios-feature-implementation` 的 `swiftui` 模式。
- 问题核心是品牌气质、色板、排版和设计系统方向；使用 `ui-ux-design-system`。
- 问题核心是运行时性能取证；使用 `ios-performance`。

## Agent Rules

- Confirm Liquid Glass is actually needed before introducing the API surface.
- Prefer `glassEffect`, `GlassEffectContainer`, `.buttonStyle(.glass)`, and `.buttonStyle(.glassProminent)` where semantically appropriate.
- Always provide compatibility fallback for non-iOS 26 paths when relevant.
- Review should cover fallback completeness, modifier ordering, interactive-only usage, and hierarchy consistency.
- When editing Liquid Glass code, document non-obvious availability guards, fallback rationale, visual hierarchy constraints, and interaction side effects in touched code.
- Update stale comments and avoid adding comments that only restate SwiftUI modifier syntax.
- If code changes are produced, final closure follows targeted validation / necessary verification plus independent reviewer subAgent `code-review`; the implementation Agent must not self-review.

## Inputs

```json
{
  "goal": "Implement or review Liquid Glass usage",
  "surface": [],
  "minimum_os": "iOS 26+ | mixed",
  "needs_fallback": true,
  "constraints": []
}
```

## Outputs

```json
{
  "status": "completed | partial | blocked",
  "summary": [],
  "recommended_api_usage": [],
  "fallback_strategy": [],
  "review_findings": [],
  "known_risks": [],
  "next_action": "ios-feature-implementation | code-review | apple-docs | blocked"
}
```

## Exit Conditions

- `completed`: API choice, hierarchy, fallback, and review or implementation guidance are explicit.
- `partial`: useful guidance exists but some compatibility or product-direction input is still missing.
- `blocked`: task is not actually a Liquid Glass problem or no safe fallback path can be defined.

## Escalation Rules

- Escalate to `ios-feature-implementation` with `swiftui` mode for general SwiftUI implementation.
- Escalate to `ui-ux-design-system` for broader visual direction and design language work.
- Escalate to `apple-docs` when official API facts or availability rules must be confirmed.

## Token Budget

- Do not paste large visual design essays.
- Prefer short API recommendations, fallback branches, and review findings.
- Load `references/liquid-glass.md` only when detailed usage guidance is needed.

## Relationship to Other Skills

- Use `ios-feature-implementation` with `swiftui` mode for normal SwiftUI pages and layout work.
- Use `ui-ux-design-system` for broader design-system direction.
- Use `ios-performance` for runtime performance diagnosis.
- Use `apple-docs` for official API fact lookup.
