# 失败回环规则

## 总流程
1. 主 Agent 先用任务分型器判定 `doc-only` / `rule-only` / `code-small` / `code-medium` / `code-risky`，再选择 `lite` / `standard` / `full` 档位并完成 `CP0 Intent Lock`
2. coder 先完成首个关键切片，通过 `CP1 Anchor Slice` 后再按需扩展
3. tester / reviewer 在冻结基线下工作，推进 `CP2 Validation Baseline Freeze`
4. 主 Agent 聚合后决定是否回写 coder
5. 代码收敛后，主 Agent 基于定向测试/必要验证与 `code-review` 推进 `CP3 Final Gate`
6. 用户显式要求、发布前自检或高风险时，主 Agent 再按需执行 `final-evidence-gate` / `verify-ios-build` 补强证据

## wait 与聚合策略
- `wait_agent(...)` 只在主 Agent 需要当前结果推进下一步时使用，不要为轮询而频繁等待。
- reviewer / tester 的结论优先按“首个真实阻塞点 -> 影响范围 -> 下一轮成功标准”聚合，再回写 coder。
- 如果当前轮因为运行时或上层策略无法真正拉起 subAgent，主 Agent 必须显式说明本轮是单 Agent fallback。
- `CP1` 未通过前禁止无必要并行扩散；先收敛首个关键切片再扩展后续角色或任务面。

## 回写 coder 的格式
- 问题类型
- 影响文件范围
- 首个真实失败点
- 必须保持不变的验证基线
- 本轮成功标准
- 对应 checkpoint（`CP1` / `CP2` / `CP3`）

## 停止条件
- 同一类问题最多回写 coder 2 次
- 如果问题仍未收敛，主 Agent 直接收口为 blocked
- 如果定向验证、审查或按需完整验证被环境阻塞，主 Agent 明确报告阻塞点，不继续盲目循环
- 定向验证失败或 `code-review` 存在 blocking findings 时，不得宣告默认收口完成
- 已达到同类问题回环上限时，`next_action` 只能是 `blocked`，不能标记为 `complete`

## Fail-Fix-Report
- `fail`：发现阻塞项时，先锁定首个真实失败点，不并发追加噪声问题。
- `fix`：可修复则先修复，并在同一基线重跑必要验证。
- `report`：仅报告“已修复并重跑”或“blocked 原因明确”两类状态。
- 禁止带着已知 blocking finding 直接汇报完成。

## 权限与升级
- 普通仓库读取、静态审查与文档比对默认留在 sandbox 内完成。
- 一旦可选证据验证或目标项目环境验证需要越过 sandbox，主 Agent 使用 `functions.exec_command` 并按需设置 `sandbox_permissions=\"require_escalated\"`，不要通过其它绕路方式规避升级。

## 何时升级 tester 为 worker
- tester explorer 明确判断“缺少必要测试代码”
- 用户明确要求补 `unit test` / `UI test`
- 当前问题本质是测试缺口，而不是实现错误

## 会话切分
- 长任务默认按“排查 / 实现 / 验证 / 提交”切分会话。
- 新会话只携带目标、关键路径、验证基线和上一轮结论，不复制完整历史。
- Apple/Xcode 项目改动的默认完成态以定向测试/必要验证通过且 `code-review` 无阻塞为准；`final-evidence-gate` / `verify-ios-build` 仅在用户显式要求、发布前自检或高风险时按需补强证据。
