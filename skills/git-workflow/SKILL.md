---
name: git-workflow
description: Git 工作流技能。当涉及 Git 操作、创建分支、编写 commit message、提交本次 git 更新、准备 PR 描述、处理 .gitignore 时使用。遵循 Conventional Commits 规范、标准分支命名、结构化 PR 描述模板。
---

# Git 工作流

## 分支命名
```
feature/<ticket-id>-<简短描述>     新功能
bugfix/<ticket-id>-<简短描述>      Bug 修复
hotfix/<ticket-id>-<简短描述>      紧急修复
release/<version>                  版本发布
refactor/<简短描述>                 重构
```
示例: `feature/SDK-123-user-auth`, `bugfix/SDK-456-token-refresh`

## Commit Message (Conventional Commits)
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 选择
| type | 用途 |
|------|------|
| feat | 新功能 |
| fix | Bug 修复 |
| refactor | 重构 |
| perf | 性能优化 |
| test | 测试 |
| docs | 文档 |
| style | 格式 |
| chore | 构建/工具/依赖 |
| ci | CI 配置 |

### 规则
- subject 中文，不加句号，≤72 字符
- body 解释 why 和 what changed
- footer 关联 issue: `Closes #123` 或 `Fixes SDK-456`

### 示例
```
feat(auth): 实现 OAuth 2.0 PKCE 流程

添加 PKCE code verifier 和 challenge 生成逻辑，
构建授权 URL 并实现 token 交换功能。

Closes SDK-123
```

## PR 描述模板
1. **概述** — 改了什么，为什么改
2. **变更类型** — Feature / Bugfix / Refactor / Perf
3. **改动详情** — 具体实现方案
4. **测试情况** — 通过了哪些测试
5. **影响范围** — 影响哪些模块/功能
6. **关联 Issue** — Closes #xxx

## .gitignore (iOS)
```
DerivedData/
*.xcuserdata/
*.ipa
*.dSYM.zip
.DS_Store
Pods/
.build/
fastlane/report.xml
```

## Git 操作行为准则
- 提交前检查 diff，确保没有调试代码或临时文件
- 不提交敏感信息 (token, key, password)
- 多个不相关变更拆成多个 commit

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: git-workflow`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel