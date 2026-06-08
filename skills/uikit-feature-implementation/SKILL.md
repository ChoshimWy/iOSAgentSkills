---
name: uikit-feature-implementation
description: UIKit 页面落地入口：ViewController、UIView、布局、列表、交互与界面装配。通用业务建模、SwiftUI、构建配置、自动化、性能和文档查询走专项；Xcode 改动收尾交给 final-evidence-gate。
---

# UIKit Feature 实现

## 角色定位
- 专注于普通 UIKit 页面与组件落地的实现型 skill。
- 负责把现有业务输入接入 ViewController、UIView、列表与交互层。
- 不承担通用业务建模、构建配置、自动化或 Apple 文档检索。

## 触发判定（硬边界）
- 已有明确的页面职责、业务输入和 UIKit 架构，只差 `UIViewController` / `UIView` / 布局 / 列表代码时，使用本 skill。
- 如果还需要先设计 `repository`、`use case`、`coordinator`、导航 wiring 或通用业务模型，先切回 `ios-feature-implementation`。
- 如果任务核心是 SwiftUI 页面、构建链路、设备自动化或性能 profiling，不要用本 skill 作为主 skill。

## 适用场景
- 编写或修改 `UIViewController`、`UIView`、`UICollectionView` / `UITableView` 页面。
- 在既定架构下接入布局、事件、状态展示与页面交互。
- 维护现有 UIKit 页面结构、绑定、列表与导航衔接。

## 核心规则
- 按 `Properties -> UI Components -> Lifecycle -> Setup -> Public -> Private -> Actions` 组织 ViewController。
- 优先复用现有布局工具和项目约定；项目已使用 SnapKit 时，延续既有风格。
- 业务逻辑继续放在 service / model / coordinator，不塞进 ViewController。
- 对 `public` / `open` API、跨模块复用类型与可复用协议要求，默认补 `///` 文档注释；至少说明输入、输出、失败语义与关键副作用。
- 涉及并发边界（`@MainActor` / actor / 回调线程）、副作用（状态/DB/缓存/磁盘/网络）或失败路径（throws/错误码/回退条件）的实现，注释必须写清约束。
- 复杂分支补 `why` 注释，解释业务原因/兼容背景/失败保护；不要只复述代码字面含义。
- 只补文件头注释不算完成；关键函数与关键分支必须有可执行语义的内联注释。
- 新建 `.swift`、`.h`、`.m`、`.mm` 文件且项目要求文件头时，`Created by` 必须使用本机用户名称（`whoami` 输出），不要写 `Codex`；日期默认使用 `YYYY/M/D`，例如 `Created by $(whoami) on 2026/4/11.`。

## 参考资源
- `references/uikit.md`

## 最终证据门禁
- 如果当前任务没有进入 `codex-subagent-orchestration`（CC 用户参考 CLAUDE.md 四步收口工作流），或当前轮只能以单 Agent 执行，本 skill 完成实现后也不要直接跳到最终门禁；默认后续链路按固定四步执行：`uikit-feature-implementation -> testing -> code-review -> final-evidence-gate`。
- 只要当前任务产出修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、构建脚本、plist / entitlements / xcconfig / scheme 或项目内环境配置），最终必须进入 `final-evidence-gate`；证据不足、高风险或命中工程/依赖/签名/资源打包类改动时，再切到 `verify-ios-build`。
- 最终验证证据必须来自目标项目根目录的项目环境；沙箱内的构建结果不能作为最终验收结论。
- 对 iOS 项目，若升级到 `verify-ios-build`，必须优先 `.xcworkspace`（当 `.xcworkspace` 与 `.xcodeproj` 同时存在时），并默认优先已连接真机；找不到连接中的真机时再回退到 simulator。
- 在 `final-evidence-gate` 接受现有证据或 `verify-ios-build` 成功前，不得把任务表述为“已完成”；只能明确说明“实现已完成，但验证证据不足/验证失败，任务未完成”。

## 与其他技能的关系
- 已有 UIKit 架构或页面模式时，普通页面落地优先使用本技能。
- 如果当前任务属于非编排 / 单 Agent 的实现链路，本 skill 完成代码修改后，固定先切到 `testing`，再切到 `code-review`，最后进入 `final-evidence-gate`。
- 如果需要先设计通用业务类型、service、repository 或导航 wiring，主 skill 切换到 `ios-feature-implementation`。
- 如果任务是构建配置、签名、Archive/Export 或 CI，切换到 `xcode-build`。
- 如果任务是 crash、异常或对象未释放等运行时问题，切换到 `debugging`。
- 如果任务已经进入性能 profiling、启动慢或滚动卡顿诊断，切换到 `ios-performance`。
