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

## 注释规范速查（审查阻塞口径）

- `public` / `open` API、跨模块复用接口、可复用协议要求：必须补中文 `///` 文档注释。
- 代码注释必须默认使用中文；API 名称、类型名、错误码、关键字、日志/报错原文可保留原文。
- 注释至少覆盖：
  - 输入/输出语义（`Parameter` / `Returns`）；
  - 失败路径（`Throws` 或失败条件）；
  - 并发语义（`@MainActor` / actor / 回调线程约束）；
  - 关键副作用（状态/DB/缓存/磁盘/网络）。
- 复杂分支注释写中文 `why`（业务原因、兼容背景、失败保护），不要复述代码字面逻辑。
- 只补文件头不算完成；关键函数和关键分支需要可执行语义注释。
- 注释与实现不一致、明显过期或误导调用方时，按阻塞项处理。

```swift
/// 同步项目快照到本地缓存。
///
/// - Parameters:
///   - projectID: 项目唯一标识
///   - force: `true` 时忽略本地时间戳，强制覆盖缓存
/// - Returns: 本次同步后缓存版本号
/// - Throws: `SyncError.networkUnavailable` 当网络不可用
/// - Important: 在 `@MainActor` 上更新 UI；缓存写入在后台队列执行。
public func syncSnapshot(projectID: String, force: Bool) async throws -> Int
```
