---
name: ios-feature-implementation
description: 默认 iOS feature 实现技能。只用于与具体 UI 技术栈无关的通用业务实现：service / repository / use case / domain model / view model、依赖注入、导航接线和常规 async/await 落地；如果任务核心已经变成 SwiftUI / UIKit 页面代码、页面模式选型、已有 SwiftUI 大 view 重构、构建配置、模拟器/真机自动化、性能取证或官方文档检索，不要使用本 skill 作为主 skill；若任务产出修改了 Apple Xcode 项目相关内容，默认以定向测试/必要验证与 `code-review` 放行为收口；`final-evidence-gate` / `verify-ios-build` 仅在用户显式要求或需要补强完整项目环境证据时按需使用。
---

# iOS Feature 实现

## 角色定位
- 默认型主 skill。
- 负责大多数通用 iOS feature 业务代码与应用层 glue code。
- 不直接承担 UIKit / SwiftUI 专项页面结构设计，也不负责构建、自动化与性能取证。

## 触发判定（硬边界）
- 用户主要在问 `service`、`repository`、`use case`、`view model`、`coordinator`、`router`、依赖注入或导航接线时，使用本 skill。
- 用户主要在问 `NavigationStack` / `TabView` / `sheet` / `body` / 页面布局 / `UIViewController` / 组件样式时，不要用本 skill 作为主 skill。
- 用户主要在问 `xcodebuild` 门禁、签名、`simctl`、`devicectl`、`xctrace`、`measure(metrics:)` 或 Apple 官方 API 事实时，切换到对应专项 skill。

## 适用场景
- 编写或修改 service、repository、use case、domain model、view model。
- 处理依赖注入、feature wiring、导航接线和错误流转。
- 落地常规 async/await、状态同步和业务层内存安全约束。

## 核心规则
- 默认优先值类型、严格访问控制、`guard` 提前返回和结构化并发。
- UI 更新放在主线程或 `@MainActor`。
- 业务逻辑进入 service / model / coordinator，不堆进 view 或 view controller。
- 如果目标工程使用 CocoaPods 且涉及私有组件/本地联调，先查 `Podfile` / `Podfile.lock` / `Pods/Manifest.lock`，确认是否为本地 `:path` Pod；命中时默认修改组件源码仓，不修改 `Pods/` 副本。
- 对本地 `:path` Pod / 私有组件，`Pods/<LibraryName>` 默认属于禁止改动范围；实现阶段的 ownership 应指向真实组件仓路径，而不是 `Pods/` 快照。
- 如本次实现修改私有库 / 私有组件，主项目默认必须切回或保持本地 `:path` 私有库依赖进行开发与验证；除非用户明确要求回线上依赖验证，否则不要把验证基线切到线上版本化依赖或 `Pods/` 快照。
- 文件、方法或类型体量超过常规阈值时优先拆分，而不是继续堆叠复杂度。
- 对 `public` / `open` API、跨模块复用类型与可复用协议要求，默认补 `///` 文档注释；至少说明输入、输出、失败语义与关键副作用。
- 涉及并发边界（`@MainActor` / actor / 回调线程）、副作用（状态/DB/缓存/磁盘/网络）或失败路径（throws/错误码/回退条件）的实现，注释必须写清约束。
- 复杂分支补 `why` 注释，解释业务原因/兼容背景/失败保护；不要只复述代码字面含义。
- 只补文件头注释不算完成；关键函数与关键分支必须有可执行语义的内联注释。
- 对应项目中新建 `.swift`、`.h`、`.m`、`.mm` 等源码文件且项目要求文件头时，`Created by` 必须使用本机用户名称（`whoami` 输出），不要写 `Codex`；日期默认使用 `YYYY/M/D`，例如 `Created by $(whoami) on 2026/4/11.`。

## 参考资源
- `references/navigation.md`：导航组织与深链。
- `references/memory-management.md`：内存管理与循环引用防护。

## 实现阶段输出合同
- 默认输出以下字段，便于后续 `code-review` / `testing` / `verify-ios-build` 聚合：

```text
changed_files:
  - ...
summary:
  - ...
known_risks:
  - ...
test_impact: <测试影响面>
no_test_reason: <仅当本轮不涉及新增测试时填写>
```

- 字段规则：
  - `changed_files` 只列本轮实际改动文件。
  - `summary` 聚焦行为变化与契约变化，不粘贴大段 diff。
  - `known_risks` 仅记录尚未消除的真实风险；无则写 `[]`。
  - `test_impact` 与 `no_test_reason` 二选一必须填写。

## 可选证据验证
- 如果当前任务没有进入 `codex-subagent-orchestration`（CC 用户参考 CLAUDE.md 三步收口工作流），或当前轮只能以单 Agent 执行，本 skill 完成实现后也不要直接跳到可选验证；默认后续链路按三步执行：`ios-feature-implementation -> testing/定向验证 -> code-review`。
- 只要当前任务产出修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、构建脚本、plist / entitlements / xcconfig / scheme 或项目内环境配置），最终默认以定向测试/必要验证与 `code-review` 放行为收口；`final-evidence-gate` / `verify-ios-build` 仅在用户显式要求或需要补强完整项目环境证据时按需使用。
- 若执行可选完整验证，证据必须来自目标项目根目录的项目环境；沙箱内的构建结果不能作为完整项目环境证据。
- 对 iOS 项目，若升级到 `verify-ios-build`，必须优先 `.xcworkspace`（当 `.xcworkspace` 与 `.xcodeproj` 同时存在时），并默认优先已连接真机；找不到连接中的真机时再回退到 simulator。
- 若可选 `final-evidence-gate` / `verify-ios-build` 未执行或失败，应在交付中说明已执行的定向测试/审查证据与残余风险。

## 与其他技能的关系
- 通用 iOS feature 业务开发默认优先使用本技能。
- 如果当前任务属于非编排 / 单 Agent 的实现链路，本 skill 完成代码修改后，默认先切到 `testing/定向验证`，再切到 `code-review`；`final-evidence-gate` / `verify-ios-build` 仅按需升级。
- 如果任务核心已经进入普通 SwiftUI 页面落地，本 skill 只作为业务层辅助，主 skill 切换到 `swiftui-feature-implementation`。
- 如果任务核心已经进入普通 UIKit 页面落地，本 skill 只作为业务层辅助，主 skill 切换到 `uikit-feature-implementation`。
- 如果任务进入复杂并发、类型擦除、协议族或跨平台可用性策略，切换到 `swift-expert`。
- 如果任务已经变成 benchmark、`measure(metrics:)`、`xctrace`、Instruments 或启动 / 滚动性能分析，切换到 `ios-performance`。
- 如果任务是构建配置、签名、Archive/Export 或 CI，切换到 `xcode-build`。
- 如果只是查询 Apple 官方 API、可用性或 WWDC 内容，切换到 `apple-docs`。
