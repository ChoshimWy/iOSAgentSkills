---
name: code-review
description: iOS/Swift 代码审查技能。只在需要 review 代码、审查 PR diff、检查代码质量或评审 public API 设计时使用；它只输出基于静态代码证据的审查结论，不承担直接修复实现、运行时排障、性能 profiling 或构建配置。
---

# 代码审查

## 角色定位
- 诊断型 skill。
- 负责发现 bug、回归风险、设计缺陷、并发与性能问题，并给出分级审查结论。
- 不负责直接实现修复，也不替代运行时调试或构建系统配置。

## 适用场景
- 用户明确要求 review 代码、审查 diff、做 PR 评审。
- 需要对 public API 或 SDK 接口做设计层面的可维护性评估。
- 需要在合入前发现正确性、安全性、内存、并发和性能风险。
- 非编排 / 单 Agent 的实现型任务进入默认三步链路时，作为 `testing/定向验证` 之后的第三步静态审查阶段。

## 核心规则
- 审查优先级固定为：正确性 → 安全性 → 内存 → 并发 → 性能 → 可维护性 → 一致性。
- Findings 必须优先输出，且按严重程度排序。
- 结论要绑定文件与行号；没有定位信息时要明确说明原因。
- 只根据代码和已知上下文下结论；缺少运行时证据时，不要伪装成已复现问题。
- 注释审查默认纳入阻塞判定：重点检查 `public/open` API 文档注释、并发边界语义、副作用语义、失败路径语义和“注释-实现一致性”。
- 在默认三步链路里，默认审查对象是 **本次任务全量差异 + 本次修改带来的直接影响面**；差异范围包含 staged、unstaged、untracked，以及任务起点基线之后的所有相关提交。
- 主 Agent / reviewer 应优先使用任务起点基线（如 `review_base_ref`、开始任务前的 `HEAD`、PR base 或用户指定 ref）审查 `review_base_ref -> 当前工作区`；如果无法确认基线，默认 fallback 为当前 `HEAD`，但必须在 `review_scope` 中说明。
- 影响面审查必须覆盖本次修改直接触达的 public API、调用方、数据契约、并发边界、持久化 / 网络 / 缓存副作用、以及验证故事；无法确认或未覆盖的部分必须写入 `unreviewed_changes`。
- 如果发现变更直接落在 `Pods/<LibraryName>`，且上下文显示目标工程使用私有 Pod / 本地 `:path` Pod 联调，默认作为 `blocking_findings`：这通常意味着改错了源码位置。
- 如果本次修改涉及私有库 / 私有组件，必须审查验证故事是否在主项目切回或保持本地 `:path` 私有库依赖后完成；未收到明确指令却使用线上版本化依赖或 `Pods/` vendored snapshot 验证，默认视为验证基线不成立。
- 如果用户问题本质上是“为什么会 crash / 卡顿 / 泄漏”，不要把本 skill 当作主 skill，切换到 `debugging` 或 `ios-performance`。
- 固定链路中必须审查验证故事：`testing` 的 `executed_validation` 是否发生在最后一次代码变更之后，是否覆盖最终交付 target / consumer app scheme，以及是否需要升级 `verify-ios-build`。

## 注释相关阻塞判定（审查口径）
- 以下情况默认进入 `blocking_findings`（🔴）：
  - `public` / `open` API、跨模块复用接口或可复用协议要求缺失必要 `///` 文档注释；
  - 涉及并发边界（`@MainActor` / actor / 回调线程）、关键副作用（状态/DB/缓存/磁盘/网络）或失败路径（throws/错误码/回退条件）的实现，注释语义缺失；
  - 注释与实现冲突、明显过期或会误导调用方。
- 以下情况默认进入 `non_blocking_findings`（🟡）：
  - 措辞统一性、行文精炼度、可读性优化等不影响正确性与调用契约理解的问题。
- “只补文件头注释”不视为满足注释规范；关键函数与关键分支必须有可执行语义注释。

## 输出要求
- 使用以下分级格式：

```text
🔴 [文件:行号] 问题描述
   建议: 修改方案
```

```text
🟡 [文件:行号] 问题描述
   建议: 改进方案
   原因: 为什么这样更好
```

```text
✅ [文件:行号] 这段代码的优点
```

- 默认采用以下结构化汇报字段，便于主 Agent 聚合与回写：

```text
blocking_findings:
  - ...
non_blocking_findings:
  - ...
review_scope: <base/ref/working-tree 与纳入审查的 staged/unstaged/untracked/提交范围>
impact_scope: <已审查的直接影响面>
unreviewed_changes: <none|无法纳入审查的差异或影响面>
first_failure: <none|首个真实失败点>
verification_story: <accepted|needs-final-evidence-gate|needs-verify-ios-build|insufficient>
next_action: <fix-and-rerun|blocked|complete>
```

- 字段规则：
  - `blocking_findings` 只放真实阻塞项；无阻塞时必须写 `blocking_findings: []`。
  - `review_scope` 必须说明本次审查使用的基线、差异范围，以及 staged / unstaged / untracked 是否已纳入；不能只写“看过代码”。
  - `impact_scope` 必须说明已检查的直接调用方、契约边界和副作用边界；若没有额外影响面，写 `none` 并说明依据。
  - `unreviewed_changes` 无遗漏时写 `none`；存在未审查文件、未确认基线或未覆盖影响面时必须列出，并影响 `verification_story`。
  - `first_failure` 只写首个真实阻塞点；无阻塞时写 `none`。
  - 存在阻塞项时，`next_action` 不能是 `complete`。
  - `verification_story` 必须说明已有验证是否足够；证据不足或高风险时应标记 `needs-verify-ios-build`。
- 总结中只补充必须修改数量、建议修改数量、整体质量判断和残余风险。
- 审查 public API / SDK 接口时，参考 `references/api-design.md`。
- 输出 `blocking_findings` 时，优先把“注释导致的调用契约误判风险”放在首个真实阻塞点。

## 与其他技能的关系
- 如果当前任务属于非编排 / 单 Agent 的实现链路，本 skill 默认承接 `testing` 之后的第三步；默认审查本次任务全量差异与直接影响面，存在 blocking findings 时不得按默认标准收口；无阻塞时仍需给出审查范围、影响面与验证故事结论。
- 需要真正修复代码异味时，切换到 `refactoring`、`swiftui-feature-implementation` 或对应实现型 skill。
- 需要复现 crash、异常、卡顿、启动慢、泄漏或做 `xctrace` 取证时，切换到 `debugging` 或 `ios-performance`。
- 需要设计 SDK 对外接口边界时，可联动 `sdk-architecture`。
- 本 skill 只负责审查与结论，不作为默认实现 skill。
