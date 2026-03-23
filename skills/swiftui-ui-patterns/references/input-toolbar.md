# 底部输入工具栏

## 用途
适用于聊天、评论、消息输入和底部常驻编辑器。

## 核心规则
- 用 `safeAreaInset(edge: .bottom)` 固定输入条。
- 键盘出现时保持输入条和内容区域关系稳定。
- 输入条自身只管理输入状态，不承载发送后的业务逻辑。

## 示例

```swift
ScrollView { content }
    .safeAreaInset(edge: .bottom) {
        MessageInputBar()
    }
```
