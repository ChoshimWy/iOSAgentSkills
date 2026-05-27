# Apple/Xcode 项目最终证据门禁规则

## 固定原则
- 最终 `final-evidence-gate` 只能由主 Agent 执行。
- `final-evidence-gate` 优先复用最后一次代码变更之后已成功的目标项目环境 `xcodebuild test` / `xcodebuild build` 证据。
- 现有证据不足、高风险或命中工程/依赖/签名/资源打包类改动时，再由主 Agent 执行 `verify-ios-build`。
- 最终验证证据必须来自目标项目环境，不能把 sandbox 结果当最终结论。
- 如果最终证据门禁或升级验证需要越过 sandbox，由主 Agent 使用 `functions.exec_command` 并按需设置 `sandbox_permissions="require_escalated"`。
- 如果同时存在 `.xcworkspace` 与 `.xcodeproj`，验证证据必须优先 `.xcworkspace`。
- iOS 项目默认优先已连接真机；只有低风险且不依赖签名、真实设备能力或打包链路时，才接受 simulator 作为最终证据。

## 基线复用
- 如果同一任务已经先跑过定向测试或其它 build/test，`final-evidence-gate` 默认复用同一套 workspace / scheme / destination 基线。
- 如果没有用户显式指定 scheme，默认优先真正绑定单元测试 `*Tests` target / bundle 的 scheme；`*UITests` 或其它 `*_TEST` 只作回退。
- 验证必须发生在最后一次 repo-tracked 代码、配置、资源或依赖快照变更之后；否则证据失效。

## 必须升级到 `verify-ios-build`
- `.xcodeproj`、`.xcworkspace`、scheme、test plan、xcconfig、Build Settings、构建脚本。
- 签名、entitlements、plist、capability、App Extension 或真实设备能力相关配置。
- `Podfile`、`Podfile.lock`、`Pods/Manifest.lock`、私有 Pod 版本或本地 `:path` 回切线上依赖。
- 资源、Storyboard/XIB、Assets、target membership、bundle packaging 相关内容。
- 定向测试只覆盖子库/子 target，不能证明主 App/consumer app 已集成通过。

## 回写规则
- 如果最终证据门禁失败，主 Agent 回写 coder 时至少包含：
  - 首个真实失败点或证据不足原因
  - 使用或缺失的 workspace / scheme / destination
  - 必要日志摘要
- 在 `final-evidence-gate` 接受现有证据或 `verify-ios-build` 成功前，主 Agent 不得宣告任务完成。
