# Skill 重构审计报告

更新日期：2026-06-16

## 目标

本报告用于记录 `iOSAgentSkills` 仓库内 Skill 结构统一进度，避免无差别重构造成职责漂移。

统一目标：

- 所有 Skill 至少包含 `Purpose`、`Agent Rules`、`Outputs`、`Exit Conditions`。
- 主链路 Skill 需要补齐 `Inputs`、`Escalation Rules`、`Relationship to Other Skills`。
- 项目固化 Skill 不写流程编排，只固化目标项目内的功能关联、当前实现方式、依赖边界与维护约束；流程继续由通用规则和通用 Skill 承接。
- 输出合同尽量结构化，便于 Codex / Claude Code / 多 Agent / build-queue daemon 复用。
- 默认遵守低 token 规则：摘要优先、diagnostics 优先、禁止默认读取大日志。

## 已完成重构

| Skill | 状态 | 说明 |
| --- | --- | --- |
| `codex-subagent-orchestration` | ✅ 已完成 | 已统一主编排结构，并将验证相关路由收敛到 `ios-verification`。 |
| `ios-feature-implementation` | ✅ 已完成 | 已整合为唯一 iOS 生产代码与测试代码实施入口，内部覆盖 business / swiftui / liquid-glass / uikit / mixed-ui / advanced-swift / refactor / sdk-contract / test-implementation。 |
| `ios-verification` | ✅ 已完成 | 已整合验证前路由、受影响测试选择、定向验证执行、项目环境验证、构建失败摘要和最终证据裁决。 |
| `code-review` | ✅ 已完成 | 已统一审查结构，补齐 review_scope、impact_scope、verification_story。 |
| `debugging` | ✅ 已完成 | 已统一运行时排障结构，补齐 symptom、evidence、confidence、validation_plan。 |
| `ios-performance` | ✅ 已完成 | 已补齐结构化性能分析合同和升级边界。 |
| `xcode-build` | ✅ 已完成 | 已明确 Build Settings / 签名 / Archive / CI 与 `ios-verification` 的边界。 |
| `ios-automation` | ✅ 已完成 | 已明确设备自动化与默认验证收口的边界。 |
| 旧 iOS 实施专项 Skills | ✅ 已移除 | SwiftUI、UIKit、Swift 进阶、重构、SDK 架构与 Liquid Glass 的 standalone Skill 已物理删除。 |
| 旧验证专项 Skills | ✅ 已移除 | 原分散验证 Skill 已并入 `ios-verification`，脚本与 references 已迁移。 |
| `app-store-changelog` | ✅ 已完成 | 已补齐轻量发布文案 Skill 结构与输出合同。 |
| `app-store-opportunity-research` | ✅ 已完成 | 已补齐研究型 Skill 结构与输出合同。 |
| `apple-docs` | ✅ 已完成 | 已补齐官方文档检索 Skill 结构与事实边界。 |
| `git-workflow` | ✅ 已完成 | 已补齐 Git 辅助 Skill 结构与输出合同。 |

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
  "verification_story": "accepted | needs-ios-verification | needs-ios-verification | insufficient",
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
2. 持续清理冗余残留，避免已整合进 `ios-feature-implementation` 的旧实现入口重新出现。
3. 执行 `scripts/lint_skill_schema.py` 与 `--strict` 做全量结构检查。
4. 若后续需要，再针对非主链路辅助 Skill 做进一步减重；项目固化 Skill 只保留功能关联和当前实现方式，不引入流程规则副本。
