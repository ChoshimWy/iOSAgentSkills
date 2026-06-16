---
name: ios-sdk-architecture
description: iOS SDK / Framework 架构设计 Skill。用于设计模块边界、Public API、入口类、Configuration、依赖方向、可测试架构、SPM/XCFramework 分发和版本演进；不要用于普通 App 页面实现、一次性构建验证、性能取证或纯测试补写。
---

# iOS SDK 架构设计

## Purpose

Design iOS SDK / Framework architecture with stable public APIs, clear module boundaries, testable seams, versioning strategy, and distribution plans.

## 中文说明

该 Skill 是 iOS SDK / Framework 架构设计专项 Skill。

负责：
- SDK 分层与模块边界。
- Public API 设计。
- SDK 入口类与生命周期。
- Configuration / Options / Environment。
- 错误、日志、指标、回调和事件流。
- Mock / Stub / Fake 注入点。
- SPM / XCFramework 分发。
- SemVer 与 breaking change 策略。

不负责：
- 普通 App feature 实现。
- SwiftUI/UIKit 页面实现。
- 单纯补测试。
- 一次性项目构建验证。
- 签名、Archive、Export、CI 设计。

## When to Use

Use this Skill when the task involves:

- SDK 架构设计。
- Framework 模块拆分。
- Public API / open API 边界。
- SDK 入口类、初始化、关闭与生命周期。
- Configuration / dependency injection 设计。
- SPM / XCFramework 分发策略。
- SDK 可测试性、Mock 注入点、示例 App 验证。
- 多平台边界或二进制兼容策略。
- 版本演进、deprecation、breaking change 管理。

## When Not to Use

Do not use this Skill when:

- The task is normal App business implementation; use `ios-feature-implementation`.
- The task is SwiftUI page implementation; use `ios-feature-implementation` with `swiftui` mode.
- The task is UIKit page implementation; use `ios-feature-implementation` with `uikit` mode.
- The task is writing tests only; use `testing`.
- The task is build/signing/archive/export/CI only; use `xcode-build`.
- The task is one-off build verification; use `verify-ios-build`.
- The task is runtime debugging; use `debugging`.
- The task is advanced Swift implementation only; use `ios-feature-implementation` with `advanced-swift` mode.

## Agent Rules

### Architecture Rules

- Expose the minimum necessary public API.
- Keep implementation details internal.
- Default dependency direction: `Public API Layer -> Feature Layer -> Core Layer -> Platform Layer`.
- Public API layer should not depend on concrete platform implementation details.
- Entry types own initialization, lifecycle, configuration validation, and high-level coordination only.
- Do not put business implementation detail into the entry type.
- Keep side effects explicit and observable.
- Prefer dependency injection over hidden singletons.

### API Design Rules

- Public/open APIs must include `///` documentation.
- Public APIs must define input, output, error, concurrency, side-effect, and availability semantics.
- Breaking changes must be explicit and paired with version strategy.
- Avoid leaking implementation types through public signatures.
- Prefer stable value types for configuration.
- Keep callbacks, async streams, delegates, and closures lifecycle-safe.

### Distribution Rules

- Prefer SPM source distribution unless binary distribution is required.
- Use XCFramework for binary distribution.
- Document platform and architecture support.
- Document resource bundling strategy.
- Document sample app or integration test strategy.
- Versioning should follow SemVer.

### Testability Rules

- Define seams for network, persistence, BLE, device, clock, queue, logger, metrics, and transport dependencies.
- Provide mock/stub/fake protocols where they improve deterministic tests.
- Do not over-abstract single-use internal implementation.
- SDK APIs should be testable without requiring real devices unless the capability inherently requires hardware.

### File Header Rules

When adding `.swift`, `.h`, `.m`, `.mm` files and the project requires headers:

- `Created by` must use local `whoami`.
- Do not write `Codex`.
- Date format: `YYYY/M/D`.

### Validation Handoff Rules

- SDK architecture changes should route to `testing` for test impact and then independent reviewer subAgent `code-review`; the implementation/design Agent must not self-review.
- Consumer app integration evidence may require `final-evidence-gate` / `verify-ios-build` only when risk or user request requires it.
- Distribution, signing, archive, and CI strategy routes to `xcode-build`.

### Token Budget

- Do not paste huge architecture docs or full source trees.
- Prefer module diagrams, public API examples, and concise contracts.
- Keep examples focused on entry class, configuration, public protocol, and dependency direction.
- Do not read full build logs; use diagnostics summaries when needed.

## Inputs

Expected input contract:

```json
{
  "goal": "Design iOS SDK architecture",
  "sdk_name": "optional",
  "target_platforms": ["iOS"],
  "distribution": "SPM | XCFramework | CocoaPods | mixed | unknown",
  "public_api_requirements": [],
  "module_requirements": [],
  "testability_requirements": [],
  "constraints": []
}
```

## Outputs

Return compact structured output:

```json
{
  "status": "completed | partial | blocked",
  "sdk_name": "...",
  "public_api_surface": [],
  "module_boundaries": [],
  "dependency_direction": "Public API -> Feature -> Core -> Platform",
  "entry_points": [],
  "configuration_model": [],
  "testability_plan": [],
  "distribution_plan": [],
  "versioning_plan": [],
  "changed_files": [],
  "known_risks": [],
  "test_impact": "...",
  "no_test_reason": null,
  "next_action": "testing | code-review | xcode-build | ask-user | blocked"
}
```

## Exit Conditions

Return `completed` when:

- Public API surface is defined.
- Module boundaries and dependency direction are defined.
- Entry lifecycle and configuration model are defined.
- Testability, distribution, and versioning plans are clear.
- Test impact or `no_test_reason` is provided.

Return `partial` when:

- A useful architecture direction is defined but platform, distribution, API, or product constraints remain incomplete.

Return `blocked` when:

- Required SDK requirements, distribution constraints, public API decisions, or platform support matrix are missing.

## Escalation Rules

Escalate to `ios-feature-implementation` with `advanced-swift` mode when:

- The main issue is complex generics, actor isolation, Sendable, type erasure, or availability strategy.

Escalate to `ios-feature-implementation` when:

- Architecture is settled and normal implementation is next.

Escalate to `testing` when:

- Test seams, mocks, integration tests, or coverage strategy need implementation.

Escalate to `code-review` when:

- Public API and architecture quality need review.

Escalate to `xcode-build` when:

- SPM/XCFramework/build/signing/archive/export/CI mechanics are the main task.

Escalate to `verify-ios-build` only when:

- User explicitly requests project-environment verification or `final-evidence-gate` requires it.

## Reporting Format

```text
SDK architecture status: completed | partial | blocked
SDK name: ...
Public API surface:
- ...
Module boundaries:
- ...
Dependency direction:
- ...
Entry points:
- ...
Configuration model:
- ...
Testability plan:
- ...
Distribution plan:
- ...
Versioning plan:
- ...
Known risks:
- ...
Next: testing -> reviewer subAgent(code-review)
```

## Reference Resources

- `references/design-guidelines.md`: API design, stability, safety, and version evolution.
- `references/sdk-testing.md`: SDK testability design, mock patterns, and coverage targets.

## Relationship to Other Skills

- Normal App implementation: `ios-feature-implementation`.
- Advanced Swift implementation: `ios-feature-implementation` with `advanced-swift` mode.
- Test implementation: `testing`.
- Static review: `code-review`.
- Build/distribution mechanics: `xcode-build`.
- Final project-environment evidence: `final-evidence-gate` / `verify-ios-build`.
