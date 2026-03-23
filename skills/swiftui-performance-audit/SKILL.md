---
name: swiftui-performance-audit
description: 基于代码审查与架构分析，审计并改进 SwiftUI 运行时性能。当用户需要排查渲染缓慢、滚动卡顿、CPU 或内存过高、视图更新过多、布局抖动等问题，或在纯代码审查不足时需要引导其进行 Instruments 分析时使用。
---

# SwiftUI 性能审计

## 适用场景
- 需要诊断 SwiftUI 页面渲染缓慢、滚动掉帧或交互卡顿。
- 需要分析高 CPU、内存增长、主线程 hang、视图更新范围过大等问题。
- 需要先做代码级审计，再决定是否向用户要 Instruments 证据。

## 工作流
1. 先分类症状
- 明确是渲染慢、滚动卡、CPU 高、内存高、hang，还是视图更新过广。
- 收集目标页面代码、重现步骤、数据流以及运行环境。

2. 优先做代码审查
- 有代码时，先用 `references/code-smells.md` 做代码优先分析。
- 重点查观察范围过宽、列表 identity 不稳定、`body` 里做重计算、主线程图片解码、布局链过复杂等问题。

3. 代码证据不足时再引导 profiling
- 用 `references/profiling-intake.md` 引导用户收集 SwiftUI timeline、Time Profiler、设备和构建配置。
- 只有在代码无法解释问题时，才提高对运行时证据的要求。

4. 汇总诊断与修复
- 把问题归类为 invalidation、identity churn、layout thrash、主线程工作过重、图片代价或动画代价。
- 优先处理影响最大的瓶颈，不按“最容易解释”排序。
- 用 `references/report-template.md` 输出结论、证据、修复和验证方式。

## 参考资源
- `references/code-smells.md`：高优先级代码异味与修复方向。
- `references/profiling-intake.md`：向用户索要 profiling 证据的清单。
- `references/report-template.md`：审计报告模板。
- `references/optimizing-swiftui-performance-instruments.md`：Instruments 工作流摘要。
- `references/understanding-improving-swiftui-performance.md`：SwiftUI 性能分析与修复模式摘要。
- `references/understanding-hangs-in-your-app.md`：主线程 hang 的判断要点。
- `references/demystify-swiftui-performance-wwdc23.md`：WWDC23 性能思路摘要。

## 输出要求
- 结论必须区分“代码推测”与“trace 证据支持”。
- 至少给出：
  - 影响最大的几个问题，按严重度排序。
  - 每个问题的现象、根因、证据与修复建议。
  - 如果有 profiling 数据，给出 before/after 指标对比。
- 需要补数据时，明确告诉用户还缺什么证据。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: swiftui-performance-audit`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
