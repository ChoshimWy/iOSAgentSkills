# 业务 Skill 分类索引

本文只覆盖业务 skill，不包含 `skills/.system/` 与 `skills/_shared-sentinel/`。

## 分类原则
- `Core Implementation`：默认优先触发的通用实现技能。
- `Specialized Implementation`：面向特定技术栈、架构形态或 UI 任务的专项实现技能。
- `Automation / Build / Validation`：自动化执行、构建配置与收尾验收技能。
- `Diagnostics`：发现问题、分析风险、定位根因的技能。
- `Research / Design / Release`：资料检索、设计方向、发布文案与机会研究技能。
- `Document / Productivity`：Office 文件类技能，处理 `.docx` / `.pptx` 等实际文档文件。
- `Platform / Legacy`：平台专项或历史兼容入口。

## 严格路由总则
在进入具体 skill 选择之前，先应用一个全局完成条件：

- **只要任务产出修改了 Apple Xcode 项目相关内容，最终都必须切到 `verify-ios-build` 做收尾门禁。**
- 最终门禁必须在目标项目根目录的项目环境执行，而不是把沙箱内构建结果当作最终结论。
- iOS 项目如果同时存在 `.xcworkspace` 与 `.xcodeproj`，门禁必须优先 `.xcworkspace`；默认优先已连接真机，找不到连接中的真机时再回退到 simulator。
- 如果没有用户显式指定 scheme，定向测试与最终门禁默认优先选择绑定了单元测试 `*Tests` target / bundle 的 scheme；若不存在，再回退到其它测试 scheme（例如 `*UITests`、`*_TEST`）。
- 在 `verify-ios-build` 成功前，任何技能都不能把任务表述为“已完成”。
- 默认优先切到 `codex-subagent-orchestration` 做自适应编排：先按 `lite` / `standard` / `full` 选择角色，再协调编码、审查、测试与最终门禁；如果当前运行时或上层策略要求显式授权 subAgent，而用户尚未授权，则临时回退到单 Agent。
- 如果当前任务未进入 `codex-subagent-orchestration`，或当前轮只能以单 Agent 执行，实现型任务默认也按固定四步收口：`实现 skill -> code-review -> testing -> verify-ios-build`；不要因为没有 subAgent 就跳过代码审查或测试阶段。
- 在多 Agent 流程中，Apple API / availability / WWDC 问题优先切 `apple-docs` 并使用 `appleDeveloperDocs`；构建、测试、simulator、真机、截图与日志优先切 `ios-device-automation`、`ios-simulator-automation`、`xcode-build` 或 `verify-ios-build`，不要用无关工具替代。

先按下面 3 组问题做一次硬判定，再选 skill：

1. **先看设备 / 构建维度**
   - Simulator 自动化、语义导航、`simctl`：`ios-simulator-automation`
   - 连接中的真机构建、安装、启动、`devicectl`：`ios-device-automation`
   - Build Settings、签名、Archive/Export、CI/CD：`xcode-build`
   - 任务收尾的一次性门禁构建：`verify-ios-build`
2. **再看 UI 技术栈与页面阶段**
   - 通用业务层与导航接线：`ios-feature-implementation`
   - 新建 SwiftUI 页面 / 模式选型：`swiftui-ui-patterns`
   - 已有模式下的普通 SwiftUI 落地：`swiftui-feature-implementation`
   - 已有模式下的普通 UIKit 落地：`uikit-feature-implementation`
   - 已有大 SwiftUI 文件整理：`swiftui-view-refactor`
   - iOS 26+ Liquid Glass API：`swiftui-liquid-glass`
   - 视觉方向 / 设计系统 / 色板 / 字体：`ui-ux-design-system`
3. **最后看问题类型**
   - 静态代码审查 / diff review：`code-review`
   - crash / 异常 / 运行时根因：`debugging`
   - 掉帧 / 启动慢 / `measure(metrics:)` / `xctrace`：`ios-performance`
   - 补测试代码 / Mock / Stub / Spy：`testing`

## 命名迁移

