---
name: _shared-sentinel
description: 内部共享片段：用于验证其它 Skill 是否被加载的 Sentinel 规则。一般不应被单独触发。
---

# Sentinel Shared Snippet

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定“当前任务已经加载并正在使用某个 Skill”时：

- 在回复末尾追加一行：`// skill-used: <SKILL_NAME>`

规则：
- 只能追加一次
- `<SKILL_NAME>` 必须是当前正在生效的 skill 目录名（例如 ios-base / testing / performance）
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守对应 Skill 的硬性规则与交付格式

## ✅ Sentinel 结构签名（可选但推荐）
若任务属于工程交付类（写代码/改代码/设计方案），回复必须包含这些小节：
- Summary
- Files changed
- How to test
- Risks
- Rollback
