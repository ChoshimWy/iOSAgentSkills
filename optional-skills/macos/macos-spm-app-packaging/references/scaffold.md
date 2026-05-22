# SwiftPM macOS 应用脚手架（无 Xcode 工程）

## 步骤
1. 创建仓库并初始化 SwiftPM：

```bash
mkdir MyApp
cd MyApp
swift package init --type executable
```

2. 修改 `Package.swift`，把目标平台设为 macOS，并定义应用的 executable target。

3. 在 `Sources/MyApp/` 下创建应用入口：
- 想要窗口应用且尽量少写 AppKit glue 时，使用 SwiftUI。
- 想要菜单栏或 accessory 形态时，使用 AppKit。

4. 如果需要资源文件，在 target 中加入：

```swift
resources: [.process("Resources")]
```

并创建 `Sources/MyApp/Resources/`。

5. 添加 `version.env` 供打包脚本读取：

```bash
MARKETING_VERSION=0.1.0
BUILD_NUMBER=1
```

6. 从 `assets/templates/` 复制打包脚本到项目，例如 `Scripts/`。

## 最小 `Package.swift` 示例

```swift
// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "MyApp",
    platforms: [.macOS(.v14)],
    targets: [
        .executableTarget(
            name: "MyApp",
            path: "Sources/MyApp",
            resources: [
                .process("Resources")
            ]
        )
    ]
)
```

## 最小 SwiftUI 入口示例

```swift
import SwiftUI

@main
struct MyApp: App {
    var body: some Scene {
        WindowGroup {
            Text("Hello")
        }
    }
}
```

## 最小 AppKit 入口示例

```swift
import AppKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        // 在这里初始化应用状态。
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
```
