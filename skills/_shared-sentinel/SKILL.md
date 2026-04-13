---
name: _shared-sentinel
description: 内部共享片段：用于验证其它 Skill 是否被加载的 Sentinel 规则。一般不应被单独触发。
---

# Shared Sentinel Snippet

本 skill 用于为其它业务 skill 提供统一的 sentinel 说明片段。

## 使用规则
- 只有在你确定某个业务 skill 已经被加载并正在用于当前任务时，才输出该 skill 对应的 sentinel。
- sentinel 必须与当前生效的 skill 目录名完全一致。
- 每次回复最多输出一次 sentinel。
- 如果不确定是否已加载对应 skill，禁止输出 sentinel。

## 命名约束
- `<SKILL_NAME>` 必须是当前正在生效的 skill 目录名（例如 `ios-feature-implementation`、`testing`、`ios-performance`）。
- 推荐统一格式：`// skill-used: <SKILL_NAME>`
