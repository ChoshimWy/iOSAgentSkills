# 焦点管理

## 用途
在表单、多输入框或键盘驱动流程中，用 `@FocusState` 管理当前焦点。

## 核心规则
- 用枚举描述字段焦点比多个布尔值更稳定。
- 提交后显式推进到下一个字段，或在完成时清空焦点。
- 焦点状态只保留在真正拥有表单的视图层。

## 示例

```swift
enum Field: Hashable { case email, password }
@FocusState private var focusedField: Field?
```
