# Apple/Xcode 项目最终门禁规则

## 固定原则
- 最终 `verify-ios-build` 只能由主 Agent 执行。
- 最终门禁必须在目标项目环境执行，不能把 sandbox 结果当最终结论。
- 如果同时存在 `.xcworkspace` 与 `.xcodeproj`，必须优先 `.xcworkspace`。
- iOS 项目默认优先已连接真机；找不到连接中的真机时才回退到 simulator。

## 基线复用
- 如果同一任务已经先跑过定向测试或其它 build/test，最终门禁默认复用同一套 workspace / scheme / destination 基线。
- 如果没有用户显式指定 scheme，默认优先真正绑定单元测试 `*Tests` target / bundle 的 scheme；`*UITests` 或其它 `*_TEST` 只作回退。

## 回写规则
- 如果最终门禁失败，主 Agent 回写 coder 时至少包含：
  - 首个真实失败点
  - 使用的 workspace / scheme / destination
  - 必要日志摘要
- 在 `verify-ios-build` 成功前，主 Agent 不得宣告任务完成。
