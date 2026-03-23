# 加载占位与空态

## 用途
用于在加载过程中保持布局稳定，并在无数据或错误时展示清晰空态。

## 核心规则
- 优先使用 `.redacted(reason: .placeholder)` 保持真实布局。
- 加载结束但无数据时，优先使用 `ContentUnavailableView`。
- 不要在一个区域里叠多个 spinner。

## 示例

```swift
if isLoading {
    RowView(model: .placeholder())
        .redacted(reason: .placeholder)
} else if items.isEmpty {
    ContentUnavailableView("No items", systemImage: "tray")
}
```
