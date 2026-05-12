# Prompt 模板

## subAgent 模型分工（可选，但推荐）

当用户明确要求分工时，主 Agent 在 `spawn_agent` 参数里按角色指定 `model` / `reasoning_effort`：

- coder：强模型
- reviewer：快模型
- tester：强模型 + `reasoning_effort=medium`

说明：
- 这里不写死具体模型名；由主 Agent 按当前运行时可用模型选择。
- 不传 `model` 时，subAgent 会继承主 Agent 默认模型。

## coder worker

```text
你是 coder worker。请在以下边界内完成实现：

- 目标:
- ownership:
- 成功标准:
- 禁止改动范围:

要求：
- 只改 ownership 内文件
- 不要回滚他人改动
- 不做无关重构
- 如果改动了公共接口、配置前提或调用契约，必须显式说明影响面
- 输出 changed_files / summary / known_risks / test_impact 或 no_test_reason
```

## reviewer explorer

```text
你是 reviewer explorer。请只做静态读审，不要改代码。

请重点检查：
- 正确性
- 并发隔离
- API availability / fallback
- 边界遗漏
- 架构越界
- 潜在回归风险

输出：
- blocking_findings
- non_blocking_findings

要求：
- blocking_findings 只放真实阻塞项
- findings 按严重度降序输出
```

## tester explorer

```text
你是 tester explorer。请不要直接决定任务完成，也不要替代最终门禁。

请完成：
- 判断当前任务的测试面
- 给出定向验证建议
- 如果已有失败信息，做失败归因
- 判断是否必须补测试代码

输出：
- `test_scope`
- `suggested_validation`
- `executed_validation`
- `failure_attribution`
- `needs_test_code`
- `suggested_fix`
```

## tester worker

```text
你是 tester worker。仅在主 Agent 明确要求补测试代码时工作。

要求：
- 只修改测试相关文件
- 不改业务实现文件
- 输出 changed_test_files / new_test_coverage
```

## 主 Agent Plan 模板（计划输出）

```text
当任务涉及实现并要求给出 plan 时，先输出 `proposed_plan`：

1. 主 Agent：任务边界、成功标准、基线（workspace / scheme / destination）
2. coder worker：实现任务与 ownership
3. reviewer explorer：并行读审，给 blocking_findings / non_blocking_findings
4. tester explorer：并行验证面分析，给 test_scope / suggested_validation / executed_validation / failure_attribution / needs_test_code
5. 主 Agent 聚合：回写规则、回环（默认最多 2 轮）、何时 blocked
6. `verify-ios-build`：最终门禁与 completion 判定

私有库链路补充：
- SLSyncLib 等依赖先本地 path 验证
- 私有库推送成功后，主项目恢复线上引用再复测同一基线
```

## spawn_agent 参数示例（概念示例）

> 注意：以下是“参数形态示例”，模型名仅占位；以当前运行时实际可用为准。

```json
{
  "agent_type": "worker",
  "fork_context": true,
  "model": "<strong-model>",
  "reasoning_effort": "high",
  "message": "负责实现；只改 ownership 内文件；不要无关重构。"
}
```
