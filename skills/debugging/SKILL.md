---
name: debugging
description: iOS 运行时排障入口：crash、异常、错误日志、对象未释放、泄漏和僵死根因诊断。不要用于构建验收、静态 review、profiling 或 Build Settings；Xcode 改动收尾交给 final-evidence-gate。
---

# iOS 调试与问题排查

## 角色定位
- 诊断型 skill。
- 负责根据症状、日志、调用栈和运行时行为定位根因，并给出复现路径、LLDB 命令和修复方向。
- 不负责替代代码审查、构建设置设计或泛化重构。

## 触发判定（硬边界）
- 至少已有日志、调用栈、错误信息、复现步骤或明确运行时症状之一时，使用本 skill。
- 如果手头只有静态 diff、没有运行时证据，主 skill 应切换到 `code-review`。
- 如果问题核心是 benchmark、`measure(metrics:)`、`xctrace`、Instruments、掉帧或启动性能，不要用本 skill 作为主 skill，切换到 `ios-performance`。

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

## 最终证据门禁
- 只要当前任务产出修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、构建脚本、plist / entitlements / xcconfig / scheme 或项目内环境配置），最终必须进入 `final-evidence-gate`；证据不足、高风险或命中工程/依赖/签名/资源打包类改动时，再切到 `verify-ios-build`。
- 最终验证证据必须来自目标项目根目录的项目环境；沙箱内的构建结果不能作为最终验收结论。
- 对 iOS 项目，若升级到 `verify-ios-build`，必须优先 `.xcworkspace`（当 `.xcworkspace` 与 `.xcodeproj` 同时存在时），并默认优先已连接真机；找不到连接中的真机时再回退到 simulator。
- 在 `final-evidence-gate` 接受现有证据或 `verify-ios-build` 成功前，不得把任务表述为“已完成”；只能明确说明“实现已完成，但验证证据不足/验证失败，任务未完成”。

## 与其他技能的关系
- 只是静态代码质量审查时，切换到 `code-review`。
- 掉帧、启动慢、CPU / 内存异常、`measure(metrics:)`、`xctrace` 或 Instruments 模板选择等性能问题，优先切换到 `ios-performance`。
- 需要构建签名、Archive、导出或 CI 配置时，切换到 `xcode-build`。
- 需要直接整理实现代码而非定位运行时根因时，切换到 `refactoring`、`swiftui-feature-implementation` 或其它实现型 skill。
