# ScrollView 与 Lazy 栈

## 用途
用于自定义滚动布局、横向列表、聊天视图和非标准卡片流。

## 核心规则
- 自定义布局优先 `ScrollView + LazyVStack` / `LazyHStack` / `LazyVGrid`。
- 需要跳转、回顶或定位时用 `ScrollViewReader`。
- 底部输入条用 `safeAreaInset(edge: .bottom)`，不要手写悬浮定位。

## 示例

```swift
ScrollView {
    LazyVStack {
        ForEach(items) { item in
            Row(item: item)
        }
    }
}
```
