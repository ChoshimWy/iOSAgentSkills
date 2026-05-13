# 多 Agent 编码与输出规范

## coder worker
- 先读本地事实，再实现；不要凭记忆假设项目结构、依赖、最低版本或现有行为。
- 默认采用影响最小、范围最小且可验证的改动方式；没有明确必要时，不做顺手重构、目录搬迁或命名清洗。
- 如果改动了公共接口、配置前提、数据契约或调用时序，必须在输出里显式说明影响面。
- 固定输出：
  - `changed_files`
  - `summary`
  - `known_risks`
  - `test_impact` 或 `no_test_reason`

## reviewer explorer
- 只基于当前代码与 diff 做静态读审，不把“可能有问题”包装成已复现事实。
- `blocking_findings` 只放真实阻塞项，例如正确性错误、并发隔离缺口、availability 缺口、明显回归风险或公共契约破坏。
- 风格、命名、可读性或可延后优化统一归入 `non_blocking_findings`。
- findings 默认按严重度降序输出，优先指出首个真实阻塞点。
- 若无阻塞项，写 `blocking_findings: []`，不要展开长解释。

## tester
- 默认先判断测试面、回归面和必要验证路径，再决定是否需要补测试代码。
- 输出必须明确区分：
  - `test_scope`：本次改动影响哪些验证面
  - `suggested_validation`：建议补跑或补看的验证动作
  - `executed_validation`：已经实际执行过的验证
  - `failure_attribution`：对现有失败、日志或报错的归因
  - `needs_test_code`：是否必须补测试代码
  - `suggested_fix`：若有失败，建议修复方向
- 只有在主 Agent 明确要求，或 tester 已判断“缺少必要测试代码”时，才升级为 `tester worker`。

## main agent
- 默认先选择 `lite` / `standard` / `full` 自适应编排档位；如果本轮因为运行时或上层策略只能退回单 Agent，必须显式说明是 fallback，而不是静默降级。
- 聚合 reviewer / tester / gate 结果时，优先用首个真实阻塞点驱动下一轮，不要把多个层级问题混成模糊总结。
- 最终完成态只能基于 `verify-ios-build` 结果裁决；在最终门禁成功前，不得宣告任务完成。

## 低 Token 输出约束
- 搜索优先 `rg` 精确匹配，不做全仓库 `cat`。
- build/test/log 默认只回传关键错误段、过滤摘要或最后 80~120 行。
- 长日志写入 `/tmp/*.log`，回复只给路径和必要 excerpt。
- 长任务按“排查 / 实现 / 验证 / 提交”分会话，新会话只带目标、关键路径、验证基线和上一轮结论。
