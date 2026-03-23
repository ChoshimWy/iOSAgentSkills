# 应用壳体与依赖图

## 用途
用于搭建 `TabView + NavigationStack + sheet` 的根壳体，并把共享依赖统一安装在一个地方。

## 推荐做法
- 根视图负责 tab、per-tab router 和全局 sheet。
- 用单独的 modifier 或装配层注入全局依赖，如认证状态、客户端、主题、`SwiftData` 容器。
- feature 视图只读取自己需要的环境值，局部状态不要上升成全局环境。

## 最小结构

```swift
@MainActor
struct AppView: View {
    @State private var selectedTab: AppTab = .home

    var body: some View {
        TabView(selection: $selectedTab) {
            HomeView()
                .tabItem { Label("Home", systemImage: "house") }
                .tag(AppTab.home)
        }
        .environment(AppClient.live)
        .environment(Theme.live)
    }
}
```

## 规则
- 应用壳体只做装配，不承载业务逻辑。
- 公共服务放环境，功能局部依赖优先走显式注入。
