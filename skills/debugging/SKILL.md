---
name: debugging
description: iOS/macOS 运行时调试与问题排查 Skill。用于 crash、异常、运行时错误、对象未释放、内存泄漏、Watchdog、卡死、行为异常等有运行时症状的问题；不要把编译验证、静态代码审查、性能 profiling、benchmark 或构建配置误判到本 Skill。
---

# iOS 调试与问题排查

## Purpose

Diagnose iOS/macOS runtime failures using symptoms, logs, stack traces, reproduction steps, and runtime evidence, then provide root-cause analysis, focused fixes, and verification guidance.

## 中文说明

该 Skill 是运行时排障专项 Skill。

负责：
- 分析 crash、异常、运行时错误。
- 定位对象未释放、内存泄漏、僵尸对象、循环引用。
- 分析 Watchdog、主线程阻塞、死锁、卡死。
- 根据日志、调用栈、复现步骤和运行时行为判断根因。
- 给出 LLDB、Memory Graph、Instruments 排查路径。
- 给出修复方案和防御建议。

不负责：
- 静态 diff 代码审查。
- 编译验证或构建门禁。
- 性能 benchmark / profiling。
- 构建设置、签名、Archive、CI 配置。
- 泛化重构或无症状代码优化。

## When to Use

Use this Skill when at least one runtime signal exists:

- Crash log.
- Symbolicated or unsymbolicated stack trace.
- Exception name or error message.
- Reproduction steps.
- Console log.
- LLDB output.
- Memory Graph evidence.
- User-visible runtime symptom.
- Object not deallocated.
- Watchdog / hang / deadlock symptom.

## When Not to Use

Do not use this Skill when:

- Only static diff exists and no runtime symptom is known; use `code-review`.
- The request is final compile/build verification; use `final-evidence-gate` / `verify-ios-build`.
- The request is benchmark, dropped frames, startup time, CPU trace, `xctrace`, or Instruments workflow; use `ios-performance`.
- The request is signing, Archive, Export, CI, build settings, destination policy; use `xcode-build`.
- The request is writing tests; use `testing`.
- The request is compact attribution of a build/test failure artifact rather than runtime diagnosis; use `ios-build-log-digest`.
- The request is implementing a feature without runtime failure; use an implementation Skill.

## Agent Rules

### Evidence Rules

- Start from runtime evidence, not speculation.
- Identify symptom type before proposing fixes.
- Prefer crash thread and first app-owned frame.
- If evidence is missing, state the missing evidence explicitly.
- If root cause is inferred, mark it as probable rather than proven.
- Do not claim a crash is fixed without reproduction or validation evidence.
- Do not paste huge logs; extract the smallest relevant stack or error section.

### Root Cause Rules

- Separate symptom, trigger, root cause, and fix.
- Distinguish current-change regression from pre-existing issue when possible.
- For async/concurrency issues, inspect actor/main-thread boundaries, shared mutable state, callback queue, cancellation, and lifecycle.
- For memory leaks, inspect closure captures, delegates, timers, NotificationCenter, KVO, Combine/Rx subscriptions, CADisplayLink, retain cycles, and view-controller lifecycle.
- For Objective-C interop issues, inspect selector names, optional protocol methods, dynamic dispatch, KVC/KVO, nullability, and bridging.
- For UI lifecycle issues, inspect view loading, containment, presentation/dismissal, reuse, and thread confinement.

### Validation Rules

- After proposing a fix, include the narrowest validation path.
- If code changes are made, default closure still requires targeted validation / necessary verification and `code-review`.
- `final-evidence-gate` / `verify-ios-build` are optional strengthening steps only when explicitly requested or risk requires it.
- Do not auto-upgrade to full build, simulator, or real-device validation for every debugging task.

### Token Budget

- Do not read full raw build logs by default.
- Do not dump full crash archives if a stack trace is enough.
- Do not paste full console logs.
- Prefer minimal stack, first app frame, exception reason, device/OS/app version, and reproduction steps.
- For build/test failure logs encountered during debugging, use `ios-build-log-digest`.

## Symptom Classification

| Symptom | Common Causes | First Checks |
| --- | --- | --- |
| `EXC_BAD_ACCESS` | Use-after-free, unsafe pointer, invalid memory access, data race | Zombie objects, memory graph, thread access, first app frame |
| `EXC_BAD_INSTRUCTION` | `fatalError`, `preconditionFailure`, forced unwrap, invalid cast | Assertion site, optional chain, type assumptions |
| `SIGABRT` | `NSException`, unrecognized selector, Auto Layout exception, KVC issue | Exception reason, ObjC selector, view hierarchy |
| `Watchdog` | Main thread blocked, deadlock, long launch/background task | Main thread stack, synchronous I/O, locks, launch work |
| Object not deallocated | Retain cycle, timer, delegate, subscription, notification | Memory Graph, closure captures, dispose/cancel lifecycle |
| UI freeze | Main thread work, layout loop, lock contention | main thread backtrace, runloop, layout invalidation |
| Async wrong state | Race, cancellation, callback order, actor boundary | task lifetime, state machine, main actor, cancellation path |

