# xctrace 模板选择

先运行：

```bash
xcrun xctrace list templates
```

不同 Xcode 版本的模板名可能略有差异，命令示例里的模板名应以本机输出为准。

## 常见症状与模板

| 症状 / 目标 | 首选模板 | 常见组合 | 适用范围 |
| --- | --- | --- | --- |
| CPU 高、主线程忙、页面进入慢 | `Time Profiler` | `Time Profiler` + `System Trace` | UIKit / SwiftUI |
| 列表滚动掉帧、转场卡顿、动画不顺 | `Animation Hitches` | `Animation Hitches` + `Time Profiler` | UIKit / SwiftUI |
| 冷启动、首屏慢 | `App Launch` | `App Launch` + `Time Profiler` | UIKit / SwiftUI |
| 内存持续上涨 | `Allocations` | `Allocations` + `Leaks` | UIKit / SwiftUI |
| 怀疑泄漏 | `Leaks` | `Leaks` + `Allocations` | UIKit / SwiftUI |
| SwiftUI 更新过多、布局抖动 | `SwiftUI` | `SwiftUI` + `Time Profiler` | SwiftUI |
| 线程调度异常、锁竞争、hang | `System Trace` | `System Trace` + `Time Profiler` | UIKit / SwiftUI |
| 网络拖慢页面响应 | `Network` | `Network` + `Time Profiler` | UIKit / SwiftUI |

## 常用命令

```bash
# Time Profiler
xcrun xctrace record \
  --template 'Time Profiler' \
  --device 'iPhone 16 Pro' \
  --attach 'MyApp' \
  --time-limit 15s \
  --output /tmp/MyApp-TimeProfiler.trace \
  --no-prompt

# Animation Hitches
xcrun xctrace record \
  --template 'Animation Hitches' \
  --device 'iPhone 16 Pro' \
  --attach 'MyApp' \
  --time-limit 15s \
  --output /tmp/MyApp-Hitches.trace \
  --no-prompt

# SwiftUI
xcrun xctrace record \
  --template 'SwiftUI' \
  --device 'iPhone 16 Pro' \
  --attach 'MyApp' \
  --time-limit 15s \
  --output /tmp/MyApp-SwiftUI.trace \
  --no-prompt

# 导出 trace 目录结构
xcrun xctrace export \
  --input /tmp/MyApp-TimeProfiler.trace \
  --toc \
  --output /tmp/MyApp-TimeProfiler-toc.xml
```
