# `.codex/xcodebuild.env` 覆盖配置

当自动发现的 workspace、project 或 scheme 不正确时，在仓库根目录创建 `.codex/xcodebuild.env`。

## 支持的变量

```bash
XCODE_WORKSPACE="App/App.xcworkspace"
XCODE_PROJECT="App/App.xcodeproj"
XCODE_SCHEME="App"
XCODE_CONFIGURATION="Debug"
XCODE_DESTINATION="generic/platform=iOS Simulator"
XCODE_ACTION="build"
XCODE_DERIVED_DATA="$PWD/.codex-derived-data"
```

## 规则

- `XCODE_WORKSPACE` 与 `XCODE_PROJECT` 二选一即可
- 如果两个都配置，脚本优先使用 `XCODE_WORKSPACE`
- `XCODE_SCHEME` 建议显式配置，避免多 scheme 仓库误判
- 默认不做 `clean build`
- 默认关闭签名，适用于大多数本地或 CI 编译校验场景
- 这些覆盖配置只影响 `xcodebuild` 参数，不会跳过 `verify-ios-build` 的前置代码审查

## 示例

```bash
XCODE_WORKSPACE="Acrux/Acrux.xcworkspace"
XCODE_SCHEME="SidusLinkPro"
XCODE_CONFIGURATION="Debug"
XCODE_DESTINATION="generic/platform=iOS Simulator"
```
