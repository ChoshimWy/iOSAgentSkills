---
name: testing
description: iOS/macOS 测试编写入口：单元测试、UI 测试、Mock/Stub/Spy 与 async 测试。不要用于构建验收、性能 profiling、代码审查或运行时排障；Xcode 改动收尾交给 final-evidence-gate。
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
- 非编排 / 单 Agent 的实现型任务进入固定四步链路时，作为实现之后、`code-review` 之前的第二步测试阶段。

## 核心规则
- 测试命名使用 `test_[方法]_[条件]_[预期]`。
- 至少覆盖正常路径、错误路径、边界条件和异步行为。
- 每个测试彼此独立，不依赖网络、文件系统或 `sleep`。
- 优先通过公开接口间接覆盖行为，不直接测试私有方法。
- 需要实际执行定向测试时，如果用户未显式指定 scheme，默认优先选择绑定了单元测试 `*Tests` target / bundle 的 scheme；若不存在，再回退到其它测试 scheme（例如 `*UITests`、`*_TEST`）。
- 本地执行 `xcodebuild`（含 `-list` / `-showdestinations` / build/test）默认在项目环境直接执行（CC 使用 `Bash` 工具；Codex 使用 `functions.exec_command` + `require_escalated`）。
- 同机同仓如果有多个 Codex / Claude CLI 并发处理同一 Xcode 项目，测试阶段的项目环境 `xcodebuild` 也应统一复用串行包装入口排队执行：优先目标项目根目录的 `codex_verify.sh`，若项目未接入则回退到本机 `~/.codex/bin/codex_verify`，避免并发锁冲突。
- 本地缓存统一复用 Xcode 系统 DerivedData（`~/Library/Developer/Xcode/DerivedData`），不要改用临时 `-derivedDataPath`。
- 如果同一任务后续还要进入 `final-evidence-gate`，最终证据门禁默认复用这次定向测试的 workspace / scheme / destination 基线；不要无说明切换到另一个 scheme。
- 如果当前改动不适合新增测试代码，也必须在本阶段明确给出 `no_test_reason` 与已覆盖的验证依据，然后再进入 `code-review` 与 `final-evidence-gate`。
- 新建 `.swift`、`.h`、`.m`、`.mm` 文件且项目要求文件头时，`Created by` 必须使用本机用户名称（`whoami` 输出），不要写 `Codex`；日期默认使用 `YYYY/M/D`，例如 `Created by $(whoami) on 2026/4/11.`。
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
- 默认使用以下结构化字段：

```text
suggested_validation:
  - ...
executed_validation:
  - ...
failure_attribution: <none|失败归因结论>
needs_test_code: <yes|no>
first_failure: <none|首个真实失败点>
no_test_reason: <仅当未新增测试代码时填写>
```

- 字段规则：
  - `suggested_validation` 写下一步建议执行的定向验证。
  - `executed_validation` 只写本轮实际已执行验证与结果摘要。
  - `failure_attribution` 只写与当前改动相关的失败归因，不扩展到未经证据支持的推断。
  - `needs_test_code` 为 `no` 且未新增测试代码时，必须补 `no_test_reason` 与验证依据。
  - 若本轮存在阻塞失败，`first_failure` 填首个真实失败点；否则写 `none`。
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

## 最终证据交接
- 只要当前任务产出修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、构建脚本、plist / entitlements / xcconfig / scheme 或项目内环境配置），最终必须进入 `final-evidence-gate`；证据不足、高风险或命中工程/依赖/签名/资源打包类改动时，再切到 `verify-ios-build`。
- 若本阶段执行了 `xcodebuild test/build`，该证据必须来自目标项目根目录的项目环境；沙箱内的构建结果不能作为最终验收结论。
- 如果同一任务里已经跑过定向测试，`final-evidence-gate` 默认复用同一套 workspace / scheme / destination 基线；不要无说明切换到不同 scheme。
- 如果用户没有显式指定 scheme，定向测试与最终证据默认优先选择绑定了单元测试 `*Tests` target / bundle 的 scheme；若不存在，再回退到其它测试 scheme（例如 `*UITests`、`*_TEST`）。
- 对 iOS 项目，最终证据默认优先 `.xcworkspace`（当 `.xcworkspace` 与 `.xcodeproj` 同时存在时）；低风险逻辑改动可接受 simulator 测试证据；高风险或设备能力相关场景需由 `final-evidence-gate` 升级，并默认优先已连接真机。
- 在 `final-evidence-gate` 接受现有证据或 `verify-ios-build` 成功前，不得把任务表述为“已完成”；只能明确说明“实现已完成，但验证证据不足/验证失败，任务未完成”。

## 与其他技能的关系
- 如果当前任务属于非编排 / 单 Agent 的实现链路，本 skill 默认承接实现后的第二步；无论是否新增测试代码，都要给出测试结论或 `no_test_reason`，然后固定进入 `code-review`，由审查阶段决定是否放行 `final-evidence-gate`。
- 任务结束只需要裁决现有验证是否足够时，切换到 `final-evidence-gate`；明确需要补跑项目环境构建时，才切换到 `verify-ios-build`。
- 需要评估代码质量和风险而不是写测试时，切换到 `code-review`。
- 需要定位运行时 crash、泄漏或卡顿时，切换到 `debugging`。
- 需要做性能基线、`measure(metrics:)`、启动性能回归或 `xctrace` / Instruments 取证时，切换到 `ios-performance`。
- 需要设计 SDK 级可测试边界时，可联动 `sdk-architecture`。
