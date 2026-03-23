# macOS Settings

## 用途
用于构建基于 SwiftUI `Settings` scene 的 macOS 设置窗口。

## 核心规则
- 在 `App` 中声明 `Settings` scene。
- 设置页使用专门根视图，例如 `SettingsView`。
- 简单偏好项优先用 `@AppStorage`。
- 多分类设置可用 `TabView` 组织。
