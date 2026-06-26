# `.codex/xcodebuild.env` 覆盖配置

当自动发现的 workspace、project、scheme 或 destination 不正确时，在仓库根目录创建配置文件（Codex 使用 `.codex/xcodebuild.env`；CC 用户可直接在项目根目录设置环境变量）。

如果同机同仓会有多个 Codex / Claude CLI 并发处理同一 Xcode 项目，本机安装脚本会先同步全局 wrapper 到 `~/.codex/bin/codex_verify`。若目标项目再把 `config/codex/templates/codex_verify.example.sh` 复制到项目根目录并重命名为 `codex_verify.sh`，则项目脚本优先；否则 `ios-verification` 自动回退到全局 wrapper。wrapper 会自动接入 shared build-queue daemon，把验证型 `xcodebuild` 串行排队执行，并统一使用 Xcode 系统 DerivedData（`~/Library/Developer/Xcode/DerivedData`）。

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
# 验证 artifact 与日志 formatter（可选，脚本自动处理；Agent 不应手动安装或调用）
CODEX_VERIFY_ARTIFACT_DIR=".codex/build-results/latest"
CODEX_VERIFY_FORMATTER="auto"
CODEX_VERIFY_TOOL_INSTALL="auto"
```

## 规则

- `XCODE_WORKSPACE` 与 `XCODE_PROJECT` 二选一即可
- 如果两个都配置，脚本优先使用 `XCODE_WORKSPACE`
- `XCODE_SCHEME` 建议显式配置，避免多 scheme 仓库误判
- 如果未显式设置 `XCODE_SCHEME`，脚本默认优先选择绑定了单元测试 `*Tests` target / bundle 的 scheme；若不存在，再回退到其它测试 scheme（例如 `*UITests`、`*_TEST`）
- 如果当前任务里已经先跑过定向测试，可选验证应优先复用同一套 workspace / scheme / destination 基线；必要时用 `XCODE_SCHEME` / `XCODE_DESTINATION` 显式固定
- 定向 XCTest 不要手工拼 `-workspace` / `-scheme` / `-destination`；应通过 `--build-check` 或 `scripts/build-check.sh` 只传 `-only-testing` / `-skip-testing` 与 action，让脚本从 `.codex/xcodebuild.env` 或自动发现结果注入 workspace、scheme 与 destination
- 如果显式 `XCODE_SCHEME` 或低层 `codex_verify -- <xcodebuild args>` 里的 `-scheme` 不存在于 shared schemes，wrapper / build-check 会 fail-fast 并打印可用 scheme；不要把环境名和测试动作拼成不存在的 scheme（例如 `Acrux_DEV_TEST`）
- 验证 wrapper 会把验证型 `xcodebuild` 统一提交到 shared build-queue daemon，并固定使用 Xcode 系统 DerivedData；不要再通过旧 `XCODE_DERIVED_DATA_*` / `CODEX_DERIVED_DATA_SLOT` 公开配置调整缓存策略
- 默认不做 `clean build`
- 可选验证仍必须在目标项目根目录的项目环境执行；`.codex/xcodebuild.env` 只负责补充参数，不会把最终验证降级成沙箱构建
- `codex_verify.sh` / `~/.codex/bin/codex_verify` 负责接入 shared build-queue daemon 与验证入口控制；workspace / scheme / destination 仍由本文件与脚本默认策略决定
- 本地需要执行 `xcodebuild` 参数探测或验证（含 `-list` / `-showdestinations` / build/test）时，默认在项目环境由主 Agent 通过 wrapper 执行（CC 使用 `Bash` 工具启动 `codex_verify.sh` / `~/.codex/bin/codex_verify`；Codex 使用 `functions.exec_command` + `require_escalated` 启动同一 wrapper）；不得直接调用 `xcodebuild` 二进制
- 如果 `--queue-status`、wrapper 输出或 `build.db is locked` 表明已有其他 Agent 正在执行验证，当前 Agent 默认应等待 shared build-queue daemon，或把本轮标记为 `env_issue` / `blocked`；不要切到单独 `-derivedDataPath` 跑同一组验证来绕过锁
- iOS 工程默认优先真机校验；如果未设置 `XCODE_DESTINATION`，脚本会先尝试“已连接真机”，找不到连接中的真机时自动回退到可用 iOS Simulator
- 如果未设置 `XCODE_DESTINATION`、`XCODE_DEVICE_ID`、`XCODE_DEVICE_NAME`、`XCODE_PREFER_MODEL`，且项目 `TARGETED_DEVICE_FAMILY` 可推断默认机型，脚本会按设备族选择验证基线：支持 iPhone（`1`，包括 iPhone+iPad 通用）时优先 iPhone；不支持 iPhone 但支持 iPad（`2`）时优先 iPad，避免 iPad-only 工程误落到列表中的第一个 iPhone simulator；显式 `XCODE_DESTINATION` 仍按显式配置执行
- macOS Xcode 工程在未显式指定 destination 时走宿主机 `xcodebuild build`
- `XCODE_DEVICE_ID`、`XCODE_DEVICE_NAME`、`XCODE_PREFER_MODEL` 会影响“已连接真机”的自动选择与 simulator → 真机回退阶段；未显式设置 `XCODE_DESTINATION` 时，`XCODE_PREFER_MODEL` 也会影响 simulator fallback 的自动选择
- `XCODE_DEVICE_ID` 必须填写 `xcodebuild` 的 destination id；不要填写 `devicectl` device identifier
- `XCODE_DERIVED_DATA_*` 与 `CODEX_DERIVED_DATA_SLOT` 公开配置已移除；如果仍在环境变量或 `.codex/xcodebuild.env` 中设置，wrapper 会 fail-fast 并要求删除
- 只有 simulator destination 会关闭签名，适用于需要显式保留 simulator 构建校验的场景
- 如果显式 simulator 阶段失败且命中第三方依赖的 simulator-only 链接白名单错误，脚本默认会自动切到已连接真机重跑一次 `build`
- 真机回退默认开启：`XCODE_DEVICE_FALLBACK=1`；它只在首次 destination 是 simulator 时生效
- 设置 `XCODE_DEVICE_FALLBACK=0` 可关闭自动真机回退，保留“只跑显式配置 destination”的行为
- `XCODE_UI_SMOKE_MODE` 控制 UI smoke：`off`（关闭）、`auto`（命中 UI 改动且 spec 存在时执行）、`required`（命中 UI 改动时强制执行并阻塞失败）
- `XCODE_UI_SMOKE_SPEC` 指定 smoke spec 路径，默认 `.codex/ui-smoke.yml`
- UI smoke 默认采用 text-first 断言（accessibility tree），截图用于失败证据
- `CODEX_VERIFY_ARTIFACT_DIR` 指定结构化验证证据输出目录，默认 `.codex/build-results/latest`
- `CODEX_VERIFY_FORMATTER` 控制脚本内部 formatter：`auto`、`xcbeautify`、`xcpretty`、`xcprint`、`none`
- `CODEX_VERIFY_TOOL_INSTALL` 控制脚本是否自动安装缺失 formatter：`auto`（默认，失败后回退内建解析）、`off`（不安装）、`required`（无法安装即 blocked）
- 如需指定非默认安装命令，可在项目环境中设置 `CODEX_VERIFY_INSTALL_XCBEAUTIFY`、`CODEX_VERIFY_INSTALL_XCPRETTY`、`CODEX_VERIFY_INSTALL_XCPRINT`；值会由脚本解析并执行，Agent 不需要判断安装方式
- formatter 安装、选择、解析和脱敏都由 wrapper / 脚本负责；Agent 默认只读取合并了 job metadata 与最终结果的 `agent-summary.json`，仅在摘要不足时再读取 `verification-report.json`、`diagnostics.json`、`build-summary.txt` 等 artifact
- `agent-summary.json` 会输出 `project_selection` 与 `scheme_selection`，包括 `.xcworkspace` / `.xcodeproj` 选择来源、`.xcworkspace` 优先原因、scheme 是否绑定 `*Tests` / `*UITests`、testables 与候选 schemes；Agent 不需要重复扫描文件树判断这些基线
- 在 `ios-verification` 的 build/test destination 选择场景中，查找当前连接真机、匹配 `xcodebuild` destination、过滤 paired/disconnected 设备、按 `TARGETED_DEVICE_FAMILY` 推断 iPhone/iPad 验证基线、以及 simulator fallback 都属于脚本职责；Agent 不应绕过 wrapper 手动执行 `xcrun devicectl list devices` / `xcodebuild -showdestinations` 后自行选择验证设备
- 这些覆盖配置只影响 `xcodebuild` 参数，不会跳过固定链路里的定向验证 / `code-review`，也不会改变“`.xcworkspace` 优先于 `.xcodeproj`”的默认规则
- 如需查看当前队列状态，使用 `codex_verify.sh --queue-status` 或 `~/.codex/bin/codex_verify --queue-status`

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

### 定向 XCTest：脚本接管 workspace / scheme / destination

```bash
~/.codex/bin/codex_verify \
  --build-check /path/to/iOSAgentSkills/skills/ios-verification/scripts/build-check.sh \
  /path/to/SidusLinkPro \
  -only-testing:AcruxTests/Unity3DViewServiceStageMembershipTests/test_handleAddFixtureOrGroup_whenRunningCuePixelCCTCrossfadeIsZero_projectsZeroToStageChannel \
  test
```

等价地，在 iOSAgentSkills 仓内可直接调用：

```bash
skills/ios-verification/scripts/build-check.sh \
  /path/to/SidusLinkPro \
  -only-testing:AcruxTests/Unity3DViewServiceStageMembershipTests/test_handleAddFixtureOrGroup_whenRunningCuePixelCCTCrossfadeIsZero_projectsZeroToStageChannel \
  test
```

这类命令只提供测试 selector 和 action；不要额外传 `-scheme Acrux_DEV`，更不要拼出 `Acrux_DEV_TEST`。

### 显式保留 simulator 首次校验

```bash
XCODE_WORKSPACE="Acrux/Acrux.xcworkspace"
XCODE_SCHEME="Acrux_DEV"
XCODE_CONFIGURATION="Debug"
XCODE_DESTINATION="generic/platform=iOS Simulator"
XCODE_DEVICE_FALLBACK="1"
XCODE_PREFER_MODEL="iPad"
```
