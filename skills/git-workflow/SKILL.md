---
name: git-workflow
description: Git 通用工作流技能。用于分支命名、commit message、PR 描述模板、`.gitignore` 和常规 Git 操作规范；不负责使用 GitHub CLI（`gh`）一条龙执行提审流程，该场景交给 `gh-pr-flow`。
---

# Git 工作流

## 角色定位
- 默认型辅助 skill。
- 负责通用 Git 规范和提交文案质量。
- 不负责显式执行 `gh` 提审流程。

## 适用场景
- 需要创建或规范分支名。
- 需要编写 Conventional Commit。
- 需要整理 PR 描述模板或 `.gitignore`。
- 需要在不依赖 `gh` 的前提下执行常规 Git 操作。

## 核心规则
- 分支命名默认使用：

```text
feature/<ticket-id>-<简短描述>
bugfix/<ticket-id>-<简短描述>
hotfix/<ticket-id>-<简短描述>
release/<version>
refactor/<简短描述>
```

- Commit 使用 Conventional Commits：

```text
<type>(<scope>): <subject>
```

- `subject` 中文、不加句号、长度不超过 72 字符。
- 多行 commit 内容使用多个 `-m` 参数，不在单个字符串里写 `\n`。
- 提交前检查 diff，避免调试代码、临时文件和敏感信息。

## 输出要求
- 默认给出 branch、commit 和 PR 描述建议。
- 需要 PR 模板时，至少覆盖：概述、变更类型、改动详情、测试情况、影响范围、关联 Issue。
- iOS 仓库应明确忽略：`DerivedData/`、`*.xcuserdata/`、`.DS_Store`、`Pods/`、`.build/` 等常见噪音。

## 与其他技能的关系
- 如果只是规范 Git 操作和文本，优先使用本技能。
- 如果用户明确要求用 `gh` 完成暂存、提交、推送和开 PR，切换到 `gh-pr-flow`。
- 如果任务主目标是代码评审、重构或调试，本技能只作为收尾辅助技能使用。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: git-workflow`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel
