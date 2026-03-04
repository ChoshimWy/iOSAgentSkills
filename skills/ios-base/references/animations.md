# 动画参考

> SwiftUI 和 UIKit 动画系统最佳实践

## 目录
- [SwiftUI 动画](#swiftui-动画)
- [UIKit 动画](#uikit-动画)
- [性能优化](#性能优化)
- [设计规范](#设计规范)

---

## SwiftUI 动画

### 动画类型选择

```swift
// 1. Spring (推荐默认)
.animation(.spring(), value: isExpanded)

// 2. 精确控制 - easeInOut
.animation(.easeInOut(duration: 0.3), value: offset)

// 3. 物理仿真 - spring with parameters
.animation(.spring(response: 0.3, dampingFraction: 0.7), value: scale)

// 4. 关键帧动画 (iOS 17+)
.keyframeAnimator(initialValue: 0.0, trigger: animate) { value in
    Circle().offset(y: value)
} keyframes: { _ in
    KeyframeTrack {
        CubicKeyframe(100, duration: 0.3)
        CubicKeyframe(0, duration: 0.3)
    }
}
```

### 隐式 vs 显式动画

```swift
// 隐式动画 - 自动应用到指定值的变化
struct ImplicitExample: View {
    @State private var scale: CGFloat = 1.0
    
    var body: some View {
        Circle()
            .scaleEffect(scale)
            .animation(.spring(), value: scale)  // scale 变化时动画
            .onTapGesture {
                scale = scale == 1.0 ? 1.5 : 1.0
            }
    }
}

// 显式动画 - 包裹状态变化
struct ExplicitExample: View {
    @State private var scale: CGFloat = 1.0
    
    var body: some View {
        Circle()
            .scaleEffect(scale)
            .onTapGesture {
                withAnimation(.spring()) {
                    scale = scale == 1.0 ? 1.5 : 1.0
                }
            }
    }
}
```

### 过渡动画

```swift
// 内置过渡
if showView {
    DetailView()
        .transition(.opacity)  // 淡入淡出
        .transition(.scale)    // 缩放
        .transition(.move(edge: .trailing))  // 移动
}

withAnimation {
    showView.toggle()
}

// 自定义组合过渡
extension AnyTransition {
    static var scaleAndFade: AnyTransition {
        .scale.combined(with: .opacity)
    }
    
    static var cardTransition: AnyTransition {
        .asymmetric(
            insertion: .move(edge: .trailing).combined(with: .opacity),
            removal: .scale.combined(with: .opacity)
        )
    }
}
```

### matchedGeometryEffect (Hero 动画)

```swift
struct HeroTransition: View {
    @State private var isExpanded = false
    @Namespace private var animation
    
    var body: some View {
        VStack {
            if !isExpanded {
                Image("avatar")
                    .matchedGeometryEffect(id: "image", in: animation)
                    .frame(width: 60, height: 60)
                    .onTapGesture {
                        withAnimation(.spring(response: 0.4, dampingFraction: 0.8)) {
                            isExpanded = true
                        }
                    }
            } else {
                VStack {
                    Image("avatar")
                        .matchedGeometryEffect(id: "image", in: animation)
                        .frame(width: 300, height: 300)
                    
                    Button("关闭") {
                        withAnimation(.spring(response: 0.4, dampingFraction: 0.8)) {
                            isExpanded = false
                        }
                    }
                }
            }
        }
    }
}
```

### 手势动画

```swift
struct DraggableCard: View {
    @State private var offset: CGSize = .zero
    @State private var isDragging = false
    
    var body: some View {
        CardView()
            .offset(offset)
            .scaleEffect(isDragging ? 1.05 : 1.0)
            .gesture(
                DragGesture()
                    .onChanged { value in
                        offset = value.translation
                        isDragging = true
                    }
                    .onEnded { value in
                        withAnimation(.spring()) {
                            if abs(offset.width) > 100 {
                                offset = CGSize(width: offset.width > 0 ? 500 : -500, height: 0)
                            } else {
                                offset = .zero
                            }
                            isDragging = false
                        }
                    }
            )
    }
}
```

---

## UIKit 动画

### UIView 动画

```swift
// 基础动画
UIView.animate(withDuration: 0.3) {
    view.alpha = 0.5
    view.transform = CGAffineTransform(scaleX: 1.2, y: 1.2)
}

// Spring 动画
UIView.animate(
    withDuration: 0.5,
    delay: 0,
    usingSpringWithDamping: 0.7,
    initialSpringVelocity: 0.5,
    animations: {
        view.frame.origin.y += 100
    },
    completion: { finished in
        print("Animation completed")
    }
)

// 关键帧动画
UIView.animateKeyframes(
    withDuration: 2.0,
    delay: 0,
    animations: {
        UIView.addKeyframe(withRelativeStartTime: 0.0, relativeDuration: 0.25) {
            view.alpha = 0.5
        }
        UIView.addKeyframe(withRelativeStartTime: 0.25, relativeDuration: 0.25) {
            view.alpha = 1.0
        }
        UIView.addKeyframe(withRelativeStartTime: 0.5, relativeDuration: 0.5) {
            view.transform = CGAffineTransform(rotationAngle: .pi)
        }
    }
)
```

### UIViewPropertyAnimator

```swift
class ViewController: UIViewController {
    private var animator: UIViewPropertyAnimator?
    
    func animateWithControl() {
        animator = UIViewPropertyAnimator(duration: 0.5, curve: .easeInOut) {
            self.boxView.transform = CGAffineTransform(translationX: 200, y: 0)
        }
        
        animator?.addCompletion { position in
            switch position {
            case .end: print("Completed")
            case .current: print("Interrupted")
            case .start: print("Cancelled")
            @unknown default: break
            }
        }
        
        animator?.startAnimation()
    }
    
    // 交互式动画
    @objc private func handlePan(_ gesture: UIPanGestureRecognizer) {
        switch gesture.state {
        case .began:
            animator = UIViewPropertyAnimator(duration: 1.0, curve: .easeOut) {
                self.boxView.transform = CGAffineTransform(translationX: 200, y: 0)
            }
            animator?.pauseAnimation()
            
        case .changed:
            let translation = gesture.translation(in: view)
            animator?.fractionComplete = max(0, min(1, translation.x / 200.0))
            
        case .ended:
            if gesture.velocity(in: view).x > 0 {
                animator?.continueAnimation(withTimingParameters: nil, durationFactor: 0)
            } else {
                animator?.isReversed = true
                animator?.continueAnimation(withTimingParameters: nil, durationFactor: 0)
            }
            
        default: break
        }
    }
}
```

### Core Animation

```swift
// CABasicAnimation
let rotation = CABasicAnimation(keyPath: "transform.rotation.z")
rotation.toValue = CGFloat.pi * 2
rotation.duration = 1.0
rotation.repeatCount = .infinity
layer.add(rotation, forKey: "rotation")

// CAKeyframeAnimation - 路径动画
let pathAnimation = CAKeyframeAnimation(keyPath: "position")
let path = UIBezierPath()
path.move(to: CGPoint(x: 50, y: 50))
path.addCurve(to: CGPoint(x: 250, y: 250),
              controlPoint1: CGPoint(x: 150, y: 50),
              controlPoint2: CGPoint(x: 150, y: 250))
pathAnimation.path = path.cgPath
pathAnimation.duration = 2.0
layer.add(pathAnimation, forKey: "path")

// CAAnimationGroup
let scale = CABasicAnimation(keyPath: "transform.scale")
scale.toValue = 2.0

let opacity = CABasicAnimation(keyPath: "opacity")
opacity.toValue = 0.0

let group = CAAnimationGroup()
group.animations = [scale, opacity]
group.duration = 1.0
layer.add(group, forKey: "group")

// 禁用隐式动画
CATransaction.begin()
CATransaction.setDisableActions(true)
layer.opacity = 0.5
CATransaction.commit()
```

---

## 性能优化

### 高性能属性 (GPU 加速)
```swift
// ✅ 使用这些属性
- opacity
- transform (scale, rotation, translation)
- backgroundColor (layer.backgroundColor)
```

### 避免的属性
```swift
// ❌ 触发布局/重绘
- frame
- bounds
- constraints
```

### Shadow 优化

```swift
// ❌ 慢 - 每帧计算
view.layer.shadowColor = UIColor.black.cgColor
view.layer.shadowOpacity = 0.3
view.layer.shadowRadius = 4

// ✅ 快 - 预定义 shadowPath
view.layer.shadowPath = UIBezierPath(
    roundedRect: view.bounds,
    cornerRadius: 8
).cgPath
view.layer.shadowColor = UIColor.black.cgColor
view.layer.shadowOpacity = 0.3
view.layer.shadowRadius = 4
```

### Transform vs Frame

```swift
// ❌ 错误 - 触发布局
UIView.animate(withDuration: 0.3) {
    view.frame.size.width += 100
}

// ✅ 正确 - 用 transform
UIView.animate(withDuration: 0.3) {
    view.transform = CGAffineTransform(scaleX: 1.5, y: 1.0)
}
```

### SwiftUI 动画作用域

```swift
// ❌ 整个视图重绘
var body: some View {
    VStack {
        Text(viewModel.title)
        CounterView(count: viewModel.count)
    }
}

// ✅ 独立动画作用域
var body: some View {
    VStack {
        Text(viewModel.title)
        CounterView(count: viewModel.count)
            .animation(.default, value: viewModel.count)
    }
}
```

---

## 设计规范

### 时长选择

| 类型 | 时长 | 适用场景 |
|------|------|----------|
| 微交互 | 100-200ms | Toggle、Button、Checkbox |
| 标准过渡 | 200-400ms | 页面切换、Modal、卡片展开 |
| 复杂动画 | 400-800ms | 列表重排、Hero 动画 |

**⚠️ 避免超过 1s 的动画，会让用户感觉慢**

### Easing 选择

```swift
.easeIn       // 渐入 - 适合退出动画
.easeOut      // 渐出 - 适合进入动画（推荐）
.easeInOut    // 两端渐变 - 适合来回移动
.linear       // 匀速 - 适合旋转/进度条
.spring()     // 弹性 - 适合交互反馈（推荐）
```

### 动画分层

```swift
struct LayeredAnimation: View {
    @State private var show = false
    
    var body: some View {
        VStack {
            // 背景先动画
            Color.black.opacity(show ? 0.5 : 0)
                .animation(.easeOut(duration: 0.2), value: show)
            
            // 内容稍后跟随
            if show {
                CardView()
                    .transition(.scale.combined(with: .opacity))
                    .animation(.spring(response: 0.3).delay(0.1), value: show)
            }
        }
    }
}
```

---

## 常用模式

### 骨架屏加载

```swift
struct SkeletonView: View {
    @State private var isAnimating = false
    
    var body: some View {
        RoundedRectangle(cornerRadius: 8)
            .fill(Color.gray.opacity(0.3))
            .frame(height: 60)
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .fill(
                        LinearGradient(
                            colors: [.clear, .white.opacity(0.5), .clear],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .offset(x: isAnimating ? 400 : -400)
            )
            .onAppear {
                withAnimation(.linear(duration: 1.5).repeatForever(autoreverses: false)) {
                    isAnimating = true
                }
            }
    }
}
```

### 下拉刷新

```swift
struct PullToRefresh: View {
    @State private var isRefreshing = false
    
    var body: some View {
        ScrollView {
            VStack {
                if isRefreshing {
                    ProgressView().padding()
                }
                ForEach(items) { item in
                    ItemRow(item: item)
                }
            }
            .offset(y: isRefreshing ? 50 : 0)
        }
        .refreshable {
            await refresh()
        }
    }
}
```

---

## 关键原则

1. **SwiftUI**: 优先 `.spring()`、用 `value:` 精确控制、Hero 动画用 `matchedGeometryEffect`
2. **UIKit**: 基础用 `UIView.animate`、可控用 `UIViewPropertyAnimator`、底层用 Core Animation
3. **性能**: Transform > Frame、预定义 shadowPath、动画作用域最小化
4. **时长**: 微交互 100-200ms、标准过渡 200-400ms、避免超过 1s
5. **工具**: SwiftUI Debug 用 `._printChanges()`
