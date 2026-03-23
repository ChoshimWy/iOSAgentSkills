---
name: swiftui-view-refactor
description: 以小而明确的子视图、MV 优先的数据流、稳定视图树、显式依赖注入和正确的 Observation 用法为默认策略，重构或审查 SwiftUI 视图文件。当任务涉及清理 SwiftUI 视图、拆分过长 `body`、移除内联动作或副作用、减少计算型 `some View` helper，或统一 `@Observable` / view model 初始化模式时使用。
---

# SwiftUI 视图重构

## 适用场景
- 需要清理 SwiftUI 大视图或过长的 `body`。
- 需要把内联动作、副作用和业务逻辑从视图中拆出来。
- 需要统一 `@Observable`、`@State`、view model 初始化方式和 MV 优先的数据流。

## 核心规则
- 默认采用 MV，而不是先上 MVVM。
- 优先抽独立子视图，不要把整屏拆成一堆 `private var header: some View` 风格 helper。
- 视图树要稳定，避免顶层 `if/else` 在不同根视图间切换。
- 业务逻辑放到 service / model，视图只保留轻量 orchestration。
- iOS 17+ 的根拥有者用 `@State` 承载 `@Observable`；仅在低版本兼容时回退到 `@StateObject` / `@ObservedObject`。

## 工作流
1. 先整理视图结构顺序
- 推荐顺序：`@Environment` -> `let` / 存储属性 -> 非视图计算属性 -> `init` -> `body` -> 视图 helper -> action / async helper。

2. 移除 `body` 内的内联逻辑
- 把非平凡按钮动作、副作用、`.task` / `.onChange` 内业务逻辑提到私有方法或 service。

3. 拆分长视图
- 复杂 section 提取为独立 `View` 类型。
- 只向子视图传最小输入：数据、`Binding`、回调。
- 复用性强或语义独立的子视图移到独立文件。

4. 稳定视图树
- 保留稳定根视图，把条件收敛到局部 section、`overlay`、`toolbar`、`disabled` 等 modifier。

5. 审查 view model
- 除非用户明确要求或现有代码已标准化，否则不要新增 view model。
- 现有 view model 尽量改成非可选，并在 `init` 中完成初始化。

## 参考资源
- `references/mv-patterns.md`：为什么默认采用 MV、什么时候才需要 view model。

## 输出要求
- 优先采用独立子视图，而不是大型计算型 helper，例如：

```swift
var body: some View {
    List {
        HeaderSection(title: title, subtitle: subtitle)
        FilterSection(
            filterOptions: filterOptions,
            selectedFilter: $selectedFilter
        )
        ResultsSection(items: filteredItems)
        FooterSection()
    }
}
```

- 避免把整屏拆成大量 `private var xxx: some View`：

```swift
var body: some View {
    List {
        header
        filters
        results
        footer
    }
}
```

- 动作和副作用应从 `body` 中抽离：

```swift
Button("Save", action: save)
    .disabled(isSaving)

.task(id: searchText) {
    await reload(for: searchText)
}

private func save() {
    Task { await saveAsync() }
}
```

- 视图文件超过约 `300` 行时，优先继续拆子视图，而不是靠扩展和注释分区掩盖复杂度。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: swiftui-view-refactor`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
