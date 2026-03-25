---
name: debugging
description: iOS 调试与问题排查技能。只在遇到 crash、异常、运行时错误、内存泄漏、ViewController 未释放、僵死等问题并需要诊断根因时使用；不要把它当作静态 code review、性能分析测试或构建配置技能。
---

# iOS 调试与问题排查

## 角色定位
- 诊断型 skill。
- 负责根据症状、日志、调用栈和运行时行为定位根因，并给出复现路径、LLDB 命令和修复方向。
- 不负责替代代码审查、构建设置设计或泛化重构。

## 适用场景
- 需要分析 crash、异常、僵死、主线程阻塞、内存泄漏、视图未释放。
- 需要根据错误日志、符号化栈或复现步骤定位问题。
- 需要给出 LLDB 命令、Memory Graph / Instruments 排查路径。

## 核心工作流
1. 先识别症状类型

| 异常类型 | 常见原因 | 排查方向 |
| --- | --- | --- |
| `EXC_BAD_ACCESS` | 野指针、`nil` 解包、数组越界 | 检查可选值解包、数组边界、多线程访问 |
| `EXC_BAD_INSTRUCTION` | `fatalError`、`preconditionFailure` | 检查断言、强制解包、边界条件 |
| `SIGABRT` | `NSException`、`unrecognized selector` | 查看异常信息、检查 ObjC 互操作 |
| `Watchdog` | 主线程阻塞超时 | 检查主线程同步 I/O、死锁、长事务 |

2. 再做根因定位
- 先看异常类型和崩溃线程调用栈。
- 再回到上下文代码，确认触发条件和共享状态。
- 缺少运行时证据时，明确写出“当前是高概率推断”。

3. 最后给出修复与防御
- 修复方案必须尽量具体，优先给可执行改法。
- 同时给出防御建议，避免问题以不同形式再次出现。

## 参考资源
- `references/memory-leak.md`：常见泄漏模式与 Memory Graph 使用。
- 常用 LLDB 命令：`po <变量>`、`bt`、`bt all`、`expr <表达式>`。

## 输出要求
- 默认按以下格式输出：

```text
🔍 问题类型: [类型]
📍 位置: [文件:方法:行]
💡 根因分析: [分析]
🔧 修复方案: [代码或修改建议]
🛡️ 防御建议: [如何预防]
```

- 如果无法定位到行号，必须说明还缺什么证据。

## 与其他技能的关系
- 只是静态代码质量审查时，切换到 `code-review`。
- 掉帧、启动慢、CPU / 内存异常、`measure(metrics:)`、`xctrace` 或 Instruments 模板选择等性能问题，优先切换到 `ios-performance`。
- 需要构建签名、Archive、导出或 CI 配置时，切换到 `xcode-build`。
- 需要直接整理实现代码而非定位运行时根因时，切换到 `refactoring`、`swiftui-view-refactor` 或其它实现型 skill。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定本 Skill 已被加载并用于当前任务时，在回复末尾追加：
`// skill-used: debugging`

规则：
- 只能输出一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的硬性规则与交付格式
- 只有当任务与本 skill 的 description 明显匹配时才允许输出 sentinel
