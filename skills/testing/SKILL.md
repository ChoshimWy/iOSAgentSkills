---
name: testing
description: iOS 测试编写技能。只在需要为 iOS/macOS 代码编写或补充单元测试、UI 测试、Mock/Stub/Spy 和 async 测试代码时使用；不要把“编译验证 / 构建验证 / 构建检查 / 门禁验收 / 最后验证一下能不能编译 / 跑一下 xcodebuild”误判到本 skill，这类收尾验证统一交给 `verify-ios-build`；也不要把它当作性能 benchmark / `measure(metrics:)`、代码审查或运行时排障技能；若任务产出修改了 Apple Xcode 项目相关内容，收尾必须切到 `verify-ios-build` 并在项目环境完成最终验证。
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
- 需要实际执行定向测试时，如果用户未显式指定 scheme，默认优先选择绑定了单元测试 `*Tests` target / bundle 的 scheme；若不存在，再回退到其它测试 scheme（例如 `*UITests`、`*_TEST`）。
- 如果同一任务后续还要执行 `verify-ios-build`，最终门禁默认复用这次定向测试的 workspace / scheme / destination 基线；不要无说明切换到另一个 scheme。
- 新建 `.swift`、`.h`、`.m`、`.mm` 文件且项目要求文件头时，`Created by` 必须使用本机用户名称 `Choshim.Wei`，不要写 `Codex`；日期默认使用 `YYYY/M/D`，例如 `Created by Choshim.Wei on 2026/4/11.`。
- 主要交付必须是测试代码、测试用例设计或测试替身方案；如果用户只要求跑一次门禁构建，不要用本 skill 作为主 skill。

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

## 强制收尾验证
- 只要当前任务产出修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、构建脚本、plist / entitlements / xcconfig / scheme 或项目内环境配置），最终必须切到 `verify-ios-build`。
- 最终门禁必须在目标项目根目录的项目环境执行；沙箱内的构建结果不能作为最终验收结论。
- 如果同一任务里已经跑过定向测试，`verify-ios-build` 默认复用同一套 workspace / scheme / destination 基线；不要无说明切换到不同 scheme。
- 如果用户没有显式指定 scheme，定向测试与最终门禁默认优先选择绑定了单元测试 `*Tests` target / bundle 的 scheme；若不存在，再回退到其它测试 scheme（例如 `*UITests`、`*_TEST`）。
- 对 iOS 项目，`verify-ios-build` 必须优先 `.xcworkspace`（当 `.xcworkspace` 与 `.xcodeproj` 同时存在时），并默认优先已连接真机；找不到连接中的真机时再回退到 simulator。
- 在 `verify-ios-build` 成功前，不得把任务表述为“已完成”；只能明确说明“实现已完成，但验证未完成/失败，任务未完成”。

## 与其他技能的关系
- 任务结束只需要跑一次 `xcodebuild` 做编译校验时，切换到 `verify-ios-build`。
- 需要评估代码质量和风险而不是写测试时，切换到 `code-review`。
- 需要定位运行时 crash、泄漏或卡顿时，切换到 `debugging`。
- 需要做性能基线、`measure(metrics:)`、启动性能回归或 `xctrace` / Instruments 取证时，切换到 `ios-performance`。
- 需要设计 SDK 级可测试边界时，可联动 `sdk-architecture`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: testing`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel
