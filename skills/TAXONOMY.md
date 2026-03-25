# 业务 Skill 分类索引

本文只覆盖业务 skill，不包含 `skills/.system/` 与 `skills/_shared-sentinel/`。

## 分类原则
- `默认`：默认优先触发的通用实现或流程技能。
- `专项`：面向特定技术面、架构面或平台形态的技能。
- `辅助`：为主技能提供资料、设计方向或事实依据的技能。
- `诊断`：用于发现问题、分析风险、定位根因的技能。
- `验证`：用于任务末尾一次性验证结果的技能。
- `发布交付`：用于发布说明、PR 交付或交付链路收尾的技能。

## 命名迁移

| 旧 skill | 新 skill | 说明 |
| --- | --- | --- |
| `yeet` | `gh-pr-flow` | 名称改为表达清晰的 `gh` 一条龙 PR 流程；旧名不再使用。 |
| `swiftui-performance-audit` | `ios-performance` | SwiftUI 性能专项并入统一的 iOS 性能分析与测试 skill；旧名仅保留兼容入口。 |

## 默认

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `ios-base` | 默认 iOS/Swift 实现技能 | 通用 iOS/Swift 业务开发、常规组件实现、普通架构落地 | 深度并发与类型抽象、性能分析与 benchmark、构建配置、官方文档检索 | `swift-expert`、`ios-performance`、`swiftui-ui-patterns`、`xcode-build`、`apple-docs` |
| `git-workflow` | 默认 Git 流程技能 | 分支、commit、PR 描述、常规 Git 操作 | 明确要求用 `gh` 一次性提交流程 | `gh-pr-flow` |

## 专项

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `swift-expert` | 进阶 Swift 设计 | `actor`、`Sendable`、`PAT`、类型擦除、多平台可用性 | 普通 iOS 开发、性能 profiling / benchmark、常规 SwiftUI 页面实现 | `ios-base`、`ios-performance`、`swiftui-ui-patterns` |
| `ios-performance` | 性能分析与测试 | 掉帧、启动慢、CPU / 内存异常、性能回归基线、`measure(metrics:)`、`xctrace`、Instruments | 通用业务实现、普通单元/UI 测试补齐、泛化 crash 排查 | `testing`、`debugging`、`swift-expert` |
| `swiftui-ui-patterns` | 新建 SwiftUI 页面与模式选型 | 新页面、组件模式、`TabView`、导航、布局结构 | 既有大 view 清理、视觉设计系统、运行时性能专项 | `swiftui-view-refactor`、`ui-ux-pro-max`、`ios-performance` |
| `swiftui-view-refactor` | 既有 SwiftUI 文件重构 | 拆分长 `body`、抽子视图、稳定状态树、清理现有视图文件 | 新页面设计、通用非 SwiftUI 重构 | `swiftui-ui-patterns`、`refactoring` |
| `swiftui-liquid-glass` | Liquid Glass 专项 | iOS 26+ 玻璃化表面、`glassEffect`、`GlassEffectContainer` | 普通 SwiftUI 模式选型、跨技术栈设计方向 | `swiftui-ui-patterns`、`ui-ux-pro-max` |
| `refactoring` | 通用代码异味重构 | 长方法、重复代码、深层嵌套、回调地狱、通用结构重构 | 既有 SwiftUI 视图文件专项整理 | `swiftui-view-refactor` |
| `sdk-architecture` | SDK/Framework 架构 | 模块边界、公共 API、配置、分发、可测试架构 | 普通应用页面开发、一次性构建校验 | `ios-base`、`testing`、`xcode-build` |
| `macos-menubar-tuist-app` | Tuist 菜单栏专项 | `LSUIElement` 菜单栏应用、Tuist manifest、脚本化运行 | 无 Xcode 的 SwiftPM 打包、公证模板化流程 | `macos-spm-app-packaging`、`xcode-build` |
| `macos-spm-app-packaging` | 无 Xcode 的 SwiftPM 打包专项 | SwiftPM macOS app 骨架、`.app` 组装、签名、公证、appcast | Tuist 菜单栏工程维护 | `macos-menubar-tuist-app`、`xcode-build` |
| `xcode-build` | 构建配置与交付链路 | Build Settings、签名、Archive、导出 IPA、CI/CD | 任务末尾只跑一次编译校验 | `verify-ios-build` |
| `testing` | 测试编写专项 | 单元测试、UI 测试、Mock/Stub/Spy、异步测试 | 性能 benchmark、`measure(metrics:)`、`xctrace`、一次性 `xcodebuild` 校验 | `ios-performance`、`verify-ios-build`、`code-review`、`debugging` |

## 辅助

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `apple-docs` | Apple 官方文档检索 | 查询 Apple API、平台可用性、WWDC 与示例工程 | 默认主实现、重构、调试、构建配置 | 对应主技能并附带 `apple-docs` |
| `ui-ux-pro-max` | 跨技术栈视觉与交互设计 | 配色、排版、设计系统、跨栈 UI/UX 方向和视觉规范 | SwiftUI 具体实现细节、Liquid Glass 专项 API 落地 | `swiftui-ui-patterns`、`swiftui-liquid-glass` |

## 诊断

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `code-review` | 静态审查 | review 代码、PR diff、public API 评审 | 直接实现修复、运行时定位 | `refactoring`、`debugging`、`sdk-architecture` |
| `debugging` | 运行时排障 | crash、异常、未释放、符号化栈、LLDB 定位 | 纯静态审查、性能分析与 benchmark、构建配置设计 | `code-review`、`ios-performance`、`xcode-build` |

## 验证

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `verify-ios-build` | 任务收尾编译验证 | 所有实现完成后，运行一次 `xcodebuild` 做最终构建校验 | 构建签名、Archive、导出、CI 设计 | `xcode-build` |

## 发布交付

| Skill | 角色 | 主触发场景 | 不要触发的场景 | 切换到 |
| --- | --- | --- | --- | --- |
| `app-store-changelog` | 发布文案整理 | 根据 tag 或提交历史生成用户可见的 App Store 更新说明 | Git 提交、PR 创建、构建配置、内部改动总结 | `git-workflow`、`gh-pr-flow`、`xcode-build` |
| `gh-pr-flow` | `gh` 一条龙 PR 流程 | 用户明确要求使用 `gh` 执行 `stage + commit + push + open PR` | 普通 Git 操作、只写 commit message、只整理 PR 模板 | `git-workflow` |
