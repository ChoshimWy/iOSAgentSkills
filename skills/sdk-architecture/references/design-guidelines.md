# SDK 设计准则参考

## 一、API 设计准则

### 1.1 命名与一致性
- 所有公开 API 遵循 Swift API Design Guidelines
- 方法读起来像自然语言: `sdk.track(event:properties:)`
- 同类操作命名保持一致：如果用了 `add`，就不要混用 `insert`/`append`
- 异步方法统一用 async/await，不混用 callback 和 async 两套 API
- Builder/Configuration 用链式调用风格保持流畅

### 1.2 最小 API 表面积
- 每个 public 符号都需要理由，默认 `internal`
- 用 `@_spi(Internal)` 隔离仅供内部模块使用但需跨 target 访问的 API
- 避免暴露内部类型别名、内部错误类型、队列、锁等实现细节
- 使用 `public struct` 而非 `public class` 阻止外部继承
- Configuration 结构体属性用 `public private(set)` 或只暴露 init

### 1.3 参数与返回值
- 参数超过 3 个 → 提取为 Configuration / Options struct
- 提供合理默认值减少调用方负担
- 返回值避免裸元组，用命名类型增强可读性
- 布尔参数考虑用 enum 替代: `.enabled` / `.disabled` 比 `true/false` 更清晰

### 1.4 错误设计
```swift
public enum SDKError: LocalizedError, CustomNSError {
    case notInitialized
    case invalidConfiguration(reason: String)
    case networkFailure(underlying: Error)
    case serverError(code: Int, message: String)
    case timeout
    
    public var errorCode: Int { ... }
    public var errorDescription: String? { ... }
    public static var errorDomain: String { "com.company.sdk" }
}
```
- 按域划分错误类型: `AuthError`, `NetworkError`, `StorageError`
- associated value 传递上下文信息，便于调试
- 实现 `LocalizedError` + `CustomNSError` 同时支持 Swift 和 ObjC
- 可恢复错误用 `throws`，不可恢复错误用 `fatalError` + 明确文档

### 1.5 线程安全契约
- 文档中明确标注每个 API 的线程安全性
- 回调/delegate 方法标明回调线程（推荐主线程）
- 用 `@MainActor` 标注需要主线程调用的 API
- `@Sendable` 标注可安全跨 actor 传递的闭包

## 二、架构设计准则

### 2.1 模块划分原则
```
SDKCore          — 零依赖基础层 (Logger, Storage, Network, Extensions)
SDKDomain        — 业务模型与协议定义 (无外部依赖)
SDKFeatureA      — 功能模块 A (依赖 Core + Domain)
SDKFeatureB      — 功能模块 B (依赖 Core + Domain)
SDK              — 聚合入口层 (组装 + 暴露 public API)
```
- 每个模块独立编译、独立测试
- 模块间通过 Protocol 通信，不直接依赖实现
- Feature 模块之间禁止互相依赖（通过 Core 层中转或事件总线）

### 2.2 依赖注入容器
```swift
final class DependencyContainer {
    private var factories: [String: () -> Any] = [:]
    
    func register<T>(_ type: T.Type, factory: @escaping () -> T) {
        factories[String(describing: type)] = factory
    }
    
    func resolve<T>(_ type: T.Type) -> T {
        guard let factory = factories[String(describing: type)] else {
            fatalError("No registration for \(type)")
        }
        return factory() as! T
    }
}
```
- SDK 启动时组装依赖图，运行时不再变更
- 外部可注入的扩展点（如 Logger、NetworkAdapter）通过 Configuration 暴露
- 内部组件通过容器获取依赖，不直接构造

### 2.3 生命周期管理
```swift
public final class MySDK {
    public enum State { case uninitialized, initializing, ready, shuttingDown, terminated }
    public private(set) var state: State = .uninitialized
    
    public func initialize(with config: Configuration) async throws {
        guard state == .uninitialized else {
            throw SDKError.alreadyInitialized
        }
        state = .initializing
        // ... 初始化各模块
        state = .ready
    }
    
    public func shutdown() async {
        guard state == .ready else { return }
        state = .shuttingDown
        // ... 释放资源、flush 缓存、关闭连接
        state = .terminated
    }
}
```
- 状态机管理 SDK 生命周期，防止非法状态转换
- `initialize` 幂等或抛错，不允许重复初始化后数据不一致
- `shutdown` 优雅关闭：flush 日志/上报队列、取消网络请求、释放缓存

