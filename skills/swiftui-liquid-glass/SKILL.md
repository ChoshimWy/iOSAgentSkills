---
name: swiftui-liquid-glass
description: 使用 iOS 26+ 的 Liquid Glass API 构建、审查或改进 SwiftUI 功能。只在需要采用 `glassEffect`、`GlassEffectContainer` 或玻璃按钮样式时使用；不要把它当作通用 SwiftUI 页面模式、跨技术栈视觉设计或普通性能审计技能。
---

# SwiftUI Liquid Glass

## 角色定位
- 专项型 skill。
- 负责 iOS 26+ `Liquid Glass` 视觉体系的实现、审查和回退策略。
- 不负责一般 SwiftUI 页面模式选型，也不替代跨技术栈 UI/UX 设计或通用性能审计。

## 适用场景
- 需要在 iOS 26+ 的 SwiftUI 界面中引入 Liquid Glass。
- 需要审查现有界面的 Liquid Glass 使用是否正确、统一且具备回退方案。
- 需要把按钮、卡片、胶囊、工具条等表面改造为玻璃化视觉。

## 核心工作流
1. 先确认 Liquid Glass 是否真的需要
- 只有在任务明确要求玻璃化视觉或已经采用 Liquid Glass 时再触发本 skill。
- 新页面的普通结构和模式选型仍优先交给 `swiftui-ui-patterns`。

2. 设计玻璃层级
- 优先使用原生 API：`glassEffect`、`GlassEffectContainer`、`.buttonStyle(.glass)`、`.buttonStyle(.glassProminent)`。
- 多个玻璃元素同时出现时，优先使用 `GlassEffectContainer` 统一管理。
- `.glassEffect(...)` 放在布局和基础视觉修饰之后。
- 仅对真实可交互元素使用 `.interactive()`。

3. 做兼容性和一致性校验
- 必须使用 `#available(iOS 26, *)` 并提供非玻璃回退。
- 同一功能内保持形状、间距、`tint` 和层级一致。
- 如需最新 API 细节，优先查询 Apple 官方文档。

## 参考资源
- `references/liquid-glass.md`：Liquid Glass 的基础用法、形状、过渡和最佳实践。

## 输出要求
- 审查现有功能时，至少覆盖：
  - 可用性回退是否完整。
  - 容器与 modifier 顺序是否正确。
  - 交互态是否只用于可操作元素。
  - 形状与视觉层级是否统一。
- 新实现或重构时，优先给出可直接落地的 `SwiftUI` 写法和兼容性分支。

## 与其他技能的关系
- 新建普通 SwiftUI 页面、`TabView` 架构或布局模式，切换到 `swiftui-ui-patterns`。
- 需要先做跨技术栈视觉方向、配色、排版和设计系统方案时，切换到 `ui-ux-pro-max`。
- 需要运行时性能诊断或 `xctrace` 取证时，切换到 `ios-performance`。
- 需要官方 API 事实依据时，可辅以 `apple-docs`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: swiftui-liquid-glass`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