| 旧 skill | 新 skill | 说明 |
| --- | --- | --- |
| `ios-base` | `ios-feature-implementation` | 默认 iOS 实现 skill 拆分重构；通用业务实现由新主名承接。 |
| `ios-simulator-skill` | `ios-simulator-automation` | 名称改为表达更清晰的 Simulator 自动化能力。 |
| `ui-ux-pro-max` | `ui-ux-design-system` | 名称改为更清晰的设计系统与 UI/UX 方向表达。 |
| `swiftui-performance-audit` | `ios-performance` | SwiftUI 性能专项并入统一的 iOS 性能分析与测试 skill；旧名仅保留兼容入口。 |

## Core Implementation

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `ios-feature-implementation` | 默认 iOS feature 实现技能 | service / repository / use case / view model / 导航接线 / async 流程 | UIKit/SwiftUI 专项页面实现、构建配置、自动化、性能 profiling、官方文档检索 | `swiftui-feature-implementation`、`uikit-feature-implementation`、`swift-expert`、`xcode-build`、`ios-performance`、`apple-docs` |
| `swiftui-feature-implementation` | 普通 SwiftUI 落地实现 | 在既定模式下实现页面、表单、列表、状态绑定 | 新页面模式选型、既有大 view 重构、Liquid Glass、性能取证 | `swiftui-ui-patterns`、`swiftui-view-refactor`、`swiftui-liquid-glass`、`ios-performance` |
| `uikit-feature-implementation` | 普通 UIKit 落地实现 | ViewController / UIView / 布局 / 列表 / 页面交互接入 | 通用业务建模、SwiftUI、构建配置、自动化 | `ios-feature-implementation`、`xcode-build`、`debugging`、`ios-performance` |
| `git-workflow` | 默认 Git 流程技能 | 分支、commit、PR 描述、常规 Git 操作 | 明确要求用 `gh` 一次性提交流程 | `gh-pr-flow` |

## Specialized Implementation

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `swift-expert` | 进阶 Swift 设计 | `actor`、`Sendable`、`PAT`、类型擦除、多平台可用性 | 普通 iOS 业务实现、性能 profiling / benchmark、通用页面实现 | `ios-feature-implementation`、`swiftui-feature-implementation`、`uikit-feature-implementation`、`ios-performance` |
| `swiftui-ui-patterns` | 新建 SwiftUI 页面与模式选型 | 新页面、导航模式、布局结构、状态归属 | 既有大 view 清理、视觉设计系统、运行时性能专项 | `swiftui-feature-implementation`、`swiftui-view-refactor`、`ui-ux-design-system`、`ios-performance` |
| `swiftui-view-refactor` | 既有 SwiftUI 文件重构 | 拆分长 `body`、抽子视图、稳定状态树 | 新页面设计、通用非 SwiftUI 重构 | `swiftui-ui-patterns`、`swiftui-feature-implementation`、`refactoring` |
| `swiftui-liquid-glass` | Liquid Glass 专项 | iOS 26+ 玻璃化表面、`glassEffect`、`GlassEffectContainer` | 普通 SwiftUI 模式选型、跨技术栈视觉方向 | `swiftui-ui-patterns`、`swiftui-feature-implementation`、`ui-ux-design-system` |
| `refactoring` | 通用代码异味重构 | 长方法、重复代码、深层嵌套、回调地狱、通用结构重构 | 既有 SwiftUI 视图文件专项整理 | `swiftui-view-refactor` |
| `sdk-architecture` | SDK / Framework 架构 | 模块边界、公共 API、配置、分发、可测试架构 | 普通应用页面开发、一次性构建校验 | `ios-feature-implementation`、`testing`、`xcode-build` |
| `macos-menubar-tuist-app` | Tuist 菜单栏专项 | `LSUIElement` 菜单栏应用、Tuist manifest、脚本化运行 | 无 Xcode 的 SwiftPM 打包、公证模板化流程 | `macos-spm-app-packaging`、`xcode-build` |
| `macos-spm-app-packaging` | 无 Xcode 的 SwiftPM 打包专项 | SwiftPM macOS app 骨架、`.app` 组装、签名、公证、appcast | Tuist 菜单栏工程维护 | `macos-menubar-tuist-app`、`xcode-build` |

