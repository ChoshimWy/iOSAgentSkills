---
name: apple-docs
description: Apple 官方文档检索辅助技能。只在需要查询 Apple Developer Documentation、框架 API、平台可用性、WWDC 视频或示例工程时使用；不要把它当作默认主开发、重构、调试或构建技能。
metadata: {"clawdbot":{"emoji":"🍎","requires":{"bins":["node"]}}}
---

# Apple 官方文档检索

## Purpose

Retrieve Apple official documentation facts for APIs, platform availability, WWDC content, and sample-code references to support other Apple-platform Skills.

## 中文说明

该 Skill 是 Apple 官方文档检索辅助 Skill，只负责提供官方事实依据，不承担主实现或构建职责。

## When to Use

- 需要确认 Apple 官方 API 定义、可用性、废弃替代方案。
- 需要查询 SwiftUI、UIKit、Foundation、AppKit 等框架的官方说明。
- 需要追溯 WWDC 会话、示例工程或技术总览。
- 用户明确要求“查 Apple 官方文档”或需要最新官方依据时。

## When Not to Use

- 任务核心是写或改 iOS/macOS 业务代码时。
- 任务核心是运行时排障、重构、构建配置或测试编写时。

## Agent Rules

- Distinguish official documentation facts from inference.
- Always include platform and minimum OS version when availability matters.
- Prefer the narrowest query that answers the task.
- If official evidence is insufficient, state the gap explicitly instead of guessing.

## Inputs

```json
{
  "query": "required",
  "framework": "optional",
  "platform": "optional",
  "need_availability": true,
  "need_wwdc": false
}
```

## Outputs

```json
{
  "status": "completed | partial | blocked",
  "official_facts": [],
  "availability_notes": [],
  "wwdc_refs": [],
  "sample_code_refs": [],
  "known_gaps": [],
  "next_action": "implementation-skill | debugging | xcode-build | blocked"
}
```

## Exit Conditions

- `completed`: official facts and relevant availability notes are explicit.
- `partial`: some official evidence exists but important gaps remain.
- `blocked`: query cannot be resolved from available official sources in the current environment.

## Escalation Rules

- Escalate to implementation Skills when the next step becomes code changes.
- Escalate to `debugging` for runtime diagnosis.
- Escalate to `xcode-build` for build, signing, archive, or CI tasks.

## Token Budget

- Do not paste large doc bodies.
- Prefer short fact bullets, availability notes, and direct references.
- Only load detailed references when the task needs them.

## Relationship to Other Skills

- Use implementation Skills for actual code changes.
- Use `debugging` for runtime investigation.
- Use `xcode-build` for build and release setup.
- Use this Skill as supporting evidence for other Apple-platform Skills.

