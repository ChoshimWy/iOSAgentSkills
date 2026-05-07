# 多 Agent 工具与 MCP 路由矩阵

## 文档与 API 事实
- Apple API、platform availability、WWDC、framework 指导：优先 `appleDeveloperDocs`，不要默认退回普通 web 搜索。
- 只有当问题超出 Apple 文档覆盖范围，或需要外部最新事实时，才额外使用 web。

## 构建、测试与设备
- 构建、测试、simulator、真机、截图、日志、xcresult：优先 `Build iOS Apps` / `xcodebuildmcp` 相关工具。
- `tester` 做定向验证、失败归因、日志查看时，优先复用 `ios-device-automation`、`ios-simulator-automation`、`testing` 既有能力。
- 最终 `verify-ios-build` 不下放给 subAgent；需要在目标项目环境执行最终门禁或越过 sandbox 时，由主 Agent 使用 `functions.exec_command` 并按需设置 `sandbox_permissions=\"require_escalated\"`。

## 并行与写操作
- 只有当多个开发者工具彼此独立、不会共享写集，也不涉及 `apply_patch`、格式化改写或其它写操作时，才允许使用 `multi_tool_use.parallel`。
- 代码修改、补丁应用、共享文件写入、以及同一轮 reviewer / tester 可能互相依赖的场景，默认保持串行。

## 非主链工具
- Figma 只在明确涉及设计稿、Code Connect、设计系统资产或 Figma 写操作时使用，不默认混入编码主链路。
- Browser / in-app browser 只用于 localhost / file 页面检查或前端交互验证，不替代 Apple API 查询、构建验证或最终门禁。