## Automation / Build / Validation

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `ios-simulator-automation` | Simulator 自动化 | boot/shutdown/create/delete、语义导航、无障碍检查、模拟器验证 | 真机运行、Build Settings/签名策略、普通业务实现 | `ios-device-automation`、`xcode-build`、`ios-feature-implementation` |
| `ios-device-automation` | 真机自动化 | 连接中的真机构建、安装、启动、测试、设备诊断 | 纯 Simulator 自动化、Build Settings/签名策略设计、普通业务实现 | `ios-simulator-automation`、`xcode-build`、`ios-feature-implementation` |
| `xcode-build` | 构建配置与交付链路 | Build Settings、签名、Archive、导出 IPA、CI/CD | 任务末尾只跑一次编译验收 | `verify-ios-build` |
| `verify-ios-build` | 收尾审查门禁 + 构建验收 | 任何 Apple Xcode 项目相关改动的强制最终门禁；未提交代码审查通过后运行一次 `xcodebuild` 最终确认 | 构建签名、Archive、导出、CI 设计 | `xcode-build` |
| `testing` | 测试编写专项 | 单元测试、UI 测试、Mock/Stub/Spy、异步测试 | 性能 benchmark、`measure(metrics:)`、`xctrace`、一次性 `xcodebuild` 校验 | `ios-performance`、`verify-ios-build`、`code-review`、`debugging` |
| `codex-subagent-orchestration` | 自适应多 Agent 编排入口 | 默认编码工作流，先按 `lite` / `standard` / `full` 选择角色；高风险或复杂验证链路才启用完整 coder/reviewer/tester | 只做一次 `verify-ios-build`、只做单一代码审查、只做单一测试编写，或当前运行时限制且用户未授权 subAgent 时的临时单 Agent 回退 | `ios-feature-implementation`、`code-review`、`testing`、`verify-ios-build` |

## Diagnostics

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `code-review` | 静态审查 | review 代码、PR diff、public API 评审 | 直接实现修复、运行时定位 | `refactoring`、`debugging`、`sdk-architecture` |
| `debugging` | 运行时排障 | crash、异常、未释放、符号化栈、LLDB 定位 | 纯静态审查、性能分析与 benchmark、构建配置设计 | `code-review`、`ios-performance`、`xcode-build` |
| `ios-performance` | 性能分析与测试 | 掉帧、启动慢、CPU / 内存异常、性能回归基线、`measure(metrics:)`、`xctrace`、Instruments | 通用业务实现、普通单元/UI 测试补齐、泛化 crash 排查 | `testing`、`debugging`、`swift-expert` |

## Research / Design / Release

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `apple-docs` | Apple 官方文档检索 | 查询 Apple API、平台可用性、WWDC 与示例工程 | 默认主实现、重构、调试、构建配置 | 对应主技能并附带 `apple-docs` |
| `ui-ux-design-system` | 视觉与设计系统方向 | 配色、排版、设计系统、跨栈 UI/UX 方向和视觉规范 | SwiftUI 具体实现细节、Liquid Glass API 落地 | `swiftui-ui-patterns`、`swiftui-liquid-glass` |
| `app-store-changelog` | 发布文案整理 | 根据 tag 或提交历史生成用户可见的 App Store 更新说明 | Git 提交、PR 创建、构建配置、内部改动总结 | `git-workflow`、`gh-pr-flow`、`xcode-build` |
| `app-store-opportunity-research` | App Store 赛道研究 | 赛道选择、竞品缺口分析、Top-3 机会排序与 MVP PRD | 直接实现业务代码、构建配置、上架执行 | `ios-feature-implementation`、`swiftui-ui-patterns`、`xcode-build` |
| `gh-pr-flow` | `gh` 一条龙 PR 流程 | 用户明确要求使用 `gh` 执行 `stage + commit + push + open PR` | 普通 Git 操作、只写 commit message、只整理 PR 模板 | `git-workflow` |

## Document / Productivity

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `office-docx` | Word / DOCX 文档处理 | 读取、编辑、生成、批注、修订、校验 `.docx` / Word 文档 | `.pptx` / `.xlsx`、Google Docs、普通文案写作 | `office-pptx` |
| `office-pptx` | PowerPoint 演示文稿处理 | 读取、编辑、生成、校验 `.pptx` / PowerPoint 演示文稿 | `docx` / `xlsx`、普通文案写作、纯视觉方向讨论 | `office-docx` |

## Platform / Legacy

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `swiftui-performance-audit` | 旧名兼容入口 | 用户明确提到旧名 `swiftui-performance-audit` | 新的性能分析需求 | `ios-performance` |
