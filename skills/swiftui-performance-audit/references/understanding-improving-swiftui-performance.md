# Understanding and Improving SwiftUI Performance（摘要）

背景：Apple 关于用 Instruments 诊断 SwiftUI 性能，并通过设计模式减少长更新和高频更新的要点。

## 核心概念
- SwiftUI 是声明式框架，视图更新由状态、环境和可观察数据依赖驱动。
- `body` 必须足够快，才能赶上每一帧的时间预算；更新太慢或太频繁都会造成 hitch。
- Instruments 是定位长更新和高频更新的主要工具。

## Instruments 工作流
1. 通过 `Product > Profile` 启动分析。
2. 选择 SwiftUI 模板并开始录制。
3. 重现目标交互。
4. 停止录制后结合 SwiftUI track 与 Time Profiler 观察问题。

## SwiftUI timeline 的关键 lane
- `Update Groups`：SwiftUI 计算更新的整体时间。
- `Long View Body Updates`：`body` 太慢的更新。
- `Long Platform View Updates`：SwiftUI 承载的 UIKit / AppKit 代价。
- `Other Long Updates`：几何、文本、布局等其他 SwiftUI 开销。
- `Hitches`：UI 没赶上帧预算的时段。

## 诊断长 `body` 更新
- 展开 SwiftUI track，看模块级子轨道。
- 框选慢更新，再和 Time Profiler 对照。
- 用 call tree 或 flame graph 找热点帧。
- 需要时多录几次，保证样本足够。
- 可以过滤到特定视图，例如 `Show Calls Made by MySwiftUIView.body`。

## 诊断高频更新
- 使用 `Update Groups` 找到长时间活跃但单次并不特别慢的区域。
- 框选后分析更新次数。
- 用 Cause graph（`Show Causes`）追踪更新触发源。
- 把触发源与预期数据流对比，优先处理最高频的错误扇出。

## 修复方向
- 缩小观察范围。
- 稳定列表 identity。
- 把格式化、排序、图片处理移出 `body`。
- 用更稳定的视图树替代顶层频繁切换的根分支。

## 验证
- 修复后重新录制同一交互。
- 对比更新次数、hitch 频率和主线程热点是否下降。
