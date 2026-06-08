# `.codex/xcodebuild.env` 覆盖配置

当自动发现的 workspace、project、scheme 或 destination 不正确时，在仓库根目录创建配置文件（Codex 使用 `.codex/xcodebuild.env`；CC 用户可直接在项目根目录设置环境变量）。

如果同机同仓会有多个 Codex / Claude CLI 并发处理同一 Xcode 项目，本机安装脚本会先同步全局 wrapper 到 `~/.codex/bin/codex_verify`。若目标项目再把 `config/codex/templates/codex_verify.example.sh` 复制到项目根目录并重命名为 `codex_verify.sh`，则项目脚本优先；否则 `verify-ios-build` 自动回退到全局 wrapper。

## 支持的变量

```bash
XCODE_WORKSPACE="App/App.xcworkspace"
XCODE_PROJECT="App/App.xcodeproj"
XCODE_SCHEME="App"
XCODE_CONFIGURATION="Debug"
# 可选：显式覆盖首次校验 destination，例如：
# XCODE_DESTINATION="generic/platform=iOS Simulator"
# 或者直接指定真机 destination id：
# XCODE_DESTINATION="id=00008110-001234567890001E"
XCODE_ACTION="build"
XCODE_DEVICE_FALLBACK="1"
# XCODE_DEVICE_ID 是 xcodebuild destination id，不是 devicectl device identifier
XCODE_DEVICE_ID="00008110-001234567890001E"
XCODE_DEVICE_NAME="Choshim's iPhone"
XCODE_PREFER_MODEL="iPad"
# UI smoke（可选）
XCODE_UI_SMOKE_MODE="auto"
XCODE_UI_SMOKE_SPEC=".codex/ui-smoke.yml"
```

## 规则

- `XCODE_WORKSPACE` 与 `XCODE_PROJECT` 二选一即可
- 如果两个都配置，脚本优先使用 `XCODE_WORKSPACE`
- `XCODE_SCHEME` 建议显式配置，避免多 scheme 仓库误判
- 如果未显式设置 `XCODE_SCHEME`，脚本默认优先选择绑定了单元测试 `*Tests` target / bundle 的 scheme；若不存在，再回退到其它测试 scheme（例如 `*UITests`、`*_TEST`）
- 如果当前任务里已经先跑过定向测试，最终门禁应优先复用同一套 workspace / scheme / destination 基线；必要时用 `XCODE_SCHEME` / `XCODE_DESTINATION` 显式固定
- 本地 `verify-ios-build` 不支持 `XCODE_DERIVED_DATA` 覆盖；统一使用 Xcode 默认 DerivedData（`~/Library/Developer/Xcode/DerivedData`）
- 默认不做 `clean build`
- 最终门禁仍必须在目标项目根目录的项目环境执行；`.codex/xcodebuild.env` 只负责补充参数，不会把最终验证降级成沙箱构建
- `codex_verify.sh` / `~/.codex/bin/codex_verify` 只负责串行化验证入口，不负责覆盖 `xcodebuild` 参数；workspace / scheme / destination 仍由本文件与脚本默认策略决定
- 本地执行 `xcodebuild`（含 `-list` / `-showdestinations` / build/test）默认在项目环境直接执行（CC 使用 `Bash` 工具；Codex 使用 `functions.exec_command` + `require_escalated`）
- iOS 工程默认优先真机校验；如果未设置 `XCODE_DESTINATION`，脚本会先尝试“已连接真机”，找不到连接中的真机时自动回退到 `generic/platform=iOS Simulator`
- macOS Xcode 工程在未显式指定 destination 时走宿主机 `xcodebuild build`
- `XCODE_DEVICE_ID`、`XCODE_DEVICE_NAME`、`XCODE_PREFER_MODEL` 只影响“已连接真机”的自动选择与 simulator → 真机回退阶段
- `XCODE_DEVICE_ID` 必须填写 `xcodebuild` 的 destination id；不要填写 `devicectl` device identifier
- 只有 simulator destination 会关闭签名，适用于需要显式保留 simulator 构建校验的场景
- 如果显式 simulator 阶段失败且命中第三方依赖的 simulator-only 链接白名单错误，脚本默认会自动切到已连接真机重跑一次 `build`
- 真机回退默认开启：`XCODE_DEVICE_FALLBACK=1`；它只在首次 destination 是 simulator 时生效
- 设置 `XCODE_DEVICE_FALLBACK=0` 可关闭自动真机回退，保留“只跑显式配置 destination”的行为
- `XCODE_UI_SMOKE_MODE` 控制 UI smoke：`off`（关闭）、`auto`（命中 UI 改动且 spec 存在时执行）、`required`（命中 UI 改动时强制执行并阻塞失败）
- `XCODE_UI_SMOKE_SPEC` 指定 smoke spec 路径，默认 `.codex/ui-smoke.yml`
- UI smoke 默认采用 text-first 断言（accessibility tree），截图用于失败证据
- 这些覆盖配置只影响 `xcodebuild` 参数，不会跳过固定链路里的前置 `testing` / `code-review`，也不会改变“`.xcworkspace` 优先于 `.xcodeproj`”的默认规则

## 示例

### 默认真机优先

```bash
XCODE_WORKSPACE="Acrux/Acrux.xcworkspace"
XCODE_SCHEME="Acrux_DEV"
XCODE_CONFIGURATION="Debug"
XCODE_PREFER_MODEL="iPad"
```

### 显式指定真机 destination

```bash
XCODE_WORKSPACE="Acrux/Acrux.xcworkspace"
XCODE_SCHEME="Acrux_DEV"
XCODE_CONFIGURATION="Debug"
XCODE_DEVICE_ID="00008130-0018782A0210001C"
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
