---
name: code-review
description: iOS/Swift 静态代码审查 Skill。用于 review diff、PR、SDK API 与实现质量；用于实现链路收口时必须由未参与实现的独立 reviewer subAgent 执行，避免同一 Agent 实现后自审；只输出基于代码和已知上下文的审查结论，不负责直接修复实现、运行时排障、性能取证或构建配置。
---

# 代码审查

## Purpose

Review iOS/macOS code changes, identify correctness and maintainability risks, evaluate verification sufficiency, and produce structured review results with clear severity and ownership.

## 中文说明

该 Skill 是静态审查专项 Skill。

负责：
- 审查本次任务差异及直接影响面。
- 发现正确性、安全性、内存、并发、性能与可维护性问题。
- 审查 public/open API、SDK 接口与调用契约。
- 审查测试与验证故事是否成立。
- 输出结构化审查发现和风险结论。

不负责：
- 直接修复代码。
- 运行时 crash、泄漏、卡顿定位。
- 性能 benchmark 或 Instruments。
- 构建系统、签名、Archive、CI 配置。

## When to Use

- 用户要求 review 代码、PR、diff。
- 实现任务进入定向验证 / no_test_reason 之后的静态审查阶段；该场景必须由未参与实现的独立 reviewer subAgent 执行。
- SDK、Framework、公共 API 设计评审。
- 合入前质量门禁。
- 验证证据充分性评估。

## When Not to Use

- 需要修复代码时。
- 需要复现 crash、异常、泄漏或卡顿时。
- 需要性能 profiling、xctrace、Instruments 时。
- 需要执行 build/test 或验证策略设计时。

## Agent Rules

### Review Priority

固定优先级：

```text
正确性
→ 安全性
→ 内存
→ 并发
→ 性能
→ 可维护性
→ 一致性
```

### Reviewer Independence Rules

- 用于实现链路收口时，必须由未参与本轮实现的独立 reviewer subAgent 执行。
- 同一 Agent 先实现再执行本 Skill 的审查结论无效，不能作为完成条件。
- 如果无法确认 reviewer 独立性或无法启动 reviewer subAgent，可见回复写 `status: blocked` / `首个失败：reviewer subAgent unavailable` / `下一步：blocked`，并用中文表格呈现。
- 纯 review 请求也应由独立 reviewer subAgent 执行；如果平台无法启动 reviewer subAgent，必须说明审查独立性缺口。

### Evidence Rules

- 审查发现必须优先输出，并使用与主回复一致的紧凑 Markdown 表格。
- 审查发现按严重等级排序。
- 可见回复字段默认中文化：`阻塞问题`、`非阻塞建议`、`审查范围`、`影响面`、`未审查变更`、`首个失败`、`验证故事`、`审查独立性`、`风险等级`、`下一步`。
- 无阻塞项时必须显式输出 `阻塞问题：无`；不要在可见回复中裸露 `blocking_findings: []`，除非调用方明确要求机器可读 JSON。
- 必须尽量绑定文件和行号。
- 不得伪造运行时证据。
- 缺少证据时必须明确说明限制。
- 只根据代码、diff 与已知上下文下结论。

### Scope Rules

- 默认审查对象为本次任务全量差异与直接影响面。
- 差异范围应覆盖 staged、unstaged、untracked 与任务起点之后的相关提交。
- 优先使用 `review_base_ref -> 当前工作区`。
- 无法确定基线时必须记录在 `review_scope`。
- 必须审查：
  - public API
  - 调用方
  - 数据契约
  - 并发边界
  - 网络/缓存/数据库副作用
  - 验证故事
- 未覆盖部分必须写入 `unreviewed_changes`。

### Business Invariant Review Rules

