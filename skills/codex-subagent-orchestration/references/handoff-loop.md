# 失败回环规则

## 总流程
1. 主 Agent 先做最小只读定位，再用任务分型器判定 `doc-only` / `rule-only` / `code-small` / `code-medium` / `code-risky`，选择 `lite` / `standard` / `full` 档位，并在任何写入前完成 `CP0 Intent Lock` 最小计划；该计划不依赖手动 Plan 模式
2. coder 先完成首个关键切片，通过 `CP1 Anchor Slice` 后再按需扩展
3. tester / reviewer 在冻结基线下工作，推进 `CP2 Validation Baseline Freeze`
4. 主 Agent 聚合后决定是否回写 coder
5. 代码收敛后，主 Agent 基于定向验证/必要验证与独立 reviewer subAgent `code-review` 推进 `CP3 Final Gate`
6. 用户显式要求、发布前自检或高风险时，主 Agent 再按需执行 `ios-verification` 补强证据

## 验证默认边界
- 默认验证先收敛到最窄定向单测：优先 `-only-testing` 到单个 test case / test class，其次最小受影响 test file / bundle。
- 若没有可低成本执行的单测路径，tester / 主 Agent 输出 `no_test_reason` 与 `suggested_validation`，不要自动升级到真机 / 模拟器验证。
- 真机 / 模拟器验证仅在用户显式要求、发布前自检、高风险或 `ios-verification` 判定证据不足时执行。

## wait 与聚合策略
- `wait_agent(...)` 只在主 Agent 需要当前结果推进下一步时使用，不要为轮询而频繁等待。
- reviewer / tester 的结论优先按“首个真实阻塞点 -> 影响范围 -> 下一轮成功标准”聚合，再回写 coder。
- 除实现链路 reviewer subAgent 必须独立启动外，本仓不对其它 subAgent 使用做额外限制。
- coder / tester / pm / reporter 等非 review 角色是否使用 subAgent 由主 Agent 按当前任务自行决定；实现链路 reviewer subAgent 必须独立启动，不可用时报告 blocked / pending review。
- 如果当前验证链路发现已有其他 Agent 正在执行同仓验证，主 Agent 应等待 shared build-queue daemon 当前任务完成后再继续；若环境长时间未释放，则按 `env_issue` / `blocked` 收口，不切到单独 `-derivedDataPath` 绕开同一个 `build.db`。
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
- 定向验证失败或 `code-review` 存在 `阻塞问题` 时，不得宣告默认收口完成
- 定向验证失败、独立 reviewer subAgent 未执行、或 `code-review` 存在 `阻塞问题` 时，不得宣告默认收口完成
- 已达到同类问题回环上限时，`next_action` 只能是 `blocked`，不能标记为 `complete`

## Fail-Fix-Report
- `fail`：发现阻塞项时，先锁定首个真实失败点，不并发追加噪声问题。
- `fix`：可修复则先修复，并在同一基线重跑必要验证。
- `report`：仅报告“已修复并重跑”或“blocked 原因明确”两类状态。
- 禁止带着已知 `阻塞问题` 直接汇报完成。

## 权限与升级
- 普通仓库读取、静态审查与文档比对默认留在 sandbox 内完成。
- 一旦涉及 iOS/Xcode 项目环境验证（含 `-list` / `-showdestinations` / build/test），主 Agent 必须使用 `functions.exec_command` 并设置 `sandbox_permissions=\"require_escalated\"`，以非沙盒环境启动 `codex_verify.sh` / `~/.codex/bin/codex_verify`；不要通过其它绕路方式规避升级。

## 何时升级 tester 为 worker
- tester explorer 明确判断“缺少必要测试代码”
- 用户明确要求补 `unit test` / `UI test`
- 当前问题本质是测试缺口，而不是实现错误

## 会话切分
- 长任务默认按“排查 / 实现 / 验证 / 提交”切分会话。
- 新会话只携带目标、关键路径、验证基线和上一轮结论，不复制完整历史。
- Apple/Xcode 项目改动的默认完成态以定向验证/必要验证通过且独立 reviewer subAgent `code-review` 无阻塞为准；`ios-verification` 仅在用户显式要求、发布前自检或高风险时按需补强证据。
