---
name: code-review
description: iOS/Swift 静态代码审查 Skill。用于 review diff、PR、SDK API 与实现质量；用于实现链路收口时必须由未参与实现的独立 reviewer subAgent 执行，避免同一 Agent 实现后自审；只输出基于代码和已知上下文的审查结论，不负责直接修复实现、运行时排障、性能取证或构建配置。
---

# 代码审查

## Purpose

Review iOS/macOS code changes, identify correctness and maintainability risks, evaluate verification sufficiency, and produce structured review findings with clear severity and ownership.

## 中文说明

该 Skill 是静态审查专项 Skill。

负责：
- 审查本次任务差异及直接影响面。
- 发现正确性、安全性、内存、并发、性能与可维护性问题。
- 审查 public/open API、SDK 接口与调用契约。
- 审查测试与验证故事是否成立。
- 输出结构化 Findings 和风险结论。

不负责：
- 直接修复代码。
- 运行时 crash、泄漏、卡顿定位。
- 性能 benchmark 或 Instruments。
- 构建系统、签名、Archive、CI 配置。

## When to Use

- 用户要求 review 代码、PR、diff。
- 实现任务进入 testing 之后的静态审查阶段；该场景必须由未参与实现的独立 reviewer subAgent 执行。
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
- 如果无法确认 reviewer 独立性或无法启动 reviewer subAgent，输出 `status: blocked`、`first_failure: reviewer subAgent unavailable`、`next_action: blocked`。
- 纯 review 请求也应由独立 reviewer subAgent 执行；如果平台无法启动 reviewer subAgent，必须说明审查独立性缺口。

### Evidence Rules

- Findings 必须优先输出。
- Findings 按严重等级排序。
- 无阻塞项时必须显式输出 `blocking_findings: []`。
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

### Validation Story Rules

必须检查：

- testing 是否发生在最后一次代码修改之后。
- executed_validation 是否覆盖目标 target。
- 是否需要升级到 final-evidence-gate。
- 是否需要升级到 verify-ios-build。

规则：

- 最窄定向单测已通过且风险较低时，不得仅因为没跑真机/模拟器就判定证据不足。
- 高风险工程、依赖、签名、资源、设备能力改动可要求升级验证。

### Private Dependency Rules

发现以下情况默认阻塞：

- 修改发生在 `Pods/<Library>`。
- 实际项目使用本地 `:path` Pod。
- 验证发生在 vendored snapshot 而非真实源码。

### Comment Rules

阻塞：

- public/open API 缺少必要文档注释。
- 并发边界语义缺失。
- 副作用语义缺失。
- 失败路径语义缺失。
- 注释与实现不一致。

非阻塞：

- 文案优化。
- 命名建议。
- 可读性建议。

### Token Budget

- 不读取完整 build.log。
- 不读取完整 xcresult dump。
- 不重复输出大段 diff。
- 优先让本地脚本或窄范围命令生成 review packet（scoped diff、changed files、关键符号、验证摘要），reviewer 只消费必要证据。
- Findings 优先于代码摘录。
- 输出应聚焦阻塞项与风险。

## Inputs

```json
{
  "review_base_ref": "optional",
  "changed_files": [],
  "diff_scope": "working-tree",
  "testing_result": {},
  "verification_result": {},
  "constraints": [],
  "reviewer_independence": "independent-subagent | pure-review | unavailable"
}
```

## Outputs

```json
{
  "status": "complete | blocked | partial",
  "blocking_findings": [],
  "non_blocking_findings": [],
  "review_scope": "...",
  "impact_scope": "...",
  "unreviewed_changes": "none",
  "first_failure": "none",
  "verification_story": "accepted | needs-final-evidence-gate | needs-verify-ios-build | insufficient",
  "risk_level": "low | medium | high",
  "reviewer_independence": "independent-subagent | pure-review | unavailable",
  "next_action": "fix-and-rerun | blocked | complete"
}
```

## Severity Format

### Blocking

```text
🔴 [File:Line]
Issue
Suggestion
```

### Non Blocking

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
- blocking_findings 为空。
- review_scope 明确。
- impact_scope 已覆盖。
- verification_story 已给出。

### blocked

- 实现链路收口审查无法确认独立 reviewer subAgent 或 reviewer subAgent 不可用。
- 存在 blocking_findings。
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

升级到 `verify-ios-build`：

- 高风险工程变更
- 证据明显不足
- 用户要求最终验证

升级到 `final-evidence-gate`：

- 需要裁决现有证据是否足够

升级到实现型 Skill：

- 已确认问题且需要修复

## Reporting Template

```text
blocking_findings:
  - ...

non_blocking_findings:
  - ...

review_scope:
  ...

impact_scope:
  ...

unreviewed_changes:
  none

first_failure:
  none

verification_story:
  accepted

reviewer_independence:
  independent-subagent

risk_level:
  low

next_action:
  complete
```

## Relationship to Other Skills

- 默认承接 testing 之后的第三步，且该第三步必须由独立 reviewer subAgent 执行。
- 修复问题时切换实现型 Skill。
- Crash/泄漏/卡顿切换 debugging。
- 性能问题切换 ios-performance。
- SDK 边界设计可联动 ios-sdk-architecture。
- 本 Skill 只负责审查与结论，不负责实现；实现者自审不得作为实现任务完成条件。
