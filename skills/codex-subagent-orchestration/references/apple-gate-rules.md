# Apple/Xcode 项目可选证据验证规则

## 固定原则
- 默认完成标准是定向测试或必要验证通过，且 `code-review` 无 blocking findings。
- `final-evidence-gate` / `verify-ios-build` 仅作为按需补强验证，由主 Agent 在用户显式要求、发布前自检或高风险时执行。
- 如果可选证据验证或升级验证需要越过 sandbox，由主 Agent 使用 `functions.exec_command` 并按需设置 `sandbox_permissions="require_escalated"`。
- 执行可选完整验证时，证据必须来自目标项目环境，不能把 sandbox 结果当完整项目环境结论。
- 可选完整验证继续遵守 `.xcworkspace` 优先、单元测试 scheme 优先、iOS 真机优先与系统 DerivedData 约束。

## 基线复用
- 如果同一任务已经先跑过定向测试或其它 build/test，`final-evidence-gate` 默认复用同一套 workspace / scheme / destination 基线。
- 如果没有用户显式指定 scheme，默认优先真正绑定单元测试 `*Tests` target / bundle 的 scheme；`*UITests` 或其它 `*_TEST` 只作回退。
- 验证必须发生在最后一次 repo-tracked 代码、配置、资源或依赖快照变更之后；否则证据失效。

## 建议按需升级到 `verify-ios-build`
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
