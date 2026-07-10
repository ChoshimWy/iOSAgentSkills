# 角色输入输出契约

## coder worker

### 输入
- 任务目标
- ownership（允许修改的文件/模块）
- 成功标准
- 禁止改动范围
- 当前 reviewer / tester / gate 审查与验证结论（若是修复轮）

### 输出
- `changed_files`
- `summary`
- `known_risks`
- `test_impact` 或 `no_test_reason`
- `file_header_check`（新增 `.swift` / `.h` / `.m` / `.mm` 时必须为 `passed` 或 `blocked`；未新增时为 `not-applicable`）
- `change_intent`
- `rollback_hint`
- `checkpoint_status`
- `first_failure`
- `next_action`

### 输出约束
- 只给摘要和影响面，不粘贴大段 diff、文件全文或完整日志
- `first_failure` 无阻塞时写 `none`
- 若存在阻塞项，`next_action` 不能是 `complete`

### 不负责
- 最终完成态裁决
- 默认收口为定向验证 + 独立 reviewer subAgent `code-review`；`ios-verification` 按需升级
- 静态代码审查结论

## reviewer explorer

### 输入
- 当前任务目标
- `review_base_ref` 或明确的 fallback 基线
- 本次任务全量差异（staged、unstaged、untracked 与基线之后相关提交）
- 本次修改带来的直接影响面
- 风险关注点（如并发、availability、边界）

### 输出
- `审查范围`
- `影响面`
- `未审查变更`
- `阻塞问题`
- `非阻塞建议`
- `checkpoint_status`
- `首个失败`
- `下一步`

### 额外要求
- 必须由未参与本轮实现的独立 reviewer subAgent 执行；同一 Agent 实现后自审无效
- 如果 reviewer subAgent 无法启动，返回 `下一步: blocked` 并声明 `首个失败: reviewer subAgent unavailable`
- 必须检查新增 `.swift` / `.h` / `.m` / `.mm` 的文件头；当目标项目使用文件头却缺失 header、`Created by` 不是真实本机用户名，或出现 `Codex` / 字面量 `$(whoami)` / 占位符时，按阻塞项处理
- `阻塞问题` 只放真实阻塞项
- 若无阻塞项，写 `阻塞问题：无`，不要展开长解释
- `审查范围` 必须说明基线与纳入审查的 staged / unstaged / untracked / 提交范围
- `影响面` 必须说明已审查的直接调用方、契约边界与副作用边界
- `未审查变更` 无遗漏时写 `none`，否则列出未审查差异或影响面
- 审查问题默认按严重度降序输出
- `首个失败` 无阻塞时写 `none`
- 存在阻塞项时，`下一步` 只能是 `fix-and-rerun` 或 `blocked`

### 不负责
- 直接改代码
- 跑可选验证
- 判断任务已完成

## tester

### explorer 模式输入
- 当前任务目标
- 相关改动范围
- 已知验证基线（如 workspace / scheme / destination）

### explorer 模式默认输出
- `suggested_validation`
- `executed_validation`
- `failure_attribution`
- `failure_attribution_type`（`code_bug` | `test_bug` | `env_issue` | `unknown`）
- `needs_test_code`
- `checkpoint_status`
- `first_failure`
- `next_action`

### explorer 模式按需输出
- `test_scope`：仅当验证面会影响下一步决策
- `no_test_reason`：仅当没有可低成本执行的单测路径
- `suggested_fix`：仅当已有失败且需要回写 coder

### worker 模式额外输出
- `changed_test_files`
- `new_test_coverage`

### 不负责
- 最终完成态裁决
- 替代主 Agent 的默认收口或按需完整验证
- 自动升级到真机 / 模拟器验证

## reporter

### 输入
- 当前任务目标
- 各角色输出与最终验证结果
- 验收标准与验证基线

### 输出
- `acceptance_matrix`
- `delivery_summary`
- `validation_evidence`
- `residual_risks`
- `checkpoint_status`
- `first_failure`
- `next_action`

### 额外要求
- `acceptance_matrix` 至少包含：`需求项`、`证据`、`状态(pass|fail|blocked)`
- 存在阻塞项时，`next_action` 不能是 `complete`
- 若无阻塞项，`first_failure` 写 `none`
- 若交付物是正式 HTML 文档，reporter 只输出 source packet，并将最终生成交给 `html-docs`

### 不负责
- 改代码
- 替代主 Agent 的可选验证裁决
- 直接手写最终 HTML 文档模板或样式

## docs_researcher

### 输入
- 需要核实的 OpenAI/Codex 或 Apple API / availability / WWDC 问题
- 目标平台、SDK、Xcode 或 Codex runtime 版本约束

### 输出
- `question`
- `official_findings`
- `availability_or_version`
- `source_links`
- `uncertainties`
- `next_action`

### 额外要求
- 只读，不修改代码或配置
- 优先使用角色专属 OpenAI / Apple 官方文档 MCP
- 区分文档事实与推断，不用第三方文章替代官方结论
- 返回最小必要证据，不粘贴长文档

## design_researcher

### 输入
- 用户明确指定的 `.sketch` 源文件、页面、画板或组件
- 目标平台与需要还原的页面/状态范围

### 输出
- `design_source`
- `artboards_and_states`
- `layout_and_tokens`
- `assets_and_interactions`
- `implementation_contract`
- `ambiguities`
- `checkpoint_status`
- `first_failure`
- `next_action`

### 额外要求
- 只读，不修改 Sketch 文件、代码或配置
- 只使用专属 `sketchMCP` 读取源文件真相；截图、历史 UI 与主观推断不能替代源文件事实
- MCP 不可达、文件不可读或图层信息缺失时报告 blocked，不虚构尺寸、token 或交互
- 将源文件事实与待确认项分开；实现前由主 Agent 冻结 `implementation_contract`

## main agent

### 固定职责
- 默认先选择 `lite` / `standard` / `full` 档位；除实现链路的 reviewer subAgent 必须独立启动外，本仓不对 coder / tester / pm / reporter 等其它原生 subAgent 角色做额外限制
- reviewer subAgent 不可用时不得降级自审，必须报告 blocked / pending review；其它 subAgent 使用由主 Agent 按当前任务自行决定
- 聚合 coder / reviewer / tester 输出
- 精确回写 coder
- 执行默认收口为定向验证 + 独立 reviewer subAgent `code-review`；`ios-verification` 按需升级
- 判定任务完成 / 未完成 / 阻塞

### 固定输出（汇总态）
- `checkpoint_status`：至少包含 `CP0` / `CP1` / `CP2` / `CP3` 的 `pass|fail|blocked`
- `first_failure`：当前轮首个真实失败点（无则显式写 `none`）
- `next_action`：`fix-and-rerun` / `blocked` / `complete`
