# API 接口设计审查参考

## 设计原则

### 最小暴露
- 默认 `internal`，只把必要的标记 `public`
- 不暴露内部实现细节
- API 一旦发布即为承诺，谨慎新增 public

### 命名清晰
- 遵循 Swift API Design Guidelines
- 读起来像自然语言: `array.insert(item, at: index)`
- mutating vs non-mutating: `.sort()` / `.sorted()`
- 工厂方法 `make` 前缀: `makeIterator()`

### 参数设计
- 超过 3 个参数 → 提取 Configuration struct
- 提供合理默认参数值
- 用参数标签增加可读性: `func move(from source: Int, to destination: Int)`

### 异步 API
- 新 API 优先 async/await
- 回调 API 标注 `@available(*, deprecated)` 并提供 async 版本
- 明确标注 callback 在哪个线程回调

### 错误设计
- 定义具体 Error enum，含错误码和描述
- 区分可恢复 vs 不可恢复错误

### 版本兼容
- 废弃旧 API 用 `@available(*, deprecated, renamed:)`
- 新 API 标注最低版本 `@available(iOS 16, *)`
- Breaking change 只在 major 版本

## API 必需文档注释
```swift
/// 获取用户资料
///
/// - Parameter id: 用户唯一标识
/// - Returns: 用户资料对象
/// - Throws: `SDKError.notFound` 如果用户不存在
public func fetchProfile(id: String) async throws -> UserProfile
```
