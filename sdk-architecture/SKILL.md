---
name: sdk-architecture
description: SDK/Framework 架构设计技能。当设计 SDK 架构、模块划分、对外 API、SDK 入口类、Configuration、分发策略时使用。也适用于为 SDK 编写测试、设计可测试架构、创建 Mock/Stub 时触发。覆盖分层架构、SPM 模块化、XCFramework 分发。
---

# SDK 架构设计

## 设计原则
1. **最小暴露** — 只暴露必要的 public API
2. **最小依赖** — 尽量零外部依赖，避免冲突
3. **透明无侵入** — 不 swizzle 宿主方法，不修改全局设置，异常内部吞掉
4. **向后兼容** — 旧 API 废弃但不删除，breaking change 走 major 版本

## 分层架构
```
Public API Layer   — 宿主唯一接触点 (SDK入口, Configuration, 公开Model)
Feature Layer      — 功能模块 (各业务功能)
Core Layer         — 基础设施 (Network, Storage, Logger)
Platform Layer     — 系统适配 (iOS/macOS 特定代码)
```
依赖方向：上层依赖下层，下层不依赖上层。

## SDK 入口类模式
```swift
public final class MySDK {
    public static let version = "x.y.z"
    public static let shared = MySDK()
    public private(set) var isInitialized = false
    private init() {}
    
    public func initialize(with config: Configuration) throws { ... }
    public func shutdown() { ... }
}
```
- 入口类 `final class`，单例模式
- `initialize` 检查重复初始化，验证 configuration
- 提供 `shutdown` 释放资源

## Configuration 设计
- 必填参数放 init，可选参数用属性默认值
- 提供 `Environment` enum: `.development`, `.staging`, `.production`
- 网络 timeout、日志级别等作为可选配置

## 内部组件
- 网络层: 独立 `URLSession`（不影响宿主），不用 `.shared`
- 日志: 内部 Logger，支持级别控制和外部自定义 handler
- 错误: `SDKError` enum，含 errorCode 便于排查

## 分发
- 优先 SPM，次选 CocoaPods
- Package.swift 按功能拆分 target（Core + 可选模块）
- 二进制分发用 XCFramework (真机 + 模拟器)
- 版本号遵循 SemVer: MAJOR.MINOR.PATCH

## 详细参考
- **设计准则**: 参见 [references/design-guidelines.md](references/design-guidelines.md) — API 设计准则、架构准则、稳定性/防御/安全准则、性能预算、版本演进策略
- **测试策略**: 参见 [references/sdk-testing.md](references/sdk-testing.md) — 可测试设计、Mock 模式、覆盖率目标


## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: sdk-architecture`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel