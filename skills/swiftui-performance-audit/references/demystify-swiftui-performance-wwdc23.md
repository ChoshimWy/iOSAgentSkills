# Demystify SwiftUI Performance（WWDC23）摘要

背景：WWDC23 这场分享主要帮助建立 SwiftUI 性能的心智模型，并指导如何排查 hitch 与 hang。

## 性能闭环
- `Measure -> Identify -> Optimize -> Re-measure`。
- 先盯具体症状，再决定优化方向，比如慢导航、动画断裂、滚动卡顿。

## 依赖与更新
- SwiftUI 视图形成依赖图，动态属性是最常见的更新源。
- 只在 Debug 场景下使用 `Self._printChanges()` 检查额外依赖。
- 通过拆分视图和缩小状态读取范围来减少无意义更新。
- 在 iOS 17+ 可优先考虑更细粒度的 `@Observable`。

## 常见慢更新原因
- `body` 过重：字符串格式化、过滤、排序、插值。
- 在 `body` 内创建动态属性或初始化重对象。
- 列表和表格的 identity 解析太慢或不稳定。
- 隐性工作太多：bundle 查询、堆分配、重复构造字符串。

## 避免在 `body` 里做慢初始化
- 不要在视图计算阶段同步创建重型 model。
- 异步加载优先用 `.task`，让 `init` 保持轻量。

## 列表与表格的 identity 规则
- 稳定 identity 对性能和动画都至关重要。
- `ForEach` 中每个元素应产生固定数量的子视图。
- 不要在 `ForEach` 里直接过滤集合；先过滤、再缓存。
- 避免在列表行中滥用 `AnyView`，它会隐藏 identity 并增加代价。
- 条件允许时，尽量拍平嵌套 `ForEach`。

## `Table` 特别注意
- `TableRow` 只表示一行，行数应该稳定。
- 优先使用结构更明确的 `Table` 初始化方式来约束行数。

## 调试提示
- 先用代码审查和 Instruments 找出真正的更新热点。
- 不要在没有证据时把所有性能问题都归咎于 SwiftUI 本身。
