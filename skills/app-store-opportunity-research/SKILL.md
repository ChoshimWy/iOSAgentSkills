---
name: app-store-opportunity-research
description: App Store 机会研究技能。用于在指定赛道中识别可商业化机会，完成竞品缺口分析、Top-3 机会排序与 MVP PRD 产出；可按需补充 Rork 原型提示词。
---

# App Store 机会研究 / App Store Opportunity Research

## Purpose

Research App Store opportunity spaces, rank candidate product opportunities with evidence, and produce a compact MVP-oriented recommendation.

## 中文说明

该 Skill 负责从“赛道选择”到“机会排序”再到“MVP PRD 落地”的研究链路。

## When to Use

- 用户想知道“现在做什么 iOS App 更有机会”。
- 需要在某个分类里找未被满足的真实需求。
- 需要基于竞品评分、评论、定价和用户抱怨做机会优先级判断。
- 需要输出可执行的 Top-3 机会报告与 MVP PRD。

## When Not to Use

- 需要保证营收结果、替代财务尽调、法务合规审查或商店上架执行时。
- 需要直接落地 iOS 业务代码实现时。

## Agent Rules

- Make all ranking logic evidence-backed and explicit about assumptions.
- Prefer comparable competitors and recurring complaint themes over anecdotal signals.
- Avoid fake precision in market sizing, revenue, or conversion estimates.
- Each recommended opportunity must include target user, gap, monetization path, implementation complexity, and main risk.
- Default deliverable is a compact Top-3 list plus one recommended pick.

## Inputs

```json
{
  "category": "optional",
  "target_users": [],
  "budget_constraints": [],
  "target_revenue_range": "optional",
  "need_prd": true
}
```

## Outputs

```json
{
  "status": "completed | partial | blocked",
  "top_opportunities": [],
  "recommended_pick": "...",
  "evidence_notes": [],
  "assumptions": [],
  "known_risks": [],
  "next_action": "write-prd | ask-user | app-store-changelog | blocked"
}
```

## Exit Conditions

- `completed`: top opportunities, recommendation, evidence, assumptions, and risks are explicit.
- `partial`: useful opportunity ranking exists but sampling or evidence depth is incomplete.
- `blocked`: research boundary is too unclear or evidence quality is too weak to recommend a direction.

## Escalation Rules

- Escalate to `app-store-changelog` when the task becomes release-note writing.
- Escalate to implementation Skills when the task becomes product delivery.
- Escalate to `xcode-build` when the task becomes build, signing, archive, export, or CI work.

## Token Budget

- Do not dump large competitor tables into the conversation.
- Prefer compact ranked findings, explicit assumptions, and one recommendation.
- Summarize only the evidence that changes prioritization.

## Relationship to Other Skills

- Use `app-store-changelog` for App Store release copy.
- Use implementation Skills for actual app delivery.
- Use `xcode-build` for build and release pipeline work.

