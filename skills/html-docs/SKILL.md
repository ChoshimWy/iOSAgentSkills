---
name: html-docs
description: HTML 文档规范与交付 Skill。作为正式 HTML 文档生成的统一入口，用于把方案、技术设计、PRD、工作流说明、评审稿、接口说明、运行记录、任务清单和 handoff 等内容整理为结构清晰、可分享、可归档且支持系统暗黑模式的 HTML 文档；不要用于 .docx/.pptx 办公文件处理、普通聊天答复或与文档交付无关的写作。
---

# HTML 文档规范

## Purpose

Create, organize, and maintain structured HTML documentation for iOS engineering plans, workflow specifications, technical designs, PRDs, review reports, and handoff documents.

## 中文说明

该 Skill 是文档规范与 HTML 交付专项 Skill。

负责：
- 技术方案 HTML 文档。
- PRD / 产品设计包 HTML 文档。
- 工作流、Agent 规范、构建验证规范文档。
- 接口说明、流程说明、评审稿、变更说明。
- 任务清单、运行报告、handoff 文档。
- 可归档、可分享、可浏览的正式文档页面。
- HTML 文档样式基线与暗黑模式适配。

不负责：
- `.docx` / Word 文件处理。
- `.pptx` / PowerPoint 文件处理。
- Excel / PDF 文件处理。
- 普通聊天中的短文案回复。

## When to Use

Use this Skill when:

- The user asks to generate an HTML document.
- The user asks for a document that should be shareable, archived, or reviewed.
- The output needs headings, table of contents, tables, code blocks, JSON examples, callouts, and responsive layout.
- The topic is iOS engineering workflow, technical design, PRD, review report, implementation plan, or process specification.
- Another Skill has produced a source packet, conclusion, evidence path, or checklist that must become a formal HTML document.

## When Not to Use

Do not use this Skill when:

- The user asks for `.docx`, Word, `.pptx`, PowerPoint, spreadsheet, or PDF editing.
- The user only needs a short plain text answer.
- The user needs source code implementation rather than documentation.
- The user needs App Store release copy only; use `app-store-changelog`.

## Agent Rules

### Document Structure Rules

- Use semantic HTML.
- Include a clear title.
- Include a table of contents for long documents.
- Use consistent heading hierarchy.
- Use tables for comparison, matrices, and structured decisions.
- Use code blocks for commands, JSON, Swift, shell, and config snippets.
- Use callout blocks for risks, decisions, assumptions, and next actions.
- Prefer responsive layout suitable for browser review.

### Content Rules

- Keep the document actionable.
- Separate background, goals, non-goals, architecture, workflow, implementation plan, validation, risks, and next steps.
- Do not mix unverified facts with decisions; label assumptions clearly.
- For engineering docs, include verification and rollback where relevant.
- For workflow docs, include trigger conditions, inputs, outputs, and exit conditions.

### Style Rules

- Default style should be clean, lightweight, and Notion-like.
- Avoid heavy visual effects.
- Use readable spacing, line height, and code block formatting.
- Do not inline huge logs or raw outputs.
- Prefer concise summaries and linked/attached artifacts where available.
- Generate a light-first visual baseline, but every HTML document must support system dark mode.
- Use CSS custom properties for color tokens, then override them in `@media (prefers-color-scheme: dark)`.
- Include `<meta name="color-scheme" content="light dark">` in `<head>`.
- Do not hard-code light-only text, table, code, or callout colors; reference semantic variables such as `--bg`, `--panel`, `--text`, `--muted`, `--border`, `--code-bg`, and `--callout-*`.
- Keep dark-mode contrast readable for body text, table borders, code blocks, links, chips, and checklist status marks.
- Read `references/dark-mode-style.md` before writing final CSS unless the caller provides an equivalent dark-mode stylesheet.

### Token Budget

- Do not paste large raw logs into the HTML.
- Summarize long data into tables or appendices.
- Keep examples representative, not exhaustive.
- Use collapsible sections only when helpful.

## Inputs

Expected input contract:

```json
{
  "goal": "Create HTML documentation",
  "document_type": "technical-design | prd | workflow | review | report | api-doc | handoff",
  "audience": "developer | product | reviewer | stakeholder | mixed",
  "source_material": [],
  "sections": [],
  "constraints": [],
  "theme_mode": "auto",
  "output_path": "optional"
}
```

## Outputs

Return compact structured output:

```json
{
  "status": "completed | partial | blocked",
  "document_type": "technical-design | prd | workflow | review | report | api-doc | handoff",
  "output_files": [],
  "summary": [],
  "sections": [],
  "dark_mode_support": "included | user-provided | blocked",
  "known_risks": [],
  "next_action": "review | publish | revise | blocked"
}
```

## Exit Conditions

Return `completed` when:

- HTML document is generated or fully specified.
- Required sections are included.
- Dark-mode behavior is included or an explicit reason for not including it is recorded.
- Output path or delivery format is clear.

Return `partial` when:

- Draft is useful but some source material, images, data, or decisions are missing.

Return `blocked` when:

- Required source material or output constraints are missing.
- The task actually requires a different artifact type such as `.docx`, `.pptx`, spreadsheet, or PDF editing.

## Escalation Rules

Escalate to implementation or workflow Skills when:

- The document reveals missing technical decisions that require code/workflow design.

Escalate to `app-store-changelog` when:

- The task is App Store release notes or user-facing update copy.

Escalate to `ui-ux-design-system` when:

- The task is primarily visual design system, typography, color, or accessibility guidance.

Escalate back to the source Skill when:

- The input lacks enough domain evidence, decisions, screenshots, validation artifacts, or review findings to produce a reliable formal document.

## Reporting Format

```text
HTML docs status: completed | partial | blocked
Document type: ...
Output files:
- ...
Sections:
- ...
Known risks:
- ...
Next action: review | publish | revise | blocked
```

## Reference Resources

- `references/template-overview.md`: shared HTML skeleton and style baseline.
- `references/dark-mode-style.md`: required color-token and `prefers-color-scheme` baseline for dark-mode support.
- `references/plan-template.md`: proposal / technical-design template.
- `references/tasklist-template.md`: task checklist / PR checklist template.
- `references/review-template.md`: review / analysis report template.
- `references/interface-template.md`: API / interface documentation template.

## Relationship to Other Skills

- iOS workflow docs can summarize outputs from `codex-subagent-orchestration`, `ios-verification`, `code-review`, `ios-feature-implementation`, and related Skills.
- App Store release notes route to `app-store-changelog`.
- Visual design guidance routes to `ui-ux-design-system`.
- Code implementation routes to iOS implementation Skills.
- Other Skills should route formal HTML doc generation here after producing source packets, conclusions, evidence paths, and risks.
