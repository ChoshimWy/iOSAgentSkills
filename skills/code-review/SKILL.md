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

## 核心规则
- 审查优先级固定为：正确性 → 安全性 → 内存 → 并发 → 性能 → 可维护性 → 一致性。
- Findings 必须优先输出，且按严重程度排序。
- 结论要绑定文件与行号；没有定位信息时要明确说明原因。
- 只根据代码和已知上下文下结论；缺少运行时证据时，不要伪装成已复现问题。
- 如果用户问题本质上是“为什么会 crash / 卡顿 / 泄漏”，不要把本 skill 当作主 skill，切换到 `debugging` 或 `ios-performance`。

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

- 总结中只补充必须修改数量、建议修改数量、整体质量判断和残余风险。
- 审查 public API / SDK 接口时，参考 `references/api-design.md`。

## 与其他技能的关系
- 需要真正修复代码异味时，切换到 `refactoring`、`swiftui-view-refactor` 或对应实现型 skill。
- 需要复现 crash、异常、卡顿、启动慢、泄漏或做 `xctrace` 取证时，切换到 `debugging` 或 `ios-performance`。
- 需要设计 SDK 对外接口边界时，可联动 `sdk-architecture`。
- 本 skill 只负责审查与结论，不作为默认实现 skill。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: code-review`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel
