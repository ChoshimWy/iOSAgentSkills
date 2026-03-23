# 在 SwiftUI 中实现 Liquid Glass

## 概述
Liquid Glass 是 iOS 26+ 引入的动态材质，结合了玻璃的折射感、内容模糊和实时交互反馈。它适合用于强调层级、突出操作焦点，或让多个相关控件形成统一的玻璃家族。

Liquid Glass 的核心特点：
- 模糊其后的内容并反射周围颜色。
- 可对触摸、鼠标和焦点状态做出响应。
- 能通过 `glassEffectID` 在不同形状之间做 morphing。
- 既可用于单个控件，也可用于多个协同玻璃元素。

## 基础用法

### 给视图添加玻璃效果

```swift
Text("Hello, World!")
    .font(.title)
    .padding()
    .glassEffect()
```

默认会在内容后方应用标准玻璃效果，通常使用 `Capsule` 形状。

### 自定义形状

```swift
Text("Hello, World!")
    .font(.title)
    .padding()
    .glassEffect(in: .rect(cornerRadius: 16.0))
```

常用形状：
- `Capsule`：默认值，适合 chip、badge、胶囊按钮。
- `Rect`：可自定义圆角，适合卡片和工具条。
- `Circle`：适合头像、圆形按钮和浮动操作。

## 玻璃效果配置

### 变体与属性

```swift
Text("Custom Glass")
    .padding()
    .glassEffect(
        .regular
            .tint(.blue.opacity(0.2))
            .interactive()
    )
```

常用配置：
- `.regular`：标准玻璃效果。
- `.clear`：更通透的玻璃效果。
- `.prominent`：更强的视觉强调。
- `.tint(_:)`：给玻璃加入颜色倾向。
- `.interactive()`：让玻璃随交互、聚焦或指针靠近产生反馈。

### 什么时候使用 `interactive()`
- 按钮、chip、标签页等可点击元素。
- 鼠标悬停或焦点状态需要更明显反馈的组件。
- 不要给纯装饰背景加 `interactive()`。

```swift
HStack(spacing: 16) {
    Button {
        // Action
    } label: {
        Image(systemName: "play.fill")
            .frame(width: 44, height: 44)
    }
    .glassEffect(.regular.interactive(), in: .circle)

    Button {
        // Action
    } label: {
        Text("Open")
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
    }
    .buttonStyle(.glassProminent)
}
```

## 多个玻璃效果协同

### 使用 `GlassEffectContainer`
多个相关玻璃元素应放进同一个 `GlassEffectContainer`，让系统统一处理高光、渲染和过渡。

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

### 协同规则
- 把空间上相邻、语义上相关的元素放进同一个容器。
- 保持间距稳定，不要在同组里混入过多随机 tint。
- 尽量让同组元素使用相近形状，如统一圆角矩形或统一胶囊。

## Morphing 与过渡

### 使用 `glassEffectID`

```swift
@Namespace private var glassNamespace
@State private var expanded = false

var body: some View {
    VStack {
        if expanded {
            RoundedRectangle(cornerRadius: 24)
                .fill(.clear)
                .frame(width: 260, height: 180)
                .glassEffect()
                .glassEffectID("card", in: glassNamespace)
        } else {
            Circle()
                .fill(.clear)
                .frame(width: 72, height: 72)
                .glassEffect()
                .glassEffectID("card", in: glassNamespace)
        }
    }
    .onTapGesture {
        withAnimation(.spring(response: 0.45, dampingFraction: 0.82)) {
            expanded.toggle()
        }
    }
}
```

使用规则：
- 同一个概念元素在不同状态间保持稳定的 `glassEffectID`。
- 两个状态必须处在同一次动画事务里。
- 只有在视觉语义确实相近时才做 morphing，避免为炫技而使用。

## 按钮样式

### 普通玻璃按钮

```swift
Button("Confirm") {
    // Action
}
.buttonStyle(.glass)
```

### 强调玻璃按钮

```swift
Button("Continue") {
    // Action
}
.buttonStyle(.glassProminent)
```

## 进阶技巧

### 让背景内容延展到玻璃下方

```swift
ZStack(alignment: .bottom) {
    ScrollView {
        // Content
    }

    footerBar
        .glassEffect()
}
```

适合底部浮层、顶部工具栏或悬浮操作区。关键是让内容自然流入玻璃表面，而不是在玻璃边缘硬切断。

### 侧边栏与横向滚动共存
当 split layout、侧边栏和玻璃 overlay 混用时，允许内容在视觉上延伸到玻璃之下，但要保证命中区域清晰，不要堆叠过多半透明层。

## 最佳实践
- Liquid Glass 适合强调层级和交互，不适合铺满整页背景。
- 同屏玻璃元素数量要克制，避免视觉噪音。
- 先保证结构、形状和层级统一，再考虑 tint 和特殊动画。
- 尽量在真机上验证，Simulator 对透明度、高光和运动感受的还原有限。
- modifier 顺序保持稳定：布局 -> 基础样式 -> `glassEffect`。
- 低版本必须提供合理回退，例如 `.ultraThinMaterial`。

## 示例：自定义状态徽章

```swift
struct StatusBadge: View {
    let title: String
    let symbol: String

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: symbol)
                .font(.system(size: 14, weight: .semibold))
            Text(title)
                .font(.footnote.weight(.semibold))
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .glassEffect(
            .regular
                .tint(.white.opacity(0.18))
                .interactive(),
            in: .capsule
        )
    }
}
```

## 参考
- Apple Developer Documentation
- 最新 SwiftUI / 设计系统相关 WWDC 视频
