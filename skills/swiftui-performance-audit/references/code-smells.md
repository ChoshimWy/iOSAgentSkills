# 常见代码异味与修复模式

## 用途
在代码优先审计阶段，用这份清单把可见的 SwiftUI 写法映射到潜在运行时代价，并给出更安全的修复方向。

## 高优先级异味

### 在 `body` 中创建昂贵 formatter

```swift
var body: some View {
    let number = NumberFormatter()
    let measure = MeasurementFormatter()
    Text(measure.string(from: .init(value: meters, unit: .meters)))
}
```

优先把 formatter 缓存在 model、service 或专门 helper 中：

```swift
final class DistanceFormatter {
    static let shared = DistanceFormatter()
    let number = NumberFormatter()
    let measure = MeasurementFormatter()
}
```

### 过重的计算属性

```swift
var filtered: [Item] {
    items.filter { $0.isEnabled }
}
```

如果这个派生值计算不便宜，应改为在输入变化时统一预计算，而不是每次渲染时重算。

### 在 `body` 中排序或过滤
- 不要在 `List`、`ForEach` 或大视图层级中反复执行 `sorted()`、`filter()`、`map()`。
- 把派生集合移到 model/helper，或在有限输入变化时更新。

### 在 `ForEach` 里内联过滤
- `ForEach(items.filter { ... })` 容易同时引入重算和 identity 问题。
- 先得到稳定、已过滤的集合，再交给 `ForEach`。

### 不稳定的 identity
- 避免用 `offset`、临时 `UUID()` 或不稳定字段作为 `id`。
- 列表、网格和动画都依赖稳定 identity。

### 顶层条件分支切换整棵视图树
- `if/else` 返回完全不同的根视图会造成 identity churn 和过度失效。
- 优先保留稳定根视图，把条件收敛到局部 section 或 modifier。

### 主线程图片解码
- 大图解码、缩放或格式转换应提前做下采样或后台处理。
- 不要把图像代价留在滚动过程或首帧渲染里。

## Observation 扇出

### iOS 17+ 的广泛 `@Observable` 读取
- 一个大对象被很多视图直接读取，会导致每次局部变更都触发更广泛重绘。
- 优先拆小可观察对象，或缩小每个视图的读取范围。

### iOS 16 及更早的 `ObservableObject` 广泛读取
- 把过多状态挂在单个 `ObservableObject` 上会导致整个订阅树频繁刷新。
- 尽量局部化观察链，避免“全局大对象 + 到处注入”。

## 修复说明

### `@State` 不是通用缓存
- 只用 `@State` 保存真正归属视图生命周期的状态。
- 不要把 `@State` 当任意计算缓存容器。

### `equatable()` 不是默认答案
- 只有在“比较成本明显低于重算成本”且输入确实值语义稳定时才使用。
- 先修 identity、观察范围和重计算，再考虑 `equatable()`。

## 审计优先级
1. 先查大范围观察与不稳定 identity。
2. 再查 `body` 内重计算、图片解码和布局链复杂度。
3. 最后再看动画代价、细粒度 modifier 顺序与局部优化。
