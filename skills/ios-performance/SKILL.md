---
name: ios-performance
description: iOS 性能分析与测试技能。只在需要处理 UIKit / SwiftUI 的掉帧、启动慢、CPU / 内存压力、性能回归基线、`measure(metrics:)`、`xctrace` 或 Instruments 取证时使用；如果问题核心是 crash、异常、对象未释放根因、纯静态审查或普通单元/UI 测试补齐，不要把它当作主 skill；若任务产出修改了 Apple Xcode 项目相关内容，默认以定向测试/必要验证与独立 reviewer subAgent `code-review` 放行为收口；`final-evidence-gate` / `verify-ios-build` 仅在用户显式要求或需要补强完整项目环境证据时按需使用。
---

# iOS 性能分析与测试

## Purpose

Analyze and improve iOS performance issues using the smallest credible evidence set, focusing on profiling strategy, baseline design, and before/after validation.

## 中文说明

该 Skill 负责性能基线设计、profiling 取证、模板选择、优化方向和前后对比验证。

- 适用于：掉帧、启动慢、CPU / 内存压力、性能回归、`measure(metrics:)`、`xctrace`、Instruments。
- 不适用于：普通业务实现、泛化 crash 排查、普通单元/UI 测试补齐。

## When to Use

- UIKit / SwiftUI 列表滚动掉帧、动画卡顿、页面进入慢、启动慢。
- CPU 高、内存增长、主线程繁忙、SwiftUI 更新过多。
- 需要建立 `XCTest` 性能基线，如 `measure {}`、`measure(metrics:)`、`XCTApplicationLaunchMetric`。
- 需要用 `xcrun xctrace` / Instruments 录制 `Time Profiler`、`Animation Hitches`、`Allocations`、`Leaks`、`App Launch`。

## When Not to Use

- 问题核心是 crash、异常、野指针、对象未释放根因；使用 `debugging`。
- 只是补业务单元测试、UI 测试或测试替身；使用 `testing`。
- 只是普通 SwiftUI/UIKit 功能实现；使用对应实现型 Skill。

## Agent Rules

- Always define one symptom and one target interaction before profiling.
- Distinguish baseline design from runtime evidence collection.
- Prefer Release configuration and stable device / OS baselines for comparison.
- Output should include symptom, evidence, hypothesis, optimization direction, and validation method.
- When performance fixes edit code, document non-obvious performance invariants, caching/lifecycle side effects, concurrency boundaries, and fallback behavior in touched code.
- Update stale comments and avoid adding comments that merely restate optimization syntax.
- If code changes are produced, final closure still follows targeted validation / necessary verification plus independent reviewer subAgent `code-review`; the implementation Agent must not self-review.

## Inputs

```json
{
  "goal": "Analyze iOS performance issue",
  "symptom": "scroll hitch | slow launch | cpu spike | memory growth | unknown",
  "surface": "UIKit | SwiftUI | mixed",
  "available_evidence": [],
  "constraints": []
}
```

## Outputs

```json
{
  "status": "completed | partial | blocked",
  "symptom": "...",
  "evidence": [],
  "hypotheses": [],
  "recommended_tools": [],
  "optimization_directions": [],
  "validation_plan": [],
  "known_risks": [],
  "next_action": "testing | code-review | debugging | ask-user | blocked"
}
```

## Exit Conditions

- `completed`: symptom, evidence path, optimization direction, and validation plan are all explicit.
- `partial`: useful hypotheses exist but evidence or environment is incomplete.
- `blocked`: no stable reproduction path, no usable profiling environment, or user intent is actually a different problem class.

## Escalation Rules

- Escalate to `debugging` when the issue is primarily crash, hang, leak root cause, or runtime behavior diagnosis.
- Escalate to `testing` when the next step is benchmark code, deterministic regression tests, or low-cost targeted validation.
- Escalate to `apple-docs` when official API or Instruments behavior must be confirmed.

## Token Budget

- Do not paste raw `xctrace` dumps or large logs.
- Prefer local scripts or command-line aggregation to produce compact top stacks, time windows, thread hotspots, allocation deltas, and artifact paths before handing evidence to the Agent.
- For `.trace` packages, prefer `scripts/summarize-xctrace.py` to export selected `xctrace` tables and consume `trace-summary.json` / `trace-summary.md` instead of raw XML exports.
- Prefer compact symptom summaries, selected counters, and one clear evidence thread.
- Avoid mixing unrelated hotspots into the same report.

## Reference Resources

- `scripts/summarize-xctrace.py`: exports high-signal `xctrace` tables and writes compact `trace-summary.json` / `trace-summary.md` evidence, including actionable findings, thread hotspots, stack signatures, and symbolication diagnostics.

## Relationship to Other Skills

- Use `debugging` for crash and runtime fault analysis.
- Use `testing` for test authoring and targeted benchmark execution.
- Use `ios-feature-implementation` with `advanced-swift` mode when performance work reveals deeper concurrency or abstraction implementation needs.
- Use `apple-docs` for official API and Instruments fact lookup.
