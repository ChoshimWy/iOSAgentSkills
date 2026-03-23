# TabView

## 用途
用于多 tab 应用架构、平台化 tab 组合和带副作用的 tab 切换。

## 核心模式
- 用 `AppTab` 枚举统一 tab identity、标题和内容构建。
- `AppView` 拥有选中态，并在需要时拦截 tab 切换。
- 每个 tab 的导航历史独立维护。

## 示例

```swift
enum AppTab: Hashable {
    case home
    case settings
}

TabView(selection: $selectedTab) {
    HomeView()
        .tag(AppTab.home)
    SettingsView()
        .tag(AppTab.settings)
}
```