## Inputs

Expected input contract:

```json
{
  "symptom": "crash | exception | leak | hang | wrong_behavior | unknown",
  "logs": [],
  "stack_trace": "optional",
  "exception_reason": "optional",
  "reproduction_steps": [],
  "device": "optional",
  "os_version": "optional",
  "app_version": "optional",
  "changed_files": [],
  "recent_changes": [],
  "constraints": []
}
```

Minimal useful input:

```json
{
  "symptom": "crash",
  "stack_trace": "...",
  "reproduction_steps": ["..."]
}
```

## Outputs

Return compact structured output:

```json
{
  "status": "diagnosed | probable | needs-more-evidence | fixed | blocked",
  "symptom_type": "crash | exception | leak | hang | wrong_behavior | unknown",
  "location": "File.swift:method:line | unknown",
  "first_app_frame": "optional",
  "root_cause": "...",
  "confidence": "high | medium | low",
  "evidence": [],
  "fix_plan": [],
  "defensive_changes": [],
  "validation_plan": [],
  "residual_risk": [],
  "next_action": "fix | collect-evidence | run-targeted-validation | code-review | blocked"
}
```

## Exit Conditions

Return `diagnosed` when:

- Symptom type is clear.
- Root cause is supported by runtime evidence.
- Location or first app-owned frame is identified.
- Fix and validation plan are specific.

Return `probable` when:

- Evidence points strongly to one cause but reproduction or stack details are incomplete.
- The answer clearly marks uncertainty.

Return `needs-more-evidence` when:

- Logs, stack trace, reproduction steps, or environment details are insufficient.
- Multiple plausible root causes remain.

Return `fixed` when:

- A fix was applied and narrow validation or reproduction verification supports it.
- Remaining risks are disclosed.

Return `blocked` when:

- Required runtime evidence, device access, crash log, symbols, credentials, or reproduction environment is unavailable.

## Escalation Rules

Escalate to `code-review` when:

- There is no runtime evidence and only static diff exists.
- The next step is quality/risk review after a debugging fix.

Escalate to `ios-performance` when:

- The issue is primarily frame drops, startup time, CPU/memory benchmark, energy, `xctrace`, or Instruments evidence.

Escalate to `testing` when:

- A regression test should be added after identifying the root cause.
- A deterministic unit/UI test can reproduce the bug.

Escalate to `ios-build-log-digest` when:

- The failure is actually a build/test log issue and compact log attribution is needed.

Escalate to `verify-ios-build` only when:

- The user explicitly asks for project-environment verification.
- `final-evidence-gate` determines the debugging fix needs full build evidence.

Escalate to implementation/refactoring Skills when:

- Root cause is clear and code changes are needed.

## Reporting Format

```text
🔍 问题类型: crash | exception | leak | hang | wrong_behavior
📍 位置: File.swift:method:line | unknown
🧩 首个 App 栈帧: ...
💡 根因分析: ...
📎 证据: ...
🔧 修复方案: ...
🛡️ 防御建议: ...
✅ 验证计划: ...
⚠️ 残余风险: ...
```

If evidence is insufficient:

```text
当前无法确认根因。
缺少证据:
- symbolicated crash stack
- reproduction steps
- device / OS version
下一步: collect-evidence
```

## Useful Commands

LLDB:

```text
bt
bt all
po <variable>
expr <expression>
thread backtrace all
image lookup -a <address>
```

Memory / lifecycle:

```text
Memory Graph
Zombies
Malloc Stack Logging
Leaks instrument
Allocations instrument
```

## Reference Resources

- `references/memory-leak.md`: common leak patterns and Memory Graph usage.

## Relationship to Other Skills

- Static review only: use `code-review`.
- Performance profiling or benchmark: use `ios-performance`.
- Build verification: use `verify-ios-build`.
- Build/test log attribution: use `ios-build-log-digest`.
- Test writing: use `testing`.
- Build/signing/archive/CI: use `xcode-build`.
- Code implementation after diagnosis: use `refactoring`, `ios-feature-implementation`, `swiftui-feature-implementation`, or `uikit-feature-implementation`.
