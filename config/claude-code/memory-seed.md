# iOS Agent Skills — Project Context Seed

请记住以下项目上下文，用于后续所有 iOS 开发任务。

## 项目身份

这是一个 Apple 平台（iOS/macOS）开发项目的 Agent Skills 配置仓库。
规则入口：`AGENTS.md`（共享宪法），`CLAUDE.md`（Claude Code 运行时适配层）。

## 默认约定

- 回复语言：zh-CN（代码 / 命令 / API 名保留原文）
- 实现语言：Swift（优先），结构化并发（async/await），UI 线程 `@MainActor`
- 构建缓存：系统 DerivedData（`~/Library/Developer/Xcode/DerivedData`），不指定 `-derivedDataPath`
- Workspace 优先：同时存在 `.xcworkspace` 和 `.xcodeproj` 时使用前者
- Scheme 优先：默认选包含 `*Tests` target 的 scheme
- 设备优先：已连接真机 > simulator（低风险改动可用 simulator）
- 作者标注：`Created by Choshim.Wei`，日期格式 `YYYY/M/D`

## 实现链路（硬约束）

```
实现 skill -> testing -> code-review -> final-evidence-gate
```

四步缺一不可。CP3 Final Gate 未通过不得宣告完成。

## Skill 路由速查

| 领域 | Skill |
|---|---|
| 通用业务实现 | `ios-feature-implementation` |
| SwiftUI 页面 | `swiftui-feature-implementation` |
| UIKit 页面 | `uikit-feature-implementation` |
| 测试 | `testing` |
| 静态审查 | `code-review` |
| 门禁裁决 | `final-evidence-gate` |
| 构建验证 | `verify-ios-build` |
| Apple 文档 | `apple-docs` |
| 调试 | `debugging` |
| 性能 | `ios-performance` |
| 自动化 | `ios-simulator-automation` / `ios-device-automation` |
| 构建配置 | `xcode-build` |

## 编排档位

| 档位 | 任务类型 | 执行方式 |
|---|---|---|
| `lite` | doc-only / rule-only | 单 Agent |
| `standard` | code-small / code-medium | 顺序 Skill 链，审查可并行 Explore |
| `full` | code-risky | Plan → Explore → general-purpose 实现 → Explore 审查 ∥ general-purpose 测试 → 门禁 |

## 私有 Pod 工作流

`pod :path` 本地调试 → 验证通过 → 推送 Pod → 主项目回线上引用 → 复测通过

## xcodebuild 约束

- 在目标项目环境执行（非沙盒），从项目根目录发起
- 不指定 `-derivedDataPath`，不使用 `XCODE_DERIVED_DATA`
- iOS 项目最终验证优先真机
- `.xcworkspace` 优先于 `.xcodeproj`

## Checkpoint 合同

- CP0 Intent Lock — Plan Mode 输出目标 / 范围 / 成功标准 / 档位
- CP1 Anchor Slice — 首个关键切片验收
- CP2 Validation Baseline Freeze — 锁定 workspace / scheme / destination
- CP3 Final Gate — `final-evidence-gate` 通过

## Fail-Fix-Report

1. fail — 定位首个真实失败点和影响范围
2. fix — 优先修复，同一基线下重新验证
3. report — 仅在已修复重跑或明确 blocked 原因后汇报

同类问题最多 2 轮回环，超限未收敛 → `next_action = blocked`。
