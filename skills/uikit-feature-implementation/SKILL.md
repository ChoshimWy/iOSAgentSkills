---
name: uikit-feature-implementation
description: UIKit 常规页面落地技能。用于在既定架构下实现 ViewController、UIView、布局、列表、交互与界面装配；不要用于通用业务建模、SwiftUI 页面模式、新旧构建配置、模拟器/真机自动化、性能取证或官方文档检索。
---

# UIKit Feature 实现

## 角色定位
- 专注于普通 UIKit 页面与组件落地的实现型 skill。
- 负责把现有业务输入接入 ViewController、UIView、列表与交互层。
- 不承担通用业务建模、构建配置、自动化或 Apple 文档检索。

## 适用场景
- 编写或修改 `UIViewController`、`UIView`、`UICollectionView` / `UITableView` 页面。
- 在既定架构下接入布局、事件、状态展示与页面交互。
- 维护现有 UIKit 页面结构、绑定、列表与导航衔接。

## 核心规则
- 按 `Properties -> UI Components -> Lifecycle -> Setup -> Public -> Private -> Actions` 组织 ViewController。
- 优先复用现有布局工具和项目约定；项目已使用 SnapKit 时，延续既有风格。
- 业务逻辑继续放在 service / model / coordinator，不塞进 ViewController。
- 新建 `.swift`、`.h`、`.m`、`.mm` 文件且项目要求文件头时，`Created by` 必须使用本机用户名称 `Choshim.Wei`，不要写 `Codex`；日期默认使用 `YYYY/M/D`，例如 `Created by Choshim.Wei on 2026/4/11.`。

## 参考资源
- `references/uikit.md`

## 与其他技能的关系
- 已有 UIKit 架构或页面模式时，普通页面落地优先使用本技能。
- 如果需要先设计通用业务类型、service、repository 或导航 wiring，切换到 `ios-feature-implementation`。
- 如果任务是构建配置、签名、Archive/Export 或 CI，切换到 `xcode-build`。
- 如果任务是 crash、异常或对象未释放等运行时问题，切换到 `debugging`。
- 如果任务已经进入性能 profiling、启动慢或滚动卡顿诊断，切换到 `ios-performance`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: uikit-feature-implementation`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel
