---
name: ui-ux-pro-max
description: "辅助型跨技术栈 UI/UX 设计与设计系统生成技能，覆盖 50+ 风格、21+ 色板、50+ 字体搭配、20+ 图表类型与 9 种技术栈；用于设计方向、视觉系统、交互规则与实现前的 UI/UX 决策，不负责 SwiftUI 落地实现细节。"
---

# UI/UX Pro Max

## 角色定位
- 辅助型 skill。
- 负责视觉方向、设计系统、交互规则和跨技术栈 UI/UX 检索。
- 不直接承担 SwiftUI 页面落地，也不处理 Liquid Glass 专项实现。

## 适用场景
- 设计新页面、组件或完整设计系统。
- 评审现有 UI/UX 代码，定位布局、可访问性、交互和视觉问题。
- 为特定产品类型、行业或技术栈生成设计方向、色彩、字体和实现前建议。

## 核心工作流
1. 提炼产品类型、行业、风格关键词、技术栈和页面目标。
2. 优先运行 `skills/ui-ux-pro-max/scripts/search.py ... --design-system` 生成设计系统。
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
- 如果目标已经明确为 SwiftUI 页面落地、状态与路由模式设计，切换到 `swiftui-ui-patterns`。
- 如果是 iOS 26+ 的 Liquid Glass 专项设计与实现，切换到 `swiftui-liquid-glass`。
- 如果是已有 SwiftUI 视图文件重构或性能审计，不使用本技能作为主技能。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: ui-ux-pro-max`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
