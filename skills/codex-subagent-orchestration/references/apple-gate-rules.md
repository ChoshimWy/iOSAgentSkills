# Apple/Xcode 项目可选证据验证规则

## 固定原则
- 默认完成标准是定向验证或必要验证通过，且独立 reviewer subAgent 执行的 `code-review` 无 blocking findings；reviewer subAgent 不可用时只能 blocked / pending review。
- 涉及代码改动时，`ios-verification` 默认只执行最窄定向单测；真机 / 模拟器验证不属于默认执行面。
- `ios-verification` 仅作为按需补强验证，由主 Agent 在用户显式要求、发布前自检或高风险时执行。
- 凡是 iOS/Xcode 项目环境验证或升级验证需要执行 `xcodebuild` 参数探测 / build / test，都必须由主 Agent 使用 `functions.exec_command` 并设置 `sandbox_permissions="require_escalated"`，以非沙盒环境启动 `codex_verify.sh` / `~/.codex/bin/codex_verify`。
- 执行可选完整验证时，证据必须来自目标项目根目录的非沙盒项目环境；sandbox 结果只能作为诊断线索，不能当完整项目环境结论。
- 私有库 / 私有组件改动默认使用主项目本地 `:path` 私有库依赖作为验证与独立 `code-review` 基线；修改真实私有库源码仓后，必须回主项目基于本地 `:path` 依赖验证与 review。未收到明确指令前，不切到线上版本化依赖或 `Pods/` vendored snapshot 验证 / review，验证通过后也默认保持当前本地 `:path` 状态。
- 可选完整验证继续遵守 `.xcworkspace` 优先、单元测试 scheme 优先与 iOS 真机优先约束；验证链路默认由 wrapper 接入 shared build-queue daemon，统一串行执行验证型 `xcodebuild`，并使用 Xcode 系统 DerivedData。

## 基线复用
- 若最后一次代码变更之后已经成功执行最窄定向单测，且未命中工程/依赖/签名/资源/设备能力高风险条件，`ios-verification` 可直接接受该证据，不因缺少真机 / 模拟器验证而默认升级。
- 如果同一任务已经先跑过定向测试或其它 build/test，`ios-verification` 默认复用同一套 workspace / scheme / destination 基线。
- 如果没有用户显式指定 scheme，默认优先真正绑定单元测试 `*Tests` target / bundle 的 scheme；`*UITests` 或其它 `*_TEST` 只作回退。
- 验证必须发生在最后一次 repo-tracked 代码、配置、资源或依赖快照变更之后；否则证据失效。

## 建议按需升级到 `ios-verification`
- `.xcodeproj`、`.xcworkspace`、scheme、test plan、xcconfig、Build Settings、构建脚本。
- 签名、entitlements、plist、capability、App Extension 或真实设备能力相关配置。
- `Podfile`、`Podfile.lock`、`Pods/Manifest.lock`、私有 Pod 版本或本地 `:path` 回切线上依赖。
- 资源、Storyboard/XIB、Assets、target membership、bundle packaging 相关内容。
- 定向测试只覆盖子库/子 target，不能证明主 App/consumer app 已集成通过。

## 回写规则
- 如果可选证据验证失败，主 Agent 回写 coder 时至少包含：
  - 首个真实失败点或证据不足原因
  - 使用或缺失的 workspace / scheme / destination
  - 必要日志摘要
- 可选验证失败不自动否定默认收口；主 Agent 必须同时说明默认收口证据、完整验证失败点与残余风险。
