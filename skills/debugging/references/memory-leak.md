# 内存泄漏排查参考

## 排查步骤
1. **找到未释放的对象** — deinit 中加日志确认哪个对象没释放
2. **检查 6 大泄漏模式** — 逐项对照
3. **定位循环引用** — 找到引用链
4. **给出修复** — 具体代码修复

## 6 大泄漏模式检查清单

### 1. 闭包强引用 self
- 属性闭包/回调闭包中是否捕获了 self？
- 修复: `[weak self]` + `guard let self`

### 2. Delegate 强引用
- delegate 属性是否声明为 `weak`？
- 修复: `weak var delegate: XxxDelegate?`

### 3. Timer 未释放
- Timer 的 target 是否是 self？（Timer 强引用 target）
- 修复: block-based Timer + `[weak self]`，合适时机 invalidate

### 4. Combine 订阅
- sink 中是否用 `[weak self]`？
- AnyCancellable 是否用 `store(in: &cancellables)` 管理？

### 5. NotificationCenter block 观察者
- block 中是否用 `[weak self]`？
- 观察 token 是否在 deinit 中移除？

### 6. 父子互引
- 两个对象是否互相持有强引用？
- 修复: 子引用父用 `weak` 或 `unowned`

## 工具建议
- Memory Graph Debugger: `⌘ + Shift + I` 查看引用图
- Instruments > Leaks: 运行时检测泄漏点
- Instruments > Allocations: Mark Generation 对比泄漏

## deinit 检测代码
```swift
deinit {
    #if DEBUG
    print("✅ \(type(of: self)) deallocated")
    #endif
}
```
