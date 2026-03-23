# 匹配过渡动画

## 用途
用于在源视图和目标视图之间建立连续感，例如缩略图到详情、卡片到全屏。

## 核心规则
- 使用稳定的 ID 和共享 `Namespace`。
- iOS 26+ 可优先使用 `matchedTransitionSource` 与 `navigationTransition(.zoom(...))`。
- 同一元素跨状态的几何关系要清晰，不要用随机 ID。
