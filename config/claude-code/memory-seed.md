# iOS Agent Skills — Project Context Seed

请记住以下项目上下文，用于后续所有 iOS 开发任务。

## 项目身份

这是一个 Apple 平台（iOS/macOS）开发项目的 Agent Skills 配置仓库。
规则入口：`AGENTS.md`（共享宪法），`CLAUDE.md`（Claude Code 运行时适配层）。

## 默认约定

- 回复语言：zh-CN（代码 / 命令 / API 名保留原文）
- 实现语言：Swift（优先），结构化并发（async/await），UI 线程 `@MainActor`
- 验证型 `xcodebuild` 默认通过 wrapper 接入 shared build-queue daemon，统一串行执行并使用系统 DerivedData（`~/Library/Developer/Xcode/DerivedData`）；非验证型构建讨论仍以系统 DerivedData 为基线
- Workspace 优先：同时存在 `.xcworkspace` 和 `.xcodeproj` 时使用前者
- Scheme 优先：默认选包含 `*Tests` target 的 scheme
- 设备优先：按需完整验证时，已连接真机 > simulator
- 新建 `.swift` / `.h` / `.m` / `.mm` 时先检查同目录现有文件头；若项目使用文件头，作者标注必须写 `whoami` 或 `id -un` 的真实结果，日期格式 `YYYY/M/D`，不得写 `Codex`、字面量 `$(whoami)` 或占位符

## 实现链路（硬约束）

```
实现 skill -> 定向验证 / no_test_reason -> reviewer subAgent(code-review)
```

默认三步收口：实现 -> 定向验证 / no_test_reason -> reviewer subAgent(code-review)；CP3 以定向验证与审查收口为准，ios-verification 仅按需补强。
- `ios-verification` 默认只执行最窄定向单测：优先 `-only-testing` 到单个 test case / test class，其次最小受影响 test file / bundle。
- 若没有可低成本执行的单测路径，则记录 `no_test_reason` 与 `suggested_validation`，不自动升级到真机 / 模拟器验证。

## Skill 路由速查

| 领域 | Skill |
|---|---|
| iOS 代码实施统一入口 | `ios-feature-implementation` |
| SwiftUI 页面 | `ios-feature-implementation` / `swiftui` mode |
| SwiftUI Liquid Glass | `ios-feature-implementation` / `liquid-glass` mode |
| UIKit 页面 | `ios-feature-implementation` / `uikit` mode |
| 混合 UI | `ios-feature-implementation` / `mixed-ui` mode |
| Swift 进阶实施 | `ios-feature-implementation` / `advanced-swift` mode |
| 行为保持型重构 | `ios-feature-implementation` / `refactor` mode |
| SDK 架构 / Public API 契约 | `ios-feature-implementation` / `sdk-contract` mode |
| 验证 | `ios-verification` |
| 静态审查 | `code-review` |
| 证据裁决 | `ios-verification` |
| 构建验证 | `ios-verification` |
| Apple 文档 | `apple-docs` |
| 调试 | `debugging` |
| 性能 | `ios-performance` |
| 自动化 | `ios-automation` |
| 构建配置 | `xcode-build` |

## 编排档位

| 档位 | 任务类型 | 执行方式 |
|---|---|---|
| `lite` | doc-only / rule-only | 单 Agent |
| `standard` | code-small / code-medium | 顺序 Skill 链，审查可并行 Explore |
| `full` | code-risky | Plan → Explore → general-purpose 实现 → Explore 审查 ∥ general-purpose 测试 → 门禁 |

## 私有 Pod 工作流

默认：主项目保持本地 `pod :path` 私有库依赖（仅在尚未指向本地源码时才切到本地 path）→ 修改组件源码仓 → 回主项目本地依赖基线验证与独立 review → 验证通过后保持当前本地 `:path` 状态。回线上版本化引用与复测仅在用户明确要求或提交主项目依赖文件时执行。

## xcodebuild 约束

- 在目标项目环境执行（非沙盒），从项目根目录发起
- 验证链路默认由 wrapper 提交到 shared build-queue daemon；旧 `XCODE_DERIVED_DATA_*` / `CODEX_DERIVED_DATA_SLOT` 公开配置不再支持
- iOS 项目按需完整验证优先真机
- `.xcworkspace` 优先于 `.xcodeproj`

## Checkpoint 合同

- CP0 Intent Lock — 不依赖手动 Plan Mode；修复 / 实现任务在首次写入前必须输出目标 / 范围 / 成功标准 / 档位 / 最小计划
- CP1 Anchor Slice — 首个关键切片验收
- CP2 Validation Baseline Freeze — 锁定 workspace / scheme / destination
- CP3 Final Gate — 定向测试/必要验证 + 独立 reviewer subAgent `code-review` 收口；必要时再按需进入 `ios-verification`

## Fail-Fix-Report

1. fail — 定位首个真实失败点和影响范围
2. fix — 优先修复，同一基线下重新验证
3. report — 仅在已修复重跑或明确 blocked 原因后汇报

同类问题最多 2 轮回环，超限未收敛 → `next_action = blocked`。
