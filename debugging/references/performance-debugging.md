# 性能问题诊断参考

## 诊断流程
1. **确认症状** — 卡顿/掉帧/加载慢/内存高/耗电？
2. **定位瓶颈** — CPU/GPU/内存/网络/I/O？
3. **找到根因** — 具体代码/操作？
4. **给出优化方案** — 可操作的代码修改

## 按症状诊断

### UI 卡顿/掉帧
可能原因（按概率排序）：
1. 主线程执行耗时操作
2. 离屏渲染 (cornerRadius + masksToBounds, shadow 无 shadowPath)
3. Cell 中复杂计算或同步图片解码
4. 频繁触发重绘/布局

修复：
- 耗时操作移到 `Task {}` / 后台队列
- 设置 `layer.shadowPath`
- `layer.cornerCurve = .continuous` 避免圆角离屏
- Cell 只做轻量操作，图片异步加载

### 启动慢
可能原因：
1. main 前: 动态库过多、+load 方法
2. main 后: 首屏初始化做太多事

修复：
- 非必要初始化延迟到首帧后 (`DispatchQueue.main.async`)
- 低优先级初始化延迟 2-3 秒
- 合并动态库为静态库

### 内存占用高
可能原因：
1. 图片未降采样
2. 大数据集一次性全部加载
3. 缓存无上限

修复：
- 图片降采样到显示尺寸
- 数据分页加载
- NSCache 设置 `countLimit` 和 `totalCostLimit`

## 工具选择
- 卡顿 → Time Profiler
- 掉帧 → Core Animation
- 内存 → Allocations + Memory Graph
- 启动 → App Launch

## 输出格式
```
⚡ 症状: [问题]
🔍 瓶颈: [CPU/GPU/内存/IO]
💡 根因: [原因]
🔧 优化方案: [代码]
📊 预期效果: [改善]
```
