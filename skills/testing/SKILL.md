---
name: testing
description: iOS 测试编写技能。只在需要为 iOS/macOS 代码编写或补充单元测试、UI 测试、Mock/Stub/Spy 和 async 测试时使用；不要把它当作一次性 `xcodebuild` 构建校验、代码审查或运行时排障技能。
---

# iOS 测试编写

## 角色定位
- 专项型 skill。
- 负责补齐单元测试、UI 测试、测试替身和异步测试结构。
- 不负责简单构建收尾校验，也不替代代码审查和运行时调试。

## 适用场景
- 为现有业务逻辑补单元测试。
- 为交互流程补 `XCUITest` 或 Page Object 封装。
- 需要设计 `Mock`、`Stub`、`Spy` 或异步测试用例。

## 核心规则
- 测试命名使用 `test_[方法]_[条件]_[预期]`。
- 至少覆盖正常路径、错误路径、边界条件和异步行为。
- 每个测试彼此独立，不依赖网络、文件系统或 `sleep`。
- 优先通过公开接口间接覆盖行为，不直接测试私有方法。

## 常用模式
- `Mock`：验证调用次数或参数，使用 `callCount`、`lastParams`。
- `Stub`：控制返回值或错误，使用 `result` / `error`。
- `Spy`：记录完整调用历史，使用数组保存输入。
- `XCUITest`：使用 Page Object、`accessibilityIdentifier` 和 `waitForExistence(timeout:)`。

## 输出要求
- 默认给出或补齐：
  - 被测对象与测试文件的对应关系。
  - 关键测试场景清单。
  - 测试替身设计。
  - 必要的 `async` 或 UI 测试等待策略。
- 示例模式可参考：

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
        mockNetwork.result = User.mock()
        let user = try await sut.fetchUser(id: "1")
        XCTAssertEqual(user.name, "Test User")
    }
}
```

## 与其他技能的关系
- 任务结束只需要跑一次 `xcodebuild` 做编译校验时，切换到 `verify-ios-build`。
- 需要评估代码质量和风险而不是写测试时，切换到 `code-review`。
- 需要定位运行时 crash、泄漏或卡顿时，切换到 `debugging`。
- 需要设计 SDK 级可测试边界时，可联动 `sdk-architecture`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: testing`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel
