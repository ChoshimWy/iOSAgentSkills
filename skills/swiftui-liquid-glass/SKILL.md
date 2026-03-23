---
name: swiftui-liquid-glass
description: 使用 iOS 26+ 的 Liquid Glass API 构建、审查或改进 SwiftUI 功能。当任务涉及在新界面中采用 Liquid Glass、把现有 SwiftUI 功能重构为 Liquid Glass 风格，或检查其正确性、性能与设计一致性时使用。
---

# SwiftUI Liquid Glass

## 适用场景
- 需要在 iOS 26+ 的 SwiftUI 界面中引入 Liquid Glass。
- 需要审查现有界面的 Liquid Glass 使用是否正确、统一且有回退方案。
- 需要把按钮、卡片、胶囊、工具条等表面改造为玻璃化视觉。

## 核心规则
- 优先使用原生 API：`glassEffect`、`GlassEffectContainer`、`.buttonStyle(.glass)`、`.buttonStyle(.glassProminent)`。
- 多个玻璃元素同时出现时，优先使用 `GlassEffectContainer` 统一管理。
- `.glassEffect(...)` 放在布局和基础视觉修饰之后。
- 仅对真实可交互元素使用 `.interactive()`。
- 同一功能内保持形状、间距、tint 和层级一致。
- 必须使用 `#available(iOS 26, *)` 并提供非玻璃回退。

## 工作流
1. 识别任务类型
- 如果是审查：先检查哪些位置应该用 Liquid Glass，哪些位置不应该用。
- 如果是增强：先确定要玻璃化的表面，再决定是否需要分组容器和交互态。
- 如果是新实现：先设计形状、层级和交互，再落代码。

2. 设计玻璃层级
- 标记目标元素：按钮、卡片、chip、浮层、顶部/底部栏。
- 多个相关元素一起出现时，先考虑 `GlassEffectContainer`。
- 只有在层级切换伴随动画时才引入 `glassEffectID` 和 morphing。

3. 编码与校验
- 修饰符顺序正确，保证玻璃效果不会被后续样式覆盖。
- 可交互元素具备 `.interactive()` 或玻璃按钮样式。
- 低版本使用 `Material` 或常规背景做回退。

## 参考资源
- `references/liquid-glass.md`：Liquid Glass 的基础用法、形状、过渡和最佳实践。
- 涉及最新 API 细节时，优先查询 Apple 官方文档。

## 输出要求
- 审查现有功能时，至少覆盖：
  - 可用性回退是否完整。
  - 容器与 modifier 顺序是否正确。
  - 交互态是否只用于可操作元素。
  - 形状与视觉层级是否统一。
- 新实现或重构时，优先参考以下模式：

```swift
if #available(iOS 26, *) {
    Text("Hello")
        .padding()
        .glassEffect(.regular.interactive(), in: .rect(cornerRadius: 16))
} else {
    Text("Hello")
        .padding()
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
}
```

```swift
GlassEffectContainer(spacing: 24) {
    HStack(spacing: 24) {
        Image(systemName: "scribble.variable")
            .frame(width: 72, height: 72)
            .font(.system(size: 32))
            .glassEffect()
        Image(systemName: "eraser.fill")
            .frame(width: 72, height: 72)
            .font(.system(size: 32))
            .glassEffect()
    }
}
```

```swift
Button("Confirm") { }
    .buttonStyle(.glassProminent)
```

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: swiftui-liquid-glass`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
