# `.codex/xcodebuild.env` 覆盖配置

当自动发现的 workspace、project 或 scheme 不正确时，在仓库根目录创建 `.codex/xcodebuild.env`。

## 支持的变量

```bash
XCODE_WORKSPACE="App/App.xcworkspace"
XCODE_PROJECT="App/App.xcodeproj"
XCODE_SCHEME="App"
XCODE_CONFIGURATION="Debug"
# 可选：仅当你要覆盖默认真机路径时设置，例如：
# XCODE_DESTINATION="generic/platform=iOS Simulator"
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
- 默认优先真机校验；如果未设置 `XCODE_DESTINATION`，脚本会自动选择最优的 `connected` / `available (paired)` 设备
- 只有 simulator destination 会关闭签名，适用于需要显式保留 simulator 构建校验的场景
- 如果显式 simulator 阶段失败且命中第三方依赖的 simulator-only 链接白名单错误，脚本默认会自动切真机重跑一次 `build`
- 真机回退默认开启：`XCODE_DEVICE_FALLBACK=1`；它只在首次 destination 是 simulator 时生效
- 设置 `XCODE_DEVICE_FALLBACK=0` 可关闭自动真机回退，保留“只跑显式配置 destination”的行为
- `XCODE_DEVICE_ID`、`XCODE_DEVICE_NAME`、`XCODE_PREFER_MODEL` 会同时影响默认真机路径和 simulator → 真机回退阶段的设备选择
- 这些覆盖配置只影响 `xcodebuild` 参数，不会跳过 `verify-ios-build` 的前置代码审查

## 示例

### 默认真机优先

```bash
XCODE_WORKSPACE="Acrux/Acrux.xcworkspace"
XCODE_SCHEME="Acrux_DEV"
XCODE_CONFIGURATION="Debug"
XCODE_PREFER_MODEL="iPad"
```

### 显式保留 simulator 首次校验

```bash
XCODE_WORKSPACE="Acrux/Acrux.xcworkspace"
XCODE_SCHEME="Acrux_DEV"
XCODE_CONFIGURATION="Debug"
XCODE_DESTINATION="generic/platform=iOS Simulator"
XCODE_DEVICE_FALLBACK="1"
XCODE_PREFER_MODEL="iPad"
```