- 审查正确性前，先从调用方、状态写入点、持久化 / 缓存 / 输出路径中提取本次改动依赖的业务不变量；不要只根据字段名推断语义。
- 对表示业务状态的布尔字段，要检查是否存在组合口径、别名或派生状态，例如 `selected`、`inStage`、`inGroup`、`running`、`dirty`、`snapshot`、`promoted` 等；若代码只检查其中一个字段，必须回到真实消费链路确认是否漏判。
- 当最新提交是 test-only、comment-only 或只补验证，但 review 结论涉及生产行为时，必须把审查范围扩展到同一任务 / PR / `review_base_ref..HEAD` 的相关实现提交，并在 `review_scope` 写明累计 diff，而不是只审最新提交。
- 对自动入队、自动恢复、fallback、snapshot hydrate、cache reuse、merge gate、权限绕过、Stage / selection / ownership 这类“只应在特定状态触发”的逻辑，必须同时审正向触发条件与负向保护条件。
- 测试充分性不能只看 happy path：若修复是“off-state 时应执行恢复 / fallback”，也要检查“already-in-state / owned-by-group / excluded / locked / dirty”等负向用例是否防止误恢复或误覆盖。
- 示例：在 Stage membership 类业务中，`fixtureListSelected` 不应被默认视为唯一 Stage 真源；需要继续搜索是否存在 group membership / collection membership / virtual membership 等等价入 Stage 口径，如 `isInFixtureListGroup`。
- 若发现测试只覆盖正向路径、缺少负向业务不变量，应至少输出为 `非阻塞建议`；若缺失的负向路径可能导致数据覆盖、设备误发码、权限绕过或持久化污染，应升级为 `阻塞问题`。

### Validation Story Rules

必须检查：

- 定向验证是否发生在最后一次代码修改之后。
- executed_validation 是否覆盖目标 target。
- 是否需要进入 `ios-verification` 补强证据。

规则：

- 最窄定向单测已通过且风险较低时，不得仅因为没跑真机/模拟器就判定证据不足。
- 高风险工程、依赖、签名、资源、设备能力改动可要求升级验证。

### Private Dependency Rules

发现以下情况默认阻塞：

- 修改发生在 `Pods/<Library>`。
- 实际项目使用本地 `:path` Pod。
- 验证发生在 vendored snapshot 而非真实源码。

### Coding Standards Reference

- Use `skills/ios-feature-implementation/references/coding-standards.md` as the shared standard when classifying style, documentation, public API, concurrency, UI ownership, or private dependency review results.
- Apply that reference as review policy; do not turn `非阻塞建议` style preferences into `阻塞问题` unless they violate the blocking criteria.

### Comment Rules

阻塞：

- public/open API 缺少必要中文文档注释。
- 并发边界语义缺失。
- 副作用语义缺失。
- 失败路径语义缺失。
- 注释未默认使用中文，或注释与实现不一致。

非阻塞：

- 文案优化。
- 命名建议。
- 可读性建议。

### Token Budget

- 不读取完整 build.log。
- 不读取完整 xcresult dump。
- 不重复输出大段 diff。
- 优先让本地脚本或窄范围命令生成 review packet（scoped diff、changed files、关键符号、验证摘要），reviewer 只消费必要证据。
- 审查发现优先于代码摘录。
- 输出应聚焦阻塞项与风险。

## Inputs

```json
{
  "review_base_ref": "optional",
  "changed_files": [],
  "diff_scope": "working-tree",
  "validation_result": {},
  "constraints": [],
  "reviewer_independence": "independent-subagent | pure-review | unavailable"
}
```

## Outputs

以下 JSON 字段是内部 / 机器交接合同；面向用户的可见回复必须按 `Reporting Template` 使用中文表格标签。

```json
{
  "status": "complete | blocked | partial",
  "blocking_findings": [],
  "non_blocking_findings": [],
  "review_scope": "...",
  "impact_scope": "...",
  "unreviewed_changes": "none",
  "first_failure": "none",
  "verification_story": "accepted | needs-ios-verification | insufficient",
  "risk_level": "low | medium | high",
  "reviewer_independence": "independent-subagent | pure-review | unavailable",
  "next_action": "fix-and-rerun | blocked | complete"
}
```

