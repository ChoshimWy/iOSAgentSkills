# 角色输入输出契约

## coder worker

### 输入
- 任务目标
- ownership（允许修改的文件/模块）
- 成功标准
- 禁止改动范围
- 当前 reviewer / tester / gate findings（若是修复轮）

### 输出
- `changed_files`
- `summary`
- `known_risks`
- `test_impact` 或 `no_test_reason`

### 输出约束
- 只给摘要和影响面，不粘贴大段 diff、文件全文或完整日志

### 不负责
- 最终完成态裁决
- 最终 `verify-ios-build`
- 静态代码审查结论

## reviewer explorer

### 输入
- 当前任务目标
- 需要审查的 diff / 文件范围
- 风险关注点（如并发、availability、边界）

### 输出
- `blocking_findings`
- `non_blocking_findings`

### 额外要求
- `blocking_findings` 只放真实阻塞项
- 若无阻塞项，写 `blocking_findings: []`，不要展开长解释
- findings 默认按严重度降序输出

### 不负责
- 直接改代码
- 跑最终门禁
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
- `needs_test_code`

### explorer 模式按需输出
- `test_scope`：仅当验证面会影响下一步决策
- `suggested_fix`：仅当已有失败且需要回写 coder

### worker 模式额外输出
- `changed_test_files`
- `new_test_coverage`

### 不负责
- 最终完成态裁决
- 替代 `verify-ios-build`

## main agent

### 固定职责
- 默认先选择 `lite` / `standard` / `full` 档位，必要时明确说明单 Agent fallback
- 启动与回收 subAgent
- 聚合 coder / reviewer / tester 输出
- 精确回写 coder
- 执行最终 `verify-ios-build`
- 判定任务完成 / 未完成 / 阻塞
