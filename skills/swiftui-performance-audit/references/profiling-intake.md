# Profiling 收集清单

## 用途
当纯代码审查无法解释 SwiftUI 性能问题时，用这份清单向用户索要运行时证据。

## 优先先问清楚
- 具体症状是什么：CPU 尖峰、掉帧、内存上涨、hang，还是视图更新过多。
- 具体交互是什么：滚动、输入、首屏加载、导航 push/pop、动画、sheet 展示、后台刷新。
- 目标设备与系统版本。
- 问题发生在真机还是 Simulator。
- 构建配置是 Debug 还是 Release。
- 用户是否已经有 before/after 的对比基线。

## 默认 profiling 请求
指导用户：
- 尽量使用 Release 构建运行应用。
- 使用 SwiftUI Instruments 模板录制。
- 只重现目标交互，时间够抓到问题即可，不要把多种操作混在一次录制里。
- 同时保留 SwiftUI timeline 和 Time Profiler。
- 导出 trace，或至少提供关键 lane 与 call tree 的截图。

## 需要的材料
- 相关 SwiftUI lane 的 trace 导出或截图。
- Time Profiler call tree 的截图或导出。
- 设备 / OS / 构建配置。
- 录制时用户做了什么操作的简短说明。
- 如果牵涉内存，再补 memory graph 或 Allocations 数据。

## 什么时候继续追问
- 如果第一次录制混入了多个交互，要求第二次只录目标动作。
- 如果用户已经尝试过修复，要求提供 before/after 成对结果。
- 如果问题只在真机上出现，或者滚动手感很关键，要求补真机录制。

## 常见陷阱
- 只给结论，不给 trace 或截图。
- Debug 环境下录制后直接下最终结论。
- 一次 trace 混合太多页面和交互，导致证据失焦。
