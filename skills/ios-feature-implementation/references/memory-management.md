# 内存管理参考

## 必检循环引用场景

### 1. 闭包捕获 self
```swift
fetchData { [weak self] result in
    guard let self else { return }
    self.update(result)
}
```

### 2. Delegate
声明为 `weak var delegate: XxxDelegate?`

### 3. Timer
用 block-based API + `[weak self]`，在 `viewWillDisappear` 或 `deinit` 中 `invalidate()`

### 4. NotificationCenter block 观察者
`[weak self]`，deinit 中 `removeObserver`

### 5. Combine
sink 中 `[weak self]`，用 `.store(in: &cancellables)` 管理

### 6. DispatchWorkItem
`[weak self]`

## weak vs unowned
- **默认 `weak`** — 安全，对象释放后自动 nil
- `unowned` 仅在确定被引用对象生命周期更长时使用（如子引用父）

## 生成代码时自动添加
- ViewController/ViewModel 加 deinit 日志（Debug 模式）：
  ```swift
  deinit {
      #if DEBUG
      print("✅ \(type(of: self)) deallocated")
      #endif
  }
  ```
- 处理大量循环数据时使用 `autoreleasepool { }`
- 图片优先用缩略图/降采样
