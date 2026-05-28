# Sheets

## 用途
用于集中管理模态展示，避免多布尔值驱动的碎片化 `sheet` 状态。

## 核心模式
- 本地状态简单时，优先 `sheet(item:)`。
- 应用级或跨多个子视图的模态路由，使用集中 router 和 `SheetDestination` 枚举。
- sheet 内部动作由 sheet 自己处理，关闭使用 `dismiss()`。

## 示例

```swift
@State private var selectedItem: Item?

.sheet(item: $selectedItem) { item in
    EditItemSheet(item: item)
}
```
