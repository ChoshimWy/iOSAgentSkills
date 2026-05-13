# 失败回环规则

## 总流程
1. 主 Agent 先选择 `lite` / `standard` / `full` 档位
2. coder 完成实现（如适用）
3. reviewer / tester 按档位给出结论
4. 主 Agent 聚合后决定是否回写 coder
5. 代码收敛后，主 Agent 执行最终 `verify-ios-build`（如适用）
6. gate 失败则再次回写 coder

## wait 与聚合策略
- `wait_agent(...)` 只在主 Agent 需要当前结果推进下一步时使用，不要为轮询而频繁等待。
- reviewer / tester 的结论优先按“首个真实阻塞点 -> 影响范围 -> 下一轮成功标准”聚合，再回写 coder。
- 如果当前轮因为运行时或上层策略无法真正拉起 subAgent，主 Agent 必须显式说明本轮是单 Agent fallback。

## 回写 coder 的格式
- 问题类型
- 影响文件范围
- 首个真实失败点
- 必须保持不变的验证基线
- 本轮成功标准

## 停止条件
- 同一类问题最多回写 coder 2 次
- 如果问题仍未收敛，主 Agent 直接收口为 blocked
- 如果门禁被环境阻塞，主 Agent 明确报告阻塞点，不继续盲目循环

## 权限与升级
- 普通仓库读取、静态审查与文档比对默认留在 sandbox 内完成。
- 一旦最终门禁或目标项目环境验证需要越过 sandbox，主 Agent 使用 `functions.exec_command` 并按需设置 `sandbox_permissions=\"require_escalated\"`，不要通过其它绕路方式规避升级。

## 何时升级 tester 为 worker
- tester explorer 明确判断“缺少必要测试代码”
- 用户明确要求补 `unit test` / `UI test`
- 当前问题本质是测试缺口，而不是实现错误

## 会话切分
- 长任务默认按“排查 / 实现 / 验证 / 提交”切分会话。
- 新会话只携带目标、关键路径、验证基线和上一轮结论，不复制完整历史。
- Apple/Xcode 项目改动的最终完成态仍以目标项目环境中的 `verify-ios-build` 成功为准。