字段中文映射：

| 内部字段 | 可见中文标签 |
| --- | --- |
| `blocking_findings` | 阻塞问题 |
| `non_blocking_findings` | 非阻塞建议 |
| `review_scope` | 审查范围 |
| `impact_scope` | 影响面 |
| `unreviewed_changes` | 未审查变更 |
| `first_failure` | 首个失败 |
| `verification_story` | 验证故事 |
| `reviewer_independence` | 审查独立性 |
| `risk_level` | 风险等级 |
| `next_action` | 下一步 |

## Severity Format

### 阻塞问题

```text
🔴 [File:Line]
Issue
Suggestion
```

### 非阻塞建议

```text
🟡 [File:Line]
Issue
Suggestion
Reason
```

### Positive Finding

```text
✅ [File:Line]
Positive observation
```

## Exit Conditions

### complete

- 审查已由独立 reviewer subAgent 执行；实现链路收口审查确认未由实现 Agent 自审。
- `阻塞问题` 为空 / 无。
- `审查范围` 明确。
- `影响面` 已覆盖。
- `验证故事` 已给出。

### blocked

- 实现链路收口审查无法确认独立 reviewer subAgent 或 reviewer subAgent 不可用。
- 存在 `阻塞问题`。
- 存在未确认高风险影响面。
- 验证故事无法成立。

### partial

- 存在无法审查的差异。
- review base 不明确。
- 部分影响面缺乏证据。

## Escalation Rules

升级到 `debugging`：

- crash
- memory leak
- hang
- runtime issue

升级到 `ios-performance`：

- benchmark
- measure(metrics:)
- xctrace
- Instruments

升级到 `ios-verification`：

- 高风险工程变更
- 证据明显不足
- 用户要求最终验证

升级到 `ios-verification`：

- 需要裁决现有证据是否足够

升级到实现型 Skill：

- 已确认问题且需要修复

## Reporting Template

```text
审查结果：

| # | 类别 | 对象 / 文件 | 结论 / 问题 | 证据 / 行号 | 必要性 / 风险 | 建议 / 下一步 | 状态 |
|---|---|---|---|---|---|---|---|
| 1 | 阻塞问题 | 无 | 未发现阻塞性问题 | diff + 代码路径 | ✅ 通过 | 可继续收口 | complete |
| 2 | 非阻塞建议 | path/file.swift | 可延后优化点 | L10-L20 | ⚠️ 可选 | 后续迭代处理 | complete |

审查范围与门禁：

| 项目 | 结论 | 证据 / 说明 | 状态 |
|---|---|---|---|
| 审查范围 | ... | review_base_ref / staged / unstaged / untracked | complete |
| 影响面 | ... | 调用方 / 契约 / 副作用边界 | complete |
| 未审查变更 | none | 无遗漏时写 none | complete |
| 首个失败 | none | 无阻塞时写 none | complete |
| 验证故事 | accepted | 定向验证或 no_test_reason 是否成立 | complete |
| 审查独立性 | independent-subagent | 实现链路必须独立 reviewer subAgent | complete |
| 风险等级 | low | low / medium / high | complete |
| 下一步 | complete | fix-and-rerun / blocked / complete | complete |
```

## Reference Resources

- `../ios-feature-implementation/references/coding-standards.md`: shared iOS coding standards for implementation and review classification.

## Relationship to Other Skills

- 默认承接定向验证 / no_test_reason 之后的第三步，且该第三步必须由独立 reviewer subAgent 执行。
- 修复问题时切换实现型 Skill。
- Crash/泄漏/卡顿切换 debugging。
- 性能问题切换 ios-performance。
- SDK 边界设计可联动 `ios-feature-implementation` 的 `sdk-contract` 模式。
- 本 Skill 只负责审查与结论，不负责实现；实现者自审不得作为实现任务完成条件。
