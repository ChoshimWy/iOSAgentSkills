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
XCODE_DEVICE_FALLBACK="1"
XCODE_DEVICE_ID="00008110-001234567890001E"
XCODE_DEVICE_NAME="Choshim's iPhone"
XCODE_PREFER_MODEL="iPad"
```

## 规则

- `XCODE_WORKSPACE` 与 `XCODE_PROJECT` 二选一即可
- 如果两个都配置，脚本优先使用 `XCODE_WORKSPACE`
- `XCODE_SCHEME` 建议显式配置，避免多 scheme 仓库误判
- 默认不做 `clean build`
- simulator 阶段默认关闭签名，适用于大多数本地或 CI 编译校验场景
- 如果 simulator 阶段失败且命中第三方依赖的 simulator-only 链接白名单错误，脚本默认会自动切真机重跑一次 `build`
- 真机回退默认开启：`XCODE_DEVICE_FALLBACK=1`
- 设置 `XCODE_DEVICE_FALLBACK=0` 可关闭自动真机回退，保留旧的“只跑 simulator”行为
- `XCODE_DEVICE_ID`、`XCODE_DEVICE_NAME`、`XCODE_PREFER_MODEL` 只影响真机回退阶段的设备选择
- 这些覆盖配置只影响 `xcodebuild` 参数，不会跳过 `verify-ios-build` 的前置代码审查

## 示例

```bash
XCODE_WORKSPACE="Acrux/Acrux.xcworkspace"
XCODE_SCHEME="Acrux_DEV"
XCODE_CONFIGURATION="Debug"
XCODE_DESTINATION="generic/platform=iOS Simulator"
XCODE_DEVICE_FALLBACK="1"
XCODE_PREFER_MODEL="iPad"
```
