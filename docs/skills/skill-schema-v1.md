# Skill Schema v1

本规范定义 `iOSAgentSkills` 仓库内 Skill 的统一结构、状态枚举和输出合同。

## 适用范围

适用于：

- `skills/*/SKILL.md`
- 主链路 Skill
- 实现型 Skill
- 诊断型 Skill
- 验证型 Skill
- 自动化 Skill

## 标准章节

每个 Skill 推荐使用以下章节顺序：

```md
# Skill Name

## Purpose

## 中文说明

## When to Use

## When Not to Use

## Agent Rules

## Inputs

## Outputs

## Exit Conditions

## Escalation Rules

## Reporting Format

## Reference Resources

## Relationship to Other Skills
```

## 必须章节

所有 Skill 至少包含：

- `## Purpose`
- `## Agent Rules`
- `## Outputs`
- `## Exit Conditions`

主链路 Skill 还应包含：

- `## Inputs`
- `## Escalation Rules`
- `## Relationship to Other Skills`

## 状态枚举

### 通用状态

```json
[
  "completed",
  "partial",
  "blocked",
  "skipped"
]
```

### 验证状态

```json
[
  "passed",
  "failed",
  "skipped",
  "blocked"
]
```

### 证据门禁状态

```json
[
  "accepted",
  "escalated",
  "blocked"
]
```

### 调试状态

```json
[
  "diagnosed",
  "probable",
  "needs-more-evidence",
  "fixed",
  "blocked"
]
```

### 测试状态

```json
[
  "passed",
  "failed",
  "skipped",
  "blocked",
  "proposed"
]
```

## 通用输出合同

实现型 Skill 默认输出：

```json
{
  "status": "completed | partial | blocked",
  "changed_files": [],
  "summary": [],
  "contract_changes": [],
  "known_risks": [],
  "test_impact": "...",
  "no_test_reason": null,
  "next_action": "run-targeted-tests | code-review | ask-user | blocked"
}
```

测试型 Skill 默认输出：

```json
{
  "status": "passed | failed | skipped | blocked | proposed",
  "suggested_validation": [],
  "executed_validation": [],
  "affected_tests": [],
  "failure_attribution": "none | current_change | pre_existing | environment | unknown",
  "first_failure": null,
  "needs_test_code": "yes | no",
  "no_test_reason": null,
  "next_action": "code-review | ios-verification | blocked"
}
```

审查型 Skill 默认输出：

```json
{
  "blocking_findings": [],
  "non_blocking_findings": [],
  "review_scope": "...",
  "impact_scope": "...",
  "unreviewed_changes": "none",
  "verification_story": "accepted | needs-ios-verification | insufficient",
  "risk_level": "low | medium | high",
  "next_action": "complete | fix-and-rerun | blocked"
}
```

验证型 Skill 默认输出：

```json
{
  "status": "passed | failed | skipped | blocked",
  "verification_route": "...",
  "fingerprint": "...",
  "cached": false,
  "diagnostics_path": "...",
  "summary_path": "...",
  "first_blocking_error": null,
  "next_action": "none | fix_first_error | blocked"
}
```

证据门禁 Skill 默认输出：

```json
{
  "status": "accepted | escalated | blocked",
  "final_evidence_gate": "accepted_existing_evidence | needs_project_environment_verification | blocked_insufficient_evidence",
  "verification_story": "accepted | needs-ios-verification | insufficient",
  "accepted_evidence": [],
  "rejected_evidence": [],
  "escalation_reason": null,
  "required_next_skill": "none | ios-verification | code-review | xcode-build",
  "residual_risk": [],
  "next_action": "complete | run-ios-verification | collect-evidence | blocked"
}
```

## Token Budget 基线

所有 Skill 默认遵守：

- 不读取完整 `build.log`。
- 不读取完整 `.xcresult` dump。
- 不递归扫描 `DerivedData`。
- 不粘贴大段 diff。
- 不粘贴完整控制台日志。
- 优先读取脚本生成的 `verification-report.json`。
- 优先读取 `diagnostics.json`。
- 优先读取 `build-summary.txt` / `test-summary.json`。
- 优先输出结构化摘要。

## 验证链路基线

默认实现链路：

```text
implementation -> targeted validation / no_test_reason -> code-review
```

按需增强链路：

```text
code-review -> ios-verification(final-gate) -> ios-verification(execute)
```

构建失败归因：

```text
ios-verification(execute) -> ios-verification(digest)
```

## Commit Message 规范

后续提交统一使用中文 Conventional Commit，并标明代码来源：

```text
<type>(<scope>): [TAG] <subject>
```

`TAG` 只允许：

- `[Codex-GENERATED]`：完全由 AI Agent 自动化生成，没有人工代码。
- `[Codex-ASSIST]`：AI 辅助生成，人工参与决策或只生成部分代码。
- `[HUMAN]`：完全由人工编写。

示例：

```text
feat(Action Panel): [Codex-GENERATED] 增加Action Panel主页面UI
refactor(Cue): [Codex-ASSIST] Cue增量更新重构
fix(bug): [HUMAN] 修复ONES bug #xxxxx
```

## Lint 建议

`scripts/lint_skill_schema.py` 至少应检查：

- `## Purpose`
- `## Agent Rules`
- `## Outputs`
- `## Exit Conditions`

后续可扩展检查：

- 是否包含 `## Relationship to Other Skills`
- 是否包含状态枚举
- 是否包含低 token 规则
- 是否包含 `next_action`
