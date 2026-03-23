# 性能审计输出模板

## 用途
用这个结构输出 SwiftUI 性能审计结果，让用户快速看到症状、证据、根因和下一步验证动作。

## 模板

```markdown
## Summary

[用一小段话说明最可能的瓶颈，以及该结论是基于代码还是基于 trace。]

## Findings

1. [问题标题]
   - Symptom: [用户看到的现象]
   - Likely cause: [最可能的根因]
   - Evidence: [代码引用或 profiling 证据]
   - Fix: [建议的具体改动]
   - Validation: [修复后要观察什么指标]

2. [问题标题]
   - Symptom: ...
   - Likely cause: ...
   - Evidence: ...
   - Fix: ...
   - Validation: ...

## Metrics

| Metric | Before | After | Notes |
| --- | --- | --- | --- |
| CPU | [value] | [value] | [note] |
| Frame drops / hitching | [value] | [value] | [note] |
| Memory peak | [value] | [value] | [note] |

## Next step

[给出一个明确的下一步：修复、补录 trace，或在真机验证。]
```

## 备注
- Findings 按影响排序，不按改动难度排序。
- 如果没有量化指标，也要明确指出目前缺哪些证据。
