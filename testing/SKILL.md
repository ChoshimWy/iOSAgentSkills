---
name: testing
description: iOS 测试编写技能。当为 iOS 应用编写单元测试、UI 测试、为现有代码补充测试时使用。覆盖 XCTest 结构、Mock/Stub/Spy 模式、async 测试、测试命名规范、Page Object 模式的 XCUITest。
---

# iOS 测试编写

## 单元测试结构
每个测试文件对应一个被测类: `UserService` → `UserServiceTests`

```swift
final class UserServiceTests: XCTestCase {
    private var sut: UserService!
    private var mockNetwork: MockNetworkClient!
    
    override func setUp() {
        super.setUp()
        mockNetwork = MockNetworkClient()
        sut = UserService(network: mockNetwork)
    }
    
    override func tearDown() {
        sut = nil
        mockNetwork = nil
        super.tearDown()
    }
    
    func test_fetchUser_withValidID_returnsUser() async throws {
        // Given
        mockNetwork.result = User.mock()
        // When
        let user = try await sut.fetchUser(id: "1")
        // Then
        XCTAssertEqual(user.name, "Test User")
    }
}
```

## 测试命名
`test_[方法]_[条件]_[预期]`

## 覆盖场景
生成测试时必须覆盖:
- 正常路径 (happy path)
- 错误路径 (error path)
- 边界条件 (nil, 空数组, 空字符串)
- 异步行为 (async/await, Combine)

## Async 测试
- 直接用 `async throws` 函数签名
- Combine 用 `XCTestExpectation` + `wait(for:timeout:)`

## Mock / Stub / Spy 选择
- **Mock**: 验证调用次数/参数 — 加 `callCount`, `lastParams`
- **Stub**: 只需控制返回值 — 设 `result`/`error`
- **Spy**: 记录完整调用历史 — 用数组记录

## UI 测试 (XCUITest)
- Page Object 模式封装页面交互
- 所有可测试 UI 元素设置 `accessibilityIdentifier`
- 方法链式调用: `loginPage.enterEmail("...").tapLogin()`
- 用 `waitForExistence(timeout:)` 等待异步加载

## 测试数据工厂
```swift
extension User {
    static func mock(name: String = "Test") -> User {
        User(id: UUID().uuidString, name: name)
    }
}
```

## 禁止事项
- 不测试私有方法（通过公开接口间接测试）
- 不写依赖网络/文件系统的测试（用 Mock）
- 不写互相依赖的测试（每个测试独立）
- 不在测试中用 sleep（用 expectation）

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: testing`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel