---
name: refactoring
description: 代码重构技能。当用户要求重构代码、或代码存在长方法/重复代码/深层嵌套/回调地狱/God Object 等异味时使用。提供 9 种代码异味识别和对应重构手法，包括提取方法、Guard Clause、async/await 转换、协议注入、策略模式等。
---

# 代码重构

## 代码异味识别
阅读代码时自动检测：

| 异味 | 触发条件 | 重构手法 |
|------|---------|---------|
| 长方法 | 函数 > 40 行 | 提取方法 (Extract Method) |
| 长参数列 | 参数 > 4 个 | 提取参数对象 (Parameter Object) |
| 重复代码 | 相似逻辑 2+ 次 | 提取方法 + 泛型/协议 |
| 过大的类 | 文件 > 400 行 | 拆分类 (Extract Class) |
| 深层嵌套 | 缩进 > 3 层 | Guard Clause + Early Return |
| Switch 散落 | 相同 switch 多处出现 | 协议多态 |
| 回调地狱 | 嵌套回调 > 2 层 | async/await |
| God Object | 一个类太多职责 | 按职责拆分 |
| 硬依赖 | 直接引用具体类/单例 | 提取协议 + 依赖注入 |

## 安全原则
1. 重构 commit 不混合功能改动
2. 每次一小步，确保编译通过
3. 有测试的代码优先重构，重构后跑测试验证

## 常用重构手法

### 提取方法
```swift
// Before: 60 行方法
func processOrder() { ... }
// After: 清晰的步骤
func processOrder() throws {
    try validateOrder()
    let total = calculateTotal()
    try submitOrder(total: total)
}
```

### Guard 消除嵌套
```swift
// Before
if let user = user { if user.isVerified { ... } }
// After
guard let user else { return }
guard user.isVerified else { throw Error.unverified }
```

### 回调 → async/await
```swift
// Before
func fetch(completion: @escaping (Result) -> Void) {
    a { result in b { result in c { ... } } }
}
// After
func fetch() async throws -> Result {
    let a = try await fetchA()
    let b = try await fetchB(a)
    return try await fetchC(b)
}
```

### 提取协议 (依赖注入)
```swift
// Before
class VM { let service = NetworkService.shared }
// After
class VM {
    private let service: NetworkServiceProtocol
    init(service: NetworkServiceProtocol = NetworkService.shared) { ... }
}
```

## 输出格式
```
🔄 异味: [类型]
📍 位置: [文件:方法]
🔧 重构: [手法]
📝 改动: [改什么，怎么改]
```

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: refactoring`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel