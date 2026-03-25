# 性能基线与 Profiling 工作流

## 1. 先建立回归基线

- 同一个问题先固定目标交互，不要把滚动、启动、导航混在一次测量里。
- 固定设备、OS 和构建配置，优先使用 Release。
- 性能回归优先通过 `measure {}` 或 `measure(metrics:)` 留在测试套件里。

```swift
final class PerformanceTests: XCTestCase {
    func test_launch_performance() {
        measure(metrics: [XCTApplicationLaunchMetric()]) {
            XCUIApplication().launch()
        }
    }

    func test_expensive_flow_performance() {
        let metrics: [XCTMetric] = [
            XCTClockMetric(),
            XCTCPUMetric(),
            XCTMemoryMetric()
        ]

        let options = XCTMeasureOptions()
        options.iterationCount = 10

        measure(metrics: metrics, options: options) {
            performExpensiveOperation()
        }
    }
}
```

## 2. 再做运行时取证

- 当 benchmark 回归了，但你还不知道“为什么”时，再切到 `xctrace` / Instruments。
- 一次 trace 只录一个目标交互。
- 如果是 SwiftUI 特有问题，保留 `SwiftUI` timeline；如果是通用卡顿，优先从 `Time Profiler` 和 `Animation Hitches` 开始。

```bash
xcrun xctrace record \
  --template 'Time Profiler' \
  --device 'iPhone 16 Pro' \
  --attach 'MyApp' \
  --time-limit 15s \
  --output /tmp/MyApp-TimeProfiler.trace \
  --no-prompt
```

## 3. 结果输出建议

- 症状：CPU、掉帧、启动慢、内存增长，还是更新过多。
- 触发动作：用户到底做了什么。
- 证据：metric 数值、trace lane、call tree、allocations 曲线。
- 根因假设：哪些代码路径最可疑，哪些只是高概率推断。
- 验证方式：before / after 对照，是否需要同设备复录。
