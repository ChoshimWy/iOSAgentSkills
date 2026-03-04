# SDK 测试策略参考

## 测试比例目标
- Unit Tests: 75% (核心逻辑全覆盖)
- Integration Tests: 20% (模块间交互)
- E2E Tests: 5% (关键链路端到端)

## 可测试设计原则
1. **依赖协议，不依赖具体类** — 所有外部依赖通过 Protocol 注入
2. **init 注入** — 依赖通过 init 传入，生产用默认值，测试传 Mock
3. **不直接用单例** — 封装后注入

```swift
class UserService {
    private let network: NetworkClientProtocol
    init(network: NetworkClientProtocol = NetworkClient()) {
        self.network = network
    }
}
```

## Mock 生成模式
```swift
class MockNetworkClient: NetworkClientProtocol {
    var result: Any?
    var error: Error?
    var callCount = 0
    var lastEndpoint: Endpoint?
    
    func request<T: Decodable>(_ endpoint: Endpoint) async throws -> T {
        callCount += 1
        lastEndpoint = endpoint
        if let error { throw error }
        return result as! T
    }
}
```

## 测试命名
`test_[方法]_[条件]_[预期]`

## 测试结构
Given / When / Then:
```swift
func test_xxx() async throws {
    // Given - 准备数据和 mock
    // When  - 执行操作
    // Then  - 验证结果
}
```

## setUp / tearDown
- setUp 创建 sut 和所有 mock
- tearDown 置 nil 确保清理
- sut 用 `var sut: Type!` 声明

## 测试数据工厂
```swift
extension User {
    static func mock(id: String = "test", name: String = "Test User") -> User {
        User(id: id, name: name)
    }
}
```

## 覆盖率目标
| 层级 | 目标 |
|------|------|
| Public API | ≥ 95% |
| Core 逻辑 | ≥ 85% |
| 网络层 | ≥ 80% |
| 工具类 | ≥ 90% |