### 2.4 事件与回调设计
```swift
// 推荐: Protocol delegate (强类型、可多方法)
public protocol SDKDelegate: AnyObject {
    func sdk(_ sdk: MySDK, didReceiveEvent event: SDKEvent)
    func sdk(_ sdk: MySDK, didEncounterError error: SDKError)
}

// 补充: Closure (简单单一回调)
public var onEvent: ((SDKEvent) -> Void)?

// 补充: Combine Publisher (流式数据)
public var eventPublisher: AnyPublisher<SDKEvent, Never> { ... }

// 补充: AsyncStream (现代 Swift)
public var events: AsyncStream<SDKEvent> { ... }
```
- Delegate 声明 `weak`，防止循环引用
- 提供多种回调机制满足不同集成风格
- 回调默认在主线程触发，或提供 `callbackQueue` 参数

## 三、稳定性与防御准则

### 3.1 防御性编程
- 所有 public API 入口做参数校验，不信任外部输入
- 内部异常 `catch` 后记录日志，不崩溃宿主 App
- 网络请求设置合理 timeout（默认 30s），避免无限等待
- 后台任务注册 `UIApplication.beginBackgroundTask` 防系统杀死

### 3.2 资源管理
- 使用独立 `URLSession`（自定义 `URLSessionConfiguration`）
- 数据库/文件存储隔离在 SDK 专属目录: `Library/Application Support/<SDK>/`
- UserDefaults 使用独立 suiteName: `UserDefaults(suiteName: "com.company.sdk")`
- 内存缓存用 `NSCache`（系统自动清理），非 Dictionary

### 3.3 安全准则
- 凭证/Token 存 Keychain，不用 UserDefaults 或文件
- 网络请求强制 HTTPS，启用 Certificate Pinning（可选配置）
- 日志中脱敏：不打印 token、密码、手机号等敏感信息
- 本地数据加密存储（敏感数据用 `kSecAttrAccessibleAfterFirstUnlock`）

### 3.4 性能预算
- SDK 初始化耗时 ≤ 100ms（不阻塞宿主启动）
- 运行时 CPU 占用 ≤ 5%（后台静默期）
- 内存增量 ≤ 10MB（基线状态）
- 包大小影响 ≤ 2MB（编译后 .framework/.xcframework）
- 单次网络请求 payload ≤ 100KB（批量上报做压缩）

## 四、兼容性与演进准则

### 4.1 版本策略 (SemVer)
- **MAJOR** — 删除/重命名 public API，改变行为语义
- **MINOR** — 新增功能、新增 API（向后兼容）
- **PATCH** — Bug 修复、性能优化（无 API 变化）

### 4.2 API 废弃流程
```swift
@available(*, deprecated, renamed: "trackEvent(_:properties:)")
public func track(_ name: String, _ params: [String: Any]) { ... }
```
1. 标记 `@available(*, deprecated, renamed:)` 并提供迁移指引
2. 废弃 API 至少保留一个 MINOR 版本周期
3. 下个 MAJOR 版本才真正删除

### 4.3 平台兼容
- 明确 `@available(iOS 15, macOS 12, *)` 最低版本
- 用 `#if canImport(UIKit)` / `#if os(iOS)` 隔离平台特定代码
- Swift 版本用 `Package.swift` 中 `swiftLanguageVersions` 声明

### 4.4 ObjC 互操作（如需支持）
- 需要暴露给 ObjC 的类继承 `NSObject`，方法标注 `@objc`
- 提供 `NS_SWIFT_NAME` 保持 Swift 侧命名优雅
- ObjC 不支持的特性（enum associated value、泛型）提供包装 API
