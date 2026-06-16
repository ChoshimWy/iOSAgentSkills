# Checkpoint 与 Fail-Fix-Report 合同

目标：把“多 Agent 编排流程”从建议提升为可执行合同，降低并行漂移和返工。

## Checkpoint 定义（单一事实源）

- 本轮由主 Agent 维护 `checkpoint_status` 作为单一事实源。
- 所有角色输出都以该状态为准，不重复发明新阶段名。

### CP0：Intent Lock（计划对齐）
- 责任人：main agent
- 进入条件：任务已澄清目标、边界、成功标准
- 通过标准：明确 `lite` / `standard` / `full` 档位与验证基线
- 失败处理：补齐缺失信息后重评，不进入实现

### CP1：Anchor Slice（首个关键切片验收）
- 责任人：coder worker + main agent
- 进入条件：CP0 通过
- 通过标准：先完成最小关键切片并由 main agent 验收
- 失败处理：只回写当前切片问题，不扩散到并行大改
- 硬约束：未通过 CP1 不启动无必要并行扩散

### CP2：Validation Baseline Freeze（验证基线冻结）
- 责任人：main agent + tester/reviewer
- 进入条件：CP1 通过并进入验证阶段
- 通过标准：锁定本轮 workspace / scheme / destination / 关键验证命令
- 失败处理：先校准基线再继续验证，不在漂移基线上比较结果

### CP3：Final Gate（定向验证与审查收口）
- 责任人：main agent
- 进入条件：CP2 通过，修复轮次收敛
- 通过标准：定向验证或必要验证通过，且独立 reviewer subAgent 执行的 `code-review` 无 blocking findings；reviewer subAgent 不可用时只能 blocked / pending review；`ios-verification` 仅在用户显式要求或高风险时按需补强
- 失败处理：按首个真实失败点回写 coder，进入下一轮；若环境阻塞则标记 blocked

## Fail-Fix-Report 纪律

- `fail`：发现阻塞项时，必须先定位首个真实失败点和影响范围。
- `fix`：可修复则优先修复，并在同一基线重跑必要验证。
- `report`：仅在“已修复并重跑”或“明确 blocked 原因”两种状态下汇报。
- 禁止：带着已知阻塞项直接宣告完成，或把未重跑的修复当作已验证结论。
