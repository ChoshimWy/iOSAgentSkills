# 使用 Instruments 优化 SwiftUI 性能（摘要）

背景：该 WWDC 内容介绍了 Instruments 26 中的新一代 SwiftUI Instrument，以及如何定位 SwiftUI 特有瓶颈。

## 关键要点
- 分析 SwiftUI 问题时，优先使用 SwiftUI 模板：SwiftUI instrument + Time Profiler + Hangs/Hitches。
- “Long View Body Updates” 是最常见的热点入口，可直接定位慢 `body`。
- 先框选长更新时间段，再和 Time Profiler 交叉定位热点栈。
- 让昂贵工作离开 `body`：格式化、排序、图片解码都应进入预计算或缓存路径。
- 用 Cause & Effect Graph 理解“为什么会更新”，不要只看调用栈。
- 避免大范围依赖传播，例如广泛读取 `@Observable` 数组或全局环境。
- 尽量把状态缩小到真正受影响的视图。
- 环境值本身也有检查成本，不要把高频变化值（计时器、几何信息）随意塞进环境。

## 建议流程
1. 在 Release 模式下录制 SwiftUI 模板 trace。
2. 查看 `Long View Body Updates` 和 `Other Long Updates`。
3. 缩小到具体慢更新，再去 Time Profiler 看热点帧。
4. 把慢逻辑迁移到预计算、缓存或后台处理路径。
5. 用 Cause & Effect Graph 找出意外的大范围更新来源。
6. 重新录制，对比更新次数和 hitch 频率。

## 典型示例
- 将距离格式化缓存到 location manager，而不是在 `body` 中每次重算。
- 把“全局 favorites 数组依赖”改为按 item 切分，减少更新扇出。
