# 多 Agent 工具与 MCP 路由矩阵

## 文档与 API 事实
- Apple API、platform availability、WWDC、framework 指导：优先 `apple-docs`；需要独立证据包时启动只读 `docs_researcher`，由其专属固定版本 `appleDeveloperDocs` 核实，不要默认退回普通 web 搜索。
- OpenAI/Codex 配置、模型与官方行为：优先 `openai-docs`；需要独立核实时由 `docs_researcher` 使用 `openaiDeveloperDocs`。官方文档 MCP 不放在全局 shared config，避免无关任务加载额外工具面。
- 用户明确指定 `.sketch` 源文件、画板或 Sketch 设计真源：启动只读 `design_researcher`，由其专属 `sketchMCP`（`http://localhost:31126/mcp`）读取图层与样式事实并输出 Design-to-Code Spec；MCP 未启动或源文件不可读时报告 blocked，不以截图或既有 UI 猜测替代。
- CodeGraph 仅配置给 `explorer` / `reviewer` 等确需代码关系与影响面分析的角色；其它 Agent 先用 `rg` 和精准文件切片。
- 正式 HTML 方案、PRD、评审、报告、任务清单、接口说明与 handoff 文档：统一使用 `html-docs`；其它 Skill 只提供 source packet、结论和证据路径。
- 只有当问题超出 Apple 文档覆盖范围，或需要外部最新事实时，才额外使用 web。

## 构建、测试与设备
- 构建、测试、simulator、真机、截图、日志、xcresult：优先 `Build iOS Apps` / `xcodebuildmcp` 相关工具。
- `tester` 做定向验证、失败归因、日志查看时，优先复用 `ios-verification`；设备/截图/导航证据才切 `ios-automation`。
- 默认验证先收敛到最窄定向单测；真机 / 模拟器验证不属于默认执行面，只有用户显式要求或主 Agent 判定证据不足 / 高风险时才升级。
- 默认收口为定向验证 + 独立 reviewer subAgent `code-review`；`ios-verification` 按需升级，不下放给 subAgent；凡是需要在目标项目环境执行 iOS/Xcode 验证，由主 Agent 使用 `functions.exec_command` 并设置 `sandbox_permissions=\"require_escalated\"`。
- 本地凡是需要执行 `xcodebuild` 参数探测或验证（含 `-list` / `-showdestinations` / build/test），默认都走非沙盒项目环境，并由主 Agent 使用 `functions.exec_command` 显式设置 `sandbox_permissions=\"require_escalated\"` 来启动 `codex_verify.sh` / `~/.codex/bin/codex_verify`；不得直接调用 `xcodebuild` 二进制，也不要让多个 Agent 各自裸跑 `xcodebuild`。
- 如果发现已有其他 Agent 正在执行验证，当前 Agent 应等待 shared build-queue daemon 串行出队，或按 `env_issue` / `blocked` 收口；不要切到单独 `-derivedDataPath` 跑同一组验证来规避 `build.db` 锁。

## 并行与写操作
- 只有当多个开发者工具彼此独立、不会共享写集，也不涉及 `apply_patch`、格式化改写或其它写操作时，才允许使用 `multi_tool_use.parallel`。
- 代码修改、补丁应用、共享文件写入、以及同一轮 reviewer / tester 可能互相依赖的场景，默认保持串行。

## 非主链工具
- Figma 只在明确涉及设计稿、Code Connect、设计系统资产或 Figma 写操作时使用，不默认混入编码主链路。
- Browser / in-app browser 只用于 localhost / file 页面检查或前端交互验证，不替代 Apple API 查询、构建验证或可选验证。

## 低 Token 工具策略
- 搜索优先 `rg` 精确匹配，不做全仓库 `cat` 或无过滤长输出。
- build/test/log 输出默认只回传关键错误段、过滤摘要或最后 80~120 行。
- 长日志写入 `/tmp/*.log`，回复只给路径和必要 excerpt。
- 只有在定位必须依赖完整日志时，才扩大输出范围，并说明原因。
