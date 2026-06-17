# Skill 统一结构规范

适用于本仓库所有 Skill。

## 目标

- 统一 Codex / Claude Code Skill 结构。
- 降低上下文消耗。
- 提高多 Agent 协作稳定性。
- 统一输入输出合同（Contract）。

## 推荐结构

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

## Examples
```

## 必须项

每个 Skill 至少包含：

- Purpose
- Agent Rules
- Outputs
- Exit Conditions

缺失以上任意项视为结构不完整。

## 项目固化 Skill

项目固化 Skill 只记录目标项目事实，不承接流程编排：

- 写功能关联：模块、页面、服务、脚本、配置、资源、数据流与状态流如何连接。
- 写当前实现方式：关键入口、依赖边界、兼容约束、已验证的约定与维护禁区。
- 不写流程相关内容：不要复制 checkpoint、fail-fix-report、多 Agent 分工、验证升级链路或通用收口规则。
- 需要执行实现、验证、审查、构建、调试或性能分析时，只写“关联到哪个通用 Skill”，不要在项目 Skill 里重写该 Skill 的流程。

## Output Contract

所有 Skill 应尽量输出结构化结果。

例如：

```json
{
  "status": "success",
  "summary": "...",
  "next_action": "..."
}
```

## Token Budget 规则

所有 Skill 默认遵守：

- 禁止读取完整 build.log
- 禁止递归扫描 DerivedData
- 禁止读取完整 xcresult dump
- 优先读取 verification-report.json，再按需读取 diagnostics.json
- 优先返回摘要而非原始日志

## Commit Message 规范

统一使用中文 Conventional Commit 风格，并标明代码来源：

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
