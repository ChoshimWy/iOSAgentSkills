---
name: swiftui-ui-patterns
description: 提供构建 SwiftUI 视图与组件的最佳实践和示例导向指南，覆盖导航层级、自定义 view modifier，以及基于 stack / grid 的响应式布局。当任务涉及创建或重构 SwiftUI UI、设计 `TabView` 架构、组合 `VStack` / `HStack` 屏幕、管理 `@State` / `@Binding`，或需要组件级模式与示例时使用。
---

# SwiftUI UI 模式

## 适用场景
- 需要设计或重构 SwiftUI 页面与组件。
- 需要为 `TabView`、`NavigationStack`、`sheet`、`List`、`Grid` 等交互选择合适模式。
- 需要为新页面快速找到与现有项目一致的状态管理和布局策略。

## 核心规则
- 优先使用现代 SwiftUI 状态管理：`@State`、`@Binding`、`@Observable`、`@Environment`。
- 先决定状态归属，再决定用哪种 wrapper。
- 共享依赖进 `@Environment`，局部依赖优先显式初始化注入。
- 大页面要拆成小视图，避免把布局、路由、网络和业务逻辑混在同一文件。
- 涉及低版本兼容时，明确标注最低系统版本和替代方案。

## 工作流
1. 识别页面类型
- 先判断当前页面是列表、详情、表单、设置、标签页还是滚动驱动交互。
- 再从 `references/components-index.md` 进入对应参考文档。

2. 确定状态与路由
- 局部状态用 `@State`，父子值传递用 `@Binding`。
- 共享服务和应用级配置用 `@Environment`。
- 需要复杂导航时，优先阅读 `references/navigationstack.md`、`references/sheets.md`、`references/deeplinks.md`。

3. 先搭结构，再补异步与性能
- 新项目从 `references/app-wiring.md` 起步。
- 需要异步加载时看 `references/async-state.md`。
- 页面较大、滚动频繁或更新密集时看 `references/performance.md`。

## 参考资源
- `references/components-index.md`：组件与横切参考总入口。
- `references/app-wiring.md`：根视图、依赖图和应用壳体装配。
- `references/async-state.md`：异步状态、取消、重启和防抖。
- `references/navigationstack.md`：导航状态与路由组织。
- `references/sheets.md`：模态与 `sheet` 路由。
- `references/previews.md`：`#Preview`、fixture 和隔离注入。

## 输出要求
- 输出具体建议时，说明：
  - 当前页面属于哪一类 UI。
  - 状态应归属在哪里。
  - 应使用哪个参考文件继续实现。
- 重构建议应避免以下反模式：
  - 一个视图同时承担布局、业务逻辑、网络请求和路由。
  - 用多个布尔值描述互斥的 `sheet`、`alert` 或导航目的地。
  - 在 `body` 驱动路径中直接调用实时服务。
  - 为规避类型问题而滥用 `AnyView`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: swiftui-ui-patterns`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
