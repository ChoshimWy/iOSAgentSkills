# 菜单栏命令

## 用途
用于在 macOS / iPadOS 场景中添加 `CommandMenu`、`CommandGroup` 或替换系统菜单项。

## 核心规则
- 菜单定义放在 `Scene` 层级。
- 应用级命令和上下文命令分开管理。
- 与当前选中对象相关的菜单项优先使用 `FocusedValue`。
