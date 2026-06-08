---
name: swiftui-feature-implementation
description: SwiftUI 页面统一入口。覆盖三种子模式：1) 模式选型 — 新页面结构、导航层级、状态归属和组件拆分方案选择；2) 常规实现 — 在既定架构下落地 SwiftUI 页面、组件、列表、表单、状态绑定与界面交互；3) 视图重构 — 已有 SwiftUI 文件的结构化整理，抽离子视图、MV 优先数据流、稳定视图树。如果任务核心是 Liquid Glass 专项、性能取证或官方文档检索，不要使用本 skill 作为主 skill；若任务产出修改了 Apple Xcode 项目相关内容，默认以定向测试/必要验证与 `code-review` 放行为收口；`final-evidence-gate` / `verify-ios-build` 仅在用户显式要求或需要补强完整项目环境证据时按需使用。
---

# SwiftUI Feature 实现

## 角色定位

SwiftUI 页面开发统一入口，根据任务阶段自动选择子模式。不负责 Liquid Glass 专项、性能 profiling 或 Apple 文档事实查询。

## 子模式选择

首次判断后，后续链路固定在对应子模式：

| 子模式 | 触发条件 |
|---|---|
| **模式选型** | 用户在问"新页面该怎么组织 / NavigationStack / sheet / 组件拆分 / 状态放哪" |
| **常规实现** | 页面结构、路由和状态归属已明确，只差 SwiftUI 代码落地 |
| **视图重构** | 已有现成的 SwiftUI 文件，`body` 过长、子视图混乱、副作用堆在视图里或状态错位 |

## 模式选型工作流

1. 判断页面类型（`TabView` / `NavigationStack` / `sheet` / `List` / `Grid`）
2. 决定状态归属与路由结构
3. 从 `references/components-index.md` 进入对应组件参考

## 常规实现工作流

1. 接入现有 view model、service 或 router
2. 把业务状态绑定到 SwiftUI 视图
3. 编写动画、过渡、组件组合与预览代码

## 视图重构工作流

1. 理顺视图结构顺序
2. 抽离 `body` 内动作和副作用
3. 拆独立子视图，稳定根视图结构
4. 仅在现有代码明确要求时保留或调整 view model

## 核心规则

- iOS 17+ 默认优先 `@Observable`、`@State`、`@Bindable` 与显式依赖注入
- 保持根视图结构稳定，避免在 `body` 中堆叠副作用和复杂分支
- 只把 UI 状态留在 View；业务逻辑放回 `ios-feature-implementation` 管理的类型中
- 对 `public`/`open` API、跨模块复用类型要求 `///` 文档注释
- 并发边界、副作用、失败路径语义必须写清注释
- 复杂分支补 `why` 注释，不重复代码字面含义
- 新建 `.swift` 文件且项目要求文件头时，`Created by` 必须使用本机用户名称（`whoami` 输出）；日期 `YYYY/M/D`

## 参考资源

- `references/components-index.md` — 组件索引入口
- `references/swiftui.md` — SwiftUI 通用指南
- `references/app-wiring.md` — 应用接线
- `references/async-state.md` — 异步状态
- `references/navigationstack.md` — 导航栈
- `references/sheets.md` — Sheet 模式
- `references/previews.md` — 预览
- `references/mv-patterns.md` — MV 模式（重构专用）

## 可选证据验证

- 如果当前任务没有进入 `codex-subagent-orchestration`（CC 用户参考 CLAUDE.md 三步收口工作流），或当前轮只能以单 Agent 执行，本 skill 完成实现后也不要直接跳到可选验证；默认后续链路按三步执行：`swiftui-feature-implementation -> testing/定向验证 -> code-review`
- 只要当前任务产出修改了 Apple Xcode 项目相关内容，默认以定向测试/必要验证与 `code-review` 放行为收口；`final-evidence-gate` / `verify-ios-build` 仅按需使用
- 若执行可选完整验证，证据必须来自目标项目根目录的项目环境
- 对 iOS 项目，若升级到 `verify-ios-build`，必须优先 `.xcworkspace`，并默认优先已连接真机
- 若可选 `final-evidence-gate` / `verify-ios-build` 未执行或失败，应说明已执行的定向测试/审查证据与残余风险。

## 与其他技能的关系

- Liquid Glass 专项：`swiftui-liquid-glass`
- 性能 profiling / 掉帧 / 重绘：`ios-performance`
- 通用代码异味（非 SwiftUI 专项）：`refactoring`
- 业务层类型、service、导航 wiring：`ios-feature-implementation`
- UIKit 页面：`uikit-feature-implementation`
- 视觉设计系统、色板、无障碍：`ui-ux-design-system`
