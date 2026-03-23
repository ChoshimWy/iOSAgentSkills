# 异步状态与任务生命周期

## 用途
当页面需要加载数据、根据输入变化重启异步任务，或与视图生命周期同步时使用。

## 核心规则
- 首次加载优先用 `.task`。
- 输入变化触发重载时使用 `.task(id:)`。
- 把取消视为正常路径，长流程里检查 `Task.isCancelled`。
- 用户驱动的高频请求先防抖或合并。

## 示例

```swift
.task(id: searchQuery) {
    guard !searchQuery.isEmpty else {
        results = []
        return
    }
    await load(query: searchQuery)
}
```

## 规则
- UI 可见状态留在视图附近。
- 真正耗时工作留给 service，结果再回写 UI 状态。
