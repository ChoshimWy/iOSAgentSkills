---
name: ui-ux-design-system
description: 辅助型跨技术栈 UI/UX 设计与设计系统技能。只用于视觉方向、设计系统、交互规则、色板、字体与实现前的 UI/UX 决策；如果用户要的是 SwiftUI / UIKit API 级落地实现、已有 SwiftUI 大 view 重构或 Liquid Glass API 级实现，不要使用本 skill 作为主 skill。
---

# UI/UX Design System

## 角色定位
- 辅助型 skill。
- 负责视觉方向、设计系统、交互规则和跨技术栈 UI/UX 检索。
- 不直接承担 SwiftUI 页面落地，也不处理 Liquid Glass API 专项实现。

## 触发判定（硬边界）
- 用户主要在问视觉风格、设计 token、色板、字体、交互规则、无障碍和设计系统方向时，使用本 skill。
- 如果用户需要的是 SwiftUI / UIKit 代码、页面结构、状态归属或具体 modifier / layout 写法，不要用本 skill 作为主 skill。
- 如果问题核心已经收缩到 Liquid Glass API 的具体实现细节，切换到 `swiftui-liquid-glass`。

## 适用场景
- 设计新页面、组件或完整设计系统。
- 评审现有 UI/UX 代码，定位布局、可访问性、交互和视觉问题。
- 为特定产品类型、行业或技术栈生成设计方向、色彩、字体和实现前建议。

## 核心工作流
1. 提炼产品类型、行业、风格关键词、技术栈和页面目标。
2. 优先运行 `skills/ui-ux-design-system/scripts/search.py ... --design-system` 生成设计系统。
3. 按需补充 `style`、`color`、`typography`、`landing`、`chart`、`ux` 等 domain 检索。
4. 用户未指定技术栈时默认使用 `html-tailwind`。

## 参考资源
- `scripts/search.py`
- `scripts/design_system.py`
- `data/products.csv`
- `data/styles.csv`
- `data/colors.csv`
- `data/typography.csv`
- `data/charts.csv`
- `data/ux-guidelines.csv`
- `data/ui-reasoning.csv`

## 与其他技能的关系
- 当任务重点是视觉风格、设计系统、色板、字体、无障碍或跨技术栈 UI/UX 方向时，优先使用本技能。
- 如果目标已经明确为 SwiftUI 页面落地、状态与路由模式设计，主 skill 切换到 `swiftui-ui-patterns` 或 `swiftui-feature-implementation`。
- 如果是 iOS 26+ 的 Liquid Glass 专项设计与实现，切换到 `swiftui-liquid-glass`。
- 如果是已有 SwiftUI 视图文件重构或性能审计，不使用本技能作为主技能。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定当前任务已经加载并正在使用本 Skill 时：

- 在回复末尾追加一行：`// skill-used: ui-ux-design-system`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
