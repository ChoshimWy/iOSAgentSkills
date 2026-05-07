# 失败回环规则

## 总流程
1. coder 完成实现
2. reviewer / tester 并行给出结论
3. 主 Agent 聚合后决定是否回写 coder
4. 代码收敛后，主 Agent 执行最终 `verify-ios-build`
5. gate 失败则再次回写 coder

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

## 何时升级 tester 为 worker
- tester explorer 明确判断“缺少必要测试代码”
- 用户明确要求补 `unit test` / `UI test`
- 当前问题本质是测试缺口，而不是实现错误
