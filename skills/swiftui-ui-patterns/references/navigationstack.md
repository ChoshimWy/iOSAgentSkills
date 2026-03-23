# NavigationStack

## 用途
用于程序化导航、深链和多 tab 独立历史。

## 核心模式
- 用 `Route` 枚举表示可导航目的地。
- 每个 tab 拥有独立 path。
- 根视图统一安装 router，并集中声明 `navigationDestination`。

## 示例

```swift
@MainActor
@Observable
final class RouterPath {
    var path: [Route] = []
}

enum Route: Hashable {
    case detail(id: String)
}

NavigationStack(path: $router.path) {
    RootView()
        .navigationDestination(for: Route.self) { route in
            switch route {
            case .detail(let id):
                DetailView(id: id)
            }
        }
}
```

## 规则
- 路由类型必须稳定、可比较。
- 不要在叶子视图里到处创建各自为政的导航状态。
