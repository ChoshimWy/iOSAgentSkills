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
| `ios-verification-router` | ✅ 已完成 | 已补齐 Inputs / Outputs / Exit Conditions，并保持低 token 验证前置路由职责。 |
| `ios-affected-tests` | ✅ 已完成 | 已补齐结构化输出合同、退出条件和关系说明。 |
| `ios-build-log-digest` | ✅ 已完成 | 已补齐摘要分析输出合同、升级规则和低 token 约束。 |
| `gh-pr-flow` | ✅ 已完成 | 已从执行清单式文档统一为正式发布交付 Skill。 |
| `ios-performance` | ✅ 已完成 | 已补齐结构化性能分析合同和升级边界。 |
| `refactoring` | ✅ 已完成 | 已补齐通用重构合同、退出条件和交接关系。 |
| `swiftui-liquid-glass` | ✅ 已完成 | 已补齐 Liquid Glass 专项实现 / 审查结构。 |
| `app-store-changelog` | ✅ 已完成 | 已补齐轻量发布文案 Skill 结构与输出合同。 |
| `app-store-opportunity-research` | ✅ 已完成 | 已补齐研究型 Skill 结构与输出合同。 |
| `apple-docs` | ✅ 已完成 | 已补齐官方文档检索 Skill 结构与事实边界。 |
| `git-workflow` | ✅ 已完成 | 已补齐 Git 辅助 Skill 结构与输出合同。 |

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
| `app-store-changelog` | P3 | 非 iOS 主链路辅助 Skill，后续只需按需精简文风。 |
| `app-store-opportunity-research` | P3 | 研究型辅助 Skill，后续只需按需压缩上下文负担。 |
| `git-workflow` | P3 | 辅助型 Git Skill，后续可再细化与 `gh-pr-flow` 的边界。 |

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

1. 继续轻量复审已通过的主链路 Skill，重点看主流程一致性而不是重写结构。
2. 清理冗余残留，如已被 `ios-sdk-architecture` 取代的 `sdk-architecture` 孤儿目录与旧引用。
3. 执行 `scripts/lint_skill_schema.py` 与 `--strict` 做全量结构检查。
4. 若后续需要，再针对非主链路辅助 Skill 做进一步减重。
