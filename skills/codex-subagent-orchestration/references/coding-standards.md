# 多 Agent 编码与输出规范

## coder worker
- 先读本地事实，再实现；不要凭记忆假设项目结构、依赖、最低版本或现有行为。
- 默认采用影响最小、范围最小且可验证的改动方式；没有明确必要时，不做顺手重构、目录搬迁或命名清洗。
- 涉及 CocoaPods 私有库/本地联调时，先查 `Podfile` / `Podfile.lock` / `Pods/Manifest.lock`，确认真实源码位置；如需修改私有库，默认严格顺序是：保持主项目本地 `:path` 私有库依赖（仅在尚未指向本地源码时才切到本地 `:path`）-> 再修改本地私有库源码仓 -> 最后回到主项目基于该本地依赖做开发、验证与独立 `code-review`；私有库仓内自测不能替代主项目验证。验证通过后默认保持当前本地 `:path` 私有库依赖状态完成 review，除非用户明确要求回切线上或准备提交主项目依赖文件。若命中本地 `:path` Pod，禁止把 `Pods/` 副本当作 ownership。
- 如果改动了公共接口、配置前提、数据契约或调用时序，必须在输出里显式说明影响面。
- 固定输出：
  - `changed_files`
  - `summary`
  - `known_risks`
  - `test_impact` 或 `no_test_reason`
  - `change_intent`
  - `rollback_hint`
  - `checkpoint_status`
  - `first_failure`
  - `next_action`

## reviewer explorer
- 只基于当前代码与 diff 做静态读审，不把“可能有问题”包装成已复现事实。
- 可见回复必须使用中文 Markdown 表格，字段写 `阻塞问题` / `非阻塞建议`，不要裸露英文审查字段。
- `阻塞问题` 只放真实阻塞项，例如正确性错误、并发隔离缺口、availability 缺口、明显回归风险或公共契约破坏。
- 若变更误落在 `Pods/<LibraryName>`，且上下文显示该库来自本地 `:path` Pod / 私有组件联调，默认判定为真实阻塞项。
- 风格、命名、可读性或可延后优化统一归入 `非阻塞建议`。
- 审查问题默认按严重度降序输出，优先指出首个真实阻塞点。
- 若无阻塞项，写 `阻塞问题：无`，不要展开长解释。
- 输出同时补齐 `checkpoint_status` / `首个失败` / `下一步`；若存在阻塞项，`下一步` 不能是 `complete`。

## tester
- 默认先判断验证面、回归面和必要验证路径，再决定是否需要补测试代码（通过 `ios-feature-implementation(test-implementation)`）。
- 默认先尝试最窄定向单测：优先 `-only-testing` 到单个 test case / test class，其次最小受影响 test file / bundle；真机 / 模拟器验证不属于默认执行面。
- 输出必须明确区分：
  - `test_scope`：本次改动影响哪些验证面
  - `suggested_validation`：建议补跑或补看的验证动作
  - `executed_validation`：已经实际执行过的验证
  - `failure_attribution`：对现有失败、日志或报错的归因
  - `failure_attribution_type`：`code_bug` / `test_bug` / `env_issue` / `unknown`
  - `needs_test_code`：是否必须补测试代码（通过 `ios-feature-implementation(test-implementation)`）
  - `suggested_fix`：若有失败，建议修复方向
- tester 输出同时补齐 `checkpoint_status` / `first_failure` / `next_action`。
- 如果当前改动没有可低成本执行的单测路径，默认输出 `no_test_reason` 与 `suggested_validation`，而不是自动升级到真机 / 模拟器验证。
- 只有在主 Agent 明确要求，或 tester 已判断“缺少必要测试代码”时，才升级为 `tester worker`。

## main agent
- 默认先选择 `lite` / `standard` / `full` 自适应编排档位；除实现链路 reviewer subAgent 必须独立启动外，本仓不对 coder / tester / pm / reporter 等其它 subAgent 使用做额外限制；reviewer 不可用时报告 blocked / pending review。
- 默认维护 `checkpoint_status`（`CP0` / `CP1` / `CP2` / `CP3`）作为单一事实源；`CP1` 未通过前不启动无必要并行扩散。
- 聚合 reviewer / tester / gate 结果时，优先用首个真实阻塞点驱动下一轮，不要把多个层级问题混成模糊总结。
- 遵守 `fail-fix-report`：先 fail 定位，再 fix 重跑，最后 report；不可带着已知阻塞项宣告完成。
- 默认完成态由主 Agent 基于定向验证/必要验证与独立 reviewer subAgent `code-review` 结论裁决；`ios-verification` 仅作为按需补强验证。

## reporter
- 输出必须包含 `acceptance_matrix`，并覆盖“需求项 -> 证据 -> 状态(pass|fail|blocked)”。
- 输出同时补齐 `checkpoint_status` / `first_failure` / `next_action`；有阻塞项时禁止 `next_action=complete`。

## 低 Token 输出约束
- 搜索优先 `rg` 精确匹配，不做全仓库 `cat`。
- build/test/log 默认只回传关键错误段、过滤摘要或最后 80~120 行。
- 长日志写入 `/tmp/*.log`，回复只给路径和必要 excerpt。
- 长任务按“排查 / 实现 / 验证 / 提交”分会话，新会话只带目标、关键路径、验证基线和上一轮结论。

## 共享 iOS 代码规范
- 实现与审查中涉及 public API、注释、并发、UI ownership、可复用组件或风格敏感重构时，读取 `skills/ios-feature-implementation/references/coding-standards.md`。
- 本文件只保留多 Agent 输出合同与角色纪律；具体 Swift/iOS 代码规范以共享 reference 为准。
