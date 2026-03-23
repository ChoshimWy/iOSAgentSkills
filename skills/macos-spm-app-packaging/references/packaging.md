# 打包说明

## 构建产物路径
SwiftPM 的二进制通常位于以下位置：
- `.build/<arch>-apple-macosx/<config>/<AppName>`：按架构输出的产物。
- `.build/<config>/<AppName>`：部分产品（如 framework / tool）会出现在这里。

需要通用二进制时，可结合 `ARCHES="arm64 x86_64"` 运行 `swift build`。

## 模板常用环境变量
- `APP_NAME`：应用或可执行文件名，例如 `MyApp`。
- `BUNDLE_ID`：Bundle Identifier，例如 `com.example.myapp`。
- `ARCHES`：空格分隔的目标架构，默认使用宿主架构。
- `SIGNING_MODE`：开发环境可用 `adhoc`，减少 keychain 弹窗。
- `APP_IDENTITY`：发布构建所用的代码签名身份。
- `MACOS_MIN_VERSION`：写入 `Info.plist` 的最低 macOS 版本。
- `MENU_BAR_APP`：设为 `1` 时，为 `Info.plist` 注入 `LSUIElement`。
