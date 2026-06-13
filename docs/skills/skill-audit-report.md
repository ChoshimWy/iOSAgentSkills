# Skill 重构审计报告

更新日期：2026-06-13

## 目标

本报告用于记录 `iOSAgentSkills` 仓库内 Skill 结构统一进度，避免无差别重构造成职责漂移。

统一目标：

- 所有 Skill 至少包含 `Purpose`、`Agent Rules`、`Outputs`、`Exit Conditions`。
- 主链路 Skill 需要补齐 `Inputs`、`Escalation Rules`、`Relationship to Other Skills`。
- 输出合同尽量结构化，便于 Codex / Claude Code / 多 Agent / build-queue daemon 复用。
- 默认遵守低 token 规则：摘要优先、diagnostics 优先、禁止默认读取大日志。

## 已完成重构

| Skill | 状态 | 说明 |
| --- | --- | --- |
| `codex-subagent-orchestration` | ✅ 已完成 | 已统一主编排结构，补齐 Outputs / Exit Conditions / Escalation Rules，并接入低 token 验证链路。 |
| `verify-ios-build` | ✅ 已完成 | 已统一项目环境构建验证结构，补齐 fingerprint、diagnostics、低 token 输出合同。 |
| `testing` | ✅ 已完成 | 已统一测试结构，补齐 affected tests、no_test_reason、failure_attribution。 |
| `code-review` | ✅ 已完成 | 已统一审查结构，补齐 review_scope、impact_scope、verification_story。 |
| `debugging` | ✅ 已完成 | 已统一运行时排障结构，补齐 symptom、evidence、confidence、validation_plan。 |
| `ios-verification-router` | ✅ 新增完成 | 低 token 验证前置路由。 |
| `ios-affected-tests` | ✅ 新增完成 | 受影响测试选择与 `-only-testing` 输出。 |
| `ios-build-log-digest` | ✅ 新增完成 | 构建失败摘要分析，禁止默认读取 raw log。 |

## P1 待重构

| Skill | 优先级 | 原因 |
| --- | --- | --- |
| `xcode-build` | P1 | 直接影响 Build Settings、签名、Archive、Export、CI、destination 策略，需与 `verify-ios-build` 边界明确。 |
| `ios-automation` | P1 | 直接影响 simulator / 真机自动化、安装、启动、截图和 accessibility tree，需要与 `testing`、`verify-ios-build` 分离。 |
| `final-evidence-gate` | P1 | 证据裁决节点，需统一 verification_story 与升级条件。 |

## P2 待重构

| Skill | 优先级 | 原因 |
| --- | --- | --- |
| `ios-feature-implementation` | P2 | 业务实现主 Skill，需统一实现输出与验证交接。 |
| `swiftui-feature-implementation` | P2 | SwiftUI 专项实现，需统一与性能 / review / testing 的交接。 |
| `uikit-feature-implementation` | P2 | UIKit 专项实现，需统一页面实现输出合同。 |
| `swift-expert` | P2 | 进阶 Swift 设计 Skill，需明确何时转实现 / review / performance。 |

## P3 待重构

| Skill | 优先级 | 原因 |
| --- | --- | --- |
| `ios-performance` | P3 | 需与 `debugging` 区分，但可在 xcode-build / automation 后处理。 |
| `refactoring` | P3 | 与实现型 Skill 边界相关，风险较低。 |
| `sdk-architecture` | P3 | 架构专项，适合后续统一 Contract。 |
| `apple-docs` | P3 | 官方文档检索型，主要需要输出合同和引用规则。 |

## 统一 Contract 基线

所有 Skill 建议遵循：

```json
{
  "status": "completed | failed | skipped | blocked | partial",
  "summary": "...",
  "changed_files": [],
  "validation": {},
  "known_risks": [],
  "next_action": "none | fix | review | test | verify | blocked"
}
```

审查型 Skill 建议使用：

```json
{
  "blocking_findings": [],
  "non_blocking_findings": [],
  "review_scope": "...",
  "impact_scope": "...",
  "verification_story": "accepted | needs-final-evidence-gate | needs-verify-ios-build | insufficient",
  "next_action": "complete | fix-and-rerun | blocked"
}
```

验证型 Skill 建议使用：

```json
{
  "status": "passed | failed | skipped | blocked",
  "verification_route": "...",
  "fingerprint": "...",
  "diagnostics_path": "...",
  "summary_path": "...",
  "first_blocking_error": null,
  "next_action": "none | fix_first_error | blocked"
}
```

## 下一步顺序

1. 重构 `xcode-build`。
2. 重构 `ios-automation`。
3. 重构 `final-evidence-gate`。
4. 执行 `scripts/lint_skill_schema.py` 对已重构 Skill 做结构检查。
5. 再进入 P2 实现型 Skill。