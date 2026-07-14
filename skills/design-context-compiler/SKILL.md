---
name: design-context-compiler
description: iOS Design Context Compiler Skill。用于把明确的 Figma / Sketch / 人工设计证据归一化为 Canonical UI IR，校验设计真源、布局意图、token、状态、交互和 unknowns，解析 UIKit / SwiftUI 组件绑定，并按 screen / region / component 生成低 Token Agent Packet；也用于执行 screenshot-only、UI IR、UI IR+Binding 的收益基准。不要用于视觉方向探索、直接编写产品 UI、截图执行或最终视觉验收。
---

# Design Context Compiler

## Purpose

Convert traceable design evidence into a validated, task-scoped iOS implementation contract without passing raw design-tool JSON or a full-screen context dump to the implementation agent.

## 中文说明

本 Skill 负责设计到 iOS 实施之间的编译层：

- 保存可审计的 Design Evidence。
- 生成以 JSON 为单一事实源的 Canonical UI IR。
- 校验 Geometry Intent、tokens、组件语义、状态、交互、响应式、无障碍和 unknowns。
- 解析 iOS Component Registry / bindings。
- 按任务裁剪 Agent Packet，并明确 context budget。
- 用 benchmark 证明 UI IR / binding 是否真实提升首轮还原质量。

不直接编写 UIKit / SwiftUI 产品代码，不替代 `ui-ux-design-system` 的设计探索，不替代 `ios-automation` 的截图执行，也不替代 `ios-verification` / `code-review` 的最终门禁。

## When to Use

Use this Skill when:

- 用户要求把 Figma / Sketch 设计证据转换为可实现的 iOS UI 语义合同。
- 已有 Design-to-Code Spec，需要归一化为稳定 Schema。
- 需要校验 `ui-ir.json`、`agent-packet.json` 或 benchmark manifest。
- 需要为单个 screen / region / component 裁剪低 Token 上下文。
- 需要建立或解析设计组件到 UIKit / SwiftUI symbol 的绑定。
- 需要对比 screenshot-only、UI IR、UI IR+Binding 三种输入的收益。

## When Not to Use

Do not use this Skill when:

- 任务是视觉方向、色板、字体或设计评审；使用 `ui-ux-design-system`。
- 任务是直接实现 UIKit / SwiftUI；使用 `ios-feature-implementation`。
- 任务是运行设备、截图、UI smoke 或 accessibility tree；使用 `ios-automation`。
- 任务是 Xcode build/test 或证据裁决；使用 `ios-verification`。
- 只有一张截图且没有可追溯设计真源，却要求把推断伪装成设计事实。

## Agent Rules

### Mode Selection

| Mode | Use When | Output |
| --- | --- | --- |
| `benchmark` | 在开发 Adapter 前证明 UI IR / Binding 的收益 | benchmark manifest 与差异报告 |
| `prepare-benchmark` | 冻结真实 Anchor Slice 并生成三组同基线输入 | benchmark case、preparation report 与 variant manifests |
| `run-benchmark` | 从冻结 commit 运行三组隔离实现与验证 | versioned input context、patch、run result、run artifact 与 aggregate score |
| `normalize` | 将 Design Evidence 转成 Canonical UI IR | `ui-ir.json` |
| `validate` | 检查 IR / Packet / benchmark 合同 | 结构化诊断 |
| `resolve-bindings` | 将设计组件匹配到现有 iOS symbol | `ios-bindings.json` |
| `index-registry` | 从 Swift 源码生成待人工确认的组件候选 | `component-registry.json` |
| `compile-packet` | 为当前任务裁剪最小充分上下文 | `agent-packet.json` |
| `initialize-manifest` | 从可实施 Packet 建立增量追踪草稿 | `implementation-manifest.json` |

### Canonical Source Rules

- `ui-ir.json` 是唯一事实源；`ui-ir.yaml` 只能由 JSON 自动生成。
- Design Evidence 必须记录 source kind、document/node、版本、截图或 evidence hash、Parser version。
- 原始设计事实、人工合同、Registry 解析和推断必须使用不同 provenance。
- `unknown` 不得被静默替换为猜测值；阻塞级 unknown 必须阻断实施 handoff。
- 禁止把完整 Figma / Sketch JSON 或全量 Component Registry 直接交给实现 Agent。

### Context Budget Rules

- 单组件建议 2K–6K tokens。
- 单区域建议 6K–12K tokens。
- 单页面建议 8K–20K tokens。
- 超限时按 component subtree、region 或 state 分片，不删除目标节点的父级约束、相对依赖、引用 token、binding 或阻塞 unknown。

### Validation Rules

- 运行 `scripts/validate_contract.py` 校验合同结构和跨引用。
- validator 默认把 blocking unknown 和超预算 Packet 返回为 `blocked` / 非零退出；`--allow-blocking-unknowns` 只用于人工检查，不得用于实施 handoff。
- benchmark 只有在候选结果来自同一页面、状态、viewport、locale 和代码基线时才可比较。
- `benchmark-case-v1` 的 ready 只证明真实源和三组输入可再生，不得被表述为 measured benchmark 或收益证据。
- `ui-ir` 对照组必须移除全部 code binding；只有 `ui-ir-with-binding` 可以读取 Registry 解析结果或 Agent Packet code anchors。
- `measured` benchmark 的三个 run 必须提供实际 artifact 路径与 SHA-256，scorer 会验证文件存在性和内容 hash。
- `run-benchmark` 必须从 benchmark case 声明的 commit 建立 evaluator 完整 checkout；若 case 声明 `provider_source_scope.mode = allowlist`，还必须按冻结 manifest 为每个 variant 构造只含允许文件的最小 Git provider worktree。两个仓库都不得包含 parent history、额外 object、refs、remote 或 alternates；runner 与 standalone scorer 必须重算精确 object set，并校验三个候选共享同一 scope identity。三组运行必须使用同一 run plan、三个互异的 hash-frozen executor / capture / validator adapters、Python runtime、模型、推理等级与公共 prompt。
- runner 固定以归档 Python adapter 作为实际脚本入口，禁止在 adapter 前插入任意 driver；provider 只在最小 worktree 中实现，完整 checkout 在 provider 活跃期间不可读。实现 patch 必须以禁用 external diff、textconv 与 rename detection 的 full object ID binary diff，相对最小 worktree baseline 冻结，再精确回放到 evaluator 完整 checkout；这样 patch identity 不依赖仓库 diff driver、两个仓库各自的 object ID 自动缩写长度或 rename heuristics，并要求回放后的 patch bytes、hash 和 changed paths 完全一致。capture 与 validation 只在完整 checkout 上执行。
- Run Plan v1.2 可声明 hash-frozen evaluator-only `capture_overlay`。runner 在 provider 运行前只把 overlay bytes/hash 冻结在 evaluator 父进程内，不得把归档 patch 落到 run directory；provider 完成且 implementation patch 冻结后才晚绑定归档并应用该 Git patch，只允许 capture adapter 在 overlay 生效期间运行。capture 成功、失败或篡改时都必须在 validator 前反向移除；反向移除冲突时只能在隔离 checkout 内 reset/clean 后重放冻结 implementation patch，并将本次 run 判为无效；还原后的 patch hash 必须与 provider 实现 patch 完全一致。
- pinned baseline 依赖缺少冻结 capture destination 所需 slice 时，typed capture runtime 可声明一个 provider-hidden、hash-frozen evaluator dependency setup。它必须独立于 capture overlay，只能在 provider patch 冻结后的 capture adapter 内临时注入，冻结 generator/compiler/SDK/baseline/product hash，所有非目标依赖入口 fail-closed，并在 `finally` 恢复原始 hash、移除生成文件；setup/restore 失败或 capture 调用 shimmed subsystem 必须阻断，不能算作 provider 实现或修复收益。
- 每个 run 必须归档 run plan、benchmark case、executor/capture/validator adapters、精确输入集合、实现 patch、三阶段 stdout/stderr、验证结果及截图/Probe/语义快照/Diff/运行观察；任何输入变更、跨目录证据、绝对 evidence path、capture/validator 改写实现或 validator 改写 capture evidence、嵌套 hash 不一致都必须阻断。
- `measured` 的 executor、capture 与 validator adapter 必须互不相同且均为 non-synthetic；scorer 必须从结构化 Probe、semantic evidence、reference/actual PNG、anchor frames、provider runs、repair events 和 manual interventions 独立反算 metrics，不得只信任 run-result 汇总值。
- input context 必须显式标注 `audience`：reference、shared prompt、UI IR、Agent Packet 为 `agent`，validation config 为 `validator`。measured 的 plan/case/executor/capture/validator 必须同属一个经审核且与代码源仓不重叠的 Git repository；output 必须位于全部 source/plan repository 之外。provider 执行期间，runner 将全部 workspace 真源、plan repository、prepared、先前 run、当前 evaluator-only artifact 设为不可读，input context 由 executor 临时设为不可读，防止通过历史、父目录、绝对路径或跨 variant 读取评估答案。
- Codex measured executor 使用 `scripts/codex_benchmark_executor.py`：固定单次 `codex exec --json --ephemeral --ignore-user-config --ignore-rules`，reference 走 `--image`，只内联该组 agent-visible 语义输入，并从唯一 `thread.started` / `turn.completed.usage` 生成 Provider Receipt；缺事件、失败事件、非 JSON、usage 缺失或多 turn 均阻断。
- Run Plan v1.2 必须冻结 provider CLI 名称、版本、绝对 launcher/native path、两者 SHA-256 与 `@openai/codex/package.json` SHA-256，并显式冻结 `capture_overlay` 为 `none` 或 `.patch` artifact；launcher 只用于 npm package provenance，executor 的 `--version` 与 measured turn 均直接调用冻结 native binary，不经 PATH、`/usr/bin/env node` 或 JS launcher 选择可执行文件，并核对 package name/version。measured executor environment 必须为空。Run Observation v1.1 记录同一 provenance、完整 canonical JSONL SHA-256 与 input/cached/output/reasoning token；runner 校验 hash，standalone scorer 还会独立重放 JSONL、重算 thread/turn/usage，三组 provider identity 与 overlay identity 必须相同。
- 信任边界：经审核的 Run Plan、本机 `@openai/codex` 安装来源及 Codex `workspace-write` sandbox 仍是信任根；`chmod(0)` 只是 evaluator 文件的附加防线，不单独构成同 UID 对抗隔离。capture overlay 的归档 bytes 会延迟到 provider 退出后才物化；runner 仍无法自动识别 pinned code tree 中与 evaluator 内容相同但路径无关的人工副本，冻结 measured plan 前必须人工确认不存在此类副本。
- provider 源码可读面必须在 Input Context 中显式冻结为 `full-tree` 或 `allowlist`，不得用缺失字段静默降级。allowlist 记录 entry、文件数、总字节数、canonical manifest SHA-256，以及最小 worktree 的 baseline commit、精确 object-set identity 与全量 Git metadata identity；范围重叠、空匹配、unsupported Git entry、manifest canonical identity 漂移、Git-ignored 越界实体、metadata/HEAD/object/config 漂移、provider/evaluator patch 不一致和跨候选 identity 漂移均阻断。runner 与 standalone scorer 都必须直接枚举文件系统和 Git baseline tree，不能只信任 `git status` 或 manifest 顶层自报字段。显式 `full-tree` 兼容模式仍会暴露完整 pinned tree，外部 measured run 前必须按完整可读面披露并获得授权，不能把 integrity anchors 冒充 allowlist。
- runner timeout 必须终止 executor/provider 整个 process group，确认子进程退出后才恢复隐藏路径权限；shield 失败必须回滚已改 mode，restore 必须 best-effort 遍历并验证。
- Validation config 必须冻结所有候选共同的 required binding ID/Registry entry/symbol 与逐 region required anchor ID/metric；semantic/visual evidence 必须精确同序覆盖，不能通过缩小分母制造增益。
- Validator 不得直接产出无法复算的通过结论：独立 capture adapter 必须先且只能生成 `actual.png` 与 `benchmark-validator-probe-v1`，固定 screenshot hash、viewport/scale/appearance/locale，并记录逐 region 的实际 frame、runtime type、accessibility identifier、visibility、parent/children，以及 required binding 的运行时 region/type identity；Probe 禁止写 structure/semantic pass/fail。validator 由冻结期望与这些原始观察派生结构/语义结果，再由 reference geometry、reference/actual PNG 和源码位置派生 anchor deviation 与 pixel difference；scorer 使用独立实现重放全部结果。
- Validation config v1.1 必须让每个 required region 都有 reference frame；position/size anchor 从 reference/actual frame 确定性计算，spacing anchor 必须冻结相对 region、两侧 edge 与 reference value。required binding 还必须冻结真实 owner source、region 与 runtime type；复用率只有在 Probe 观察到该运行时类型且 owner declaration 位置有效时才能计入，声明存在本身不等于实际复用。
- Executor 阶段只能产出固定且被冻结的 `run-observation.json`；capture 阶段只能新增 `actual.png`、`validator-probe.json` 与 capture logs；validator 阶段只能新增 semantic/diff/result 与 validation logs。每阶段都执行精确文件集合、pinned checkout、输入 hash 和所有权门禁。
- aggregate 必须强制三组共享 plan/case/executor/capture/validator hash、appearance、UI framework 和代码基线，且全部 provider run ID 跨组唯一；每组 `validation_status` 必须与 Run Artifact、Run Result 一致，最终 `ui-ir-with-binding` 只有为 `passed` 才允许 `go`，前两组 `failed` 仍可用于比较。
- `synthetic-example` 只允许在显式 opt-in 的 deterministic self-test 中执行；runner 必须重新校验 scorer 状态，不能仅靠重命名或改字段晋升为 `measured`。
- 合成样例只验证工具，不得作为真实收益证据。
- 实施完成后要求 Implementation Manifest 关联 Design Node、code symbol、source file、PreviewScene 和 validation region。
- 源码索引只生成 <code>pending-review</code> / heuristic 候选；未经过人工设计映射确认，不得提升为 active binding。
- Task Context Compiler 必须保留目标子树、全部祖先、递归 <code>relative_to</code> 依赖、被引用 token、节点 style/state/component 语义、环境/viewport、连通 state/interaction、responsive、accessibility、active binding 和所有 blocking unknown。
- Agent Packet 必须记录 <code>requested_states</code>；validator 从 seeds 重算连通状态/交互闭包、目标 acceptance regions 和确定性 context token estimate，不信任 Packet 自报值。
- <code>active</code> Registry entry 必须来自 <code>manual-contract/exact</code>；<code>source-index/heuristic</code> 只能保持 <code>pending-review</code>，compiler 不得静默选取 framework 不匹配或多候选 binding。
- Implementation Manifest 初始化结果固定为 blocked draft；只有 PreviewScene、validation region、passed evidence 均补齐后才能标记 complete。
- Complete Manifest 必须校验实际 UI IR、Agent Packet、validation evidence 文件及 SHA-256，并核对 screen、环境、viewport、Design Node、binding、mapping coverage 与逐 region 语义视觉证据。

### Token Budget

- 只读取目标 screen / region / component 的 evidence slice。
- Registry 只返回候选 symbol、源码路径、availability 和最小必要签名。
- 不把全量设计 JSON、全量源码、完整截图 Diff 日志写入 Agent Packet。
- 长诊断写文件，回复只返回首个失败和摘要。

## Inputs

```json
{
  "mode": "benchmark | prepare-benchmark | run-benchmark | normalize | validate | index-registry | resolve-bindings | compile-packet | initialize-manifest",
  "design_source": "Figma | Sketch | manual-evidence",
  "target": {
    "screen": "required",
    "region": "optional",
    "component": "optional",
    "state": "optional"
  },
  "evidence_path": "optional",
  "ui_ir_path": "optional",
  "registry_path": "optional",
  "context_budget": "optional integer",
  "output_dir": "required for generated artifacts"
}
```

## Outputs

```json
{
  "status": "completed | partial | blocked",
  "mode": "benchmark | prepare-benchmark | run-benchmark | normalize | validate | resolve-bindings | compile-packet | initialize-manifest",
  "design_source": {},
  "canonical_ui_ir": "path-or-null",
  "ios_bindings": "path-or-null",
  "agent_packet": "path-or-null",
  "component_registry": "path-or-null",
  "implementation_manifest": "path-or-null",
  "benchmark_report": "path-or-null",
  "diagnostics": [],
  "blocking_unknowns": [],
  "handoff_ready": false,
  "context_budget": {},
  "suggested_next_skill": "ios-feature-implementation | ui-ux-design-system | ios-automation | blocked",
  "next_action": "implement | collect-evidence | fix-contract | benchmark | blocked"
}
```

## Exit Conditions

Return `completed` when:

- source/version/node provenance is traceable;
- the selected contract passes validation;
- blocking unknowns are empty;
- an Agent Packet stays within budget and preserves required dependency closure; and
- the next implementation or evidence action is explicit.

Return `partial` when a useful IR/Packet exists but non-blocking design facts or bindings remain unresolved.

Return `blocked` when the design source is unreadable, the target node is ambiguous, required bindings are stale, the contract is invalid, or blocking unknowns remain.

## Escalation Rules

- Escalate design-source ambiguity or missing visual decisions to `ui-ux-design-system` / design researcher.
- Escalate a validated Agent Packet to `ios-feature-implementation(swiftui|uikit|mixed-ui)`.
- Escalate screenshot capture, accessibility tree and UI smoke to `ios-automation`.
- Escalate build/test evidence to `ios-verification` and static final review to independent `code-review`.
- Formal HTML output routes to `html-docs`.

## Reporting Format

```text
Design context status: completed | partial | blocked
Mode: ...
Canonical UI IR: ...
iOS bindings: ...
Agent Packet: ...
Context budget: ...
Blocking unknowns: ...
Diagnostics: ...
Next action: ...
```

## Reference Resources

- `references/design-evidence-v1.schema.json`: 可审计 Design Evidence Snapshot Schema。
- `references/ui-ir-v1.1.schema.json`: Canonical UI IR v1.1 Schema。
- `references/agent-packet-v1.schema.json`: Task-scoped Agent Packet Schema。
- `references/component-registry-v1.schema.json`: Design component 到 UIKit / SwiftUI symbol 的绑定合同。
- `references/implementation-manifest-v1.schema.json`: Design Node 到代码、PreviewScene 与验证区域的完成合同。
- `references/implementation-validation-v1.schema.json`: 逐 region 结构、语义、视觉验证结果及环境合同。
- `references/benchmark-v1.schema.json`: 三组输入对照 benchmark 合同。
- `references/benchmark-case-v1.schema.json`: 真实 benchmark 的 pre-run source/hash/input readiness 合同。
- `references/benchmark-validation-config-v1.schema.json`: 同基线 viewport、region、指标与阈值合同。
- `references/benchmark-validator-probe-v1.schema.json`: 独立 capture adapter 生成的截图、环境与逐 region runtime type/accessibility/visibility/层级原始观察合同；不含验收结论。
- `references/benchmark-capture-adapter-protocol-v1.md`: 项目专用 iOS capture adapter 的冻结环境、精确输出、运行时观测与所有权边界。
- `references/benchmark-run-artifact-v1.schema.json`: 单次 benchmark run 的环境、指标与输入/输出/验证证据链。
- `references/benchmark-run-plan-v1.schema.json`: 同模型、同推理等级、hash-frozen adapter、evaluator overlay、typed iOS capture runtime 与隔离顺序合同。
- `references/benchmark-input-context-v1.schema.json`: 单次运行实际读取的 plan、case、adapter、variant 输入及 agent/validator audience 快照。
- `references/provider-source-manifest-v1.schema.json`: provider 可读源码 allowlist、逐 blob/mode/size 与 canonical identity 合同。
- `references/benchmark-run-result-v1.schema.json`: provider run、token、逐 region 验收、截图/语义/Diff 证据合同。
- `references/benchmark-semantic-evidence-v1.schema.json`: required binding、源码位置、未映射视觉字面量与逐 region 结构/语义证据。
- `references/benchmark-visual-diff-v1.schema.json`: reference/actual hash、逐 region anchor 偏差与视觉测量证据。
- `references/benchmark-run-observation-v1.schema.json`: provider CLI identity、JSONL receipt、usage、repair events 与人工介入时长证据。
- `references/benchmark-cases/au-create-project-alert/`: SidusLinkPro New Project Alert 的真实 ready case；尚未 measured。
- `references/*-example.json`: 合成样例，只用于脚本自测。
- `references/benchmark-metrics.md`: benchmark 指标定义与同基线要求。
- `scripts/validate_contract.py`: 无第三方依赖的结构与跨引用校验。
- `scripts/index_swift_components.py`: 索引 UIKit / SwiftUI 类型并生成待审 Registry candidates。
- `scripts/compile_agent_packet.py`: 计算任务引用闭包并输出受 context budget 约束的 Agent Packet。
- `scripts/create_ios_capture_runtime.py`: 冻结 iOS Simulator、`codex_verify` 与 `simctl` identity 的机器专用 capture runtime。
- `scripts/unityframework_simulator_stub.py`: 为缺少 arm64 Simulator slice 的 pinned UnityFramework 生成 capture-only、fail-closed evaluator ABI stub，并严格恢复 Pod 基线。
- `scripts/initialize_implementation_manifest.py`: 从 handoff-ready Packet 生成默认 blocked 的 Manifest 草稿。
- `scripts/score_benchmark.py`: 汇总 benchmark 指标并给出 go / revise 建议。
- `scripts/prepare_benchmark_case.py`: 从冻结的 Sketch/代码源校验哈希、重导参考图、重编 Packet 并生成隔离的三组输入。
- `scripts/run_benchmark.py`: 从 pinned commit 建立三组 clean checkout，执行 hash-frozen adapter，捕获实现 patch、验证证据并调用 scorer。
- `scripts/create_benchmark_run_plan.py`: 校验真实 case，并冻结当前 Codex launcher/native/package、executor、项目专用 capture adapter 与独立 validator 的 measured Run Plan。
- `scripts/codex_benchmark_executor.py`: 真实 Codex CLI 单 turn executor；隔离 validator-only 输入并从 provider JSONL 生成不可估算的 Run Observation。
- `scripts/ios_semantic_visual_validator.py`: 从只读 Probe、冻结 PNG、reference geometry 与源码位置独立派生 binding reuse、magic numbers、anchor deviation、pixel ratio 与 Run Result。
- `scripts/fake_benchmark_capture.py`: 仅供 deterministic synthetic self-test 使用；拒绝 measured evidence。
- `scripts/fake_benchmark_executor.py`: 仅供 deterministic synthetic self-test 使用；拒绝 measured evidence。
- `scripts/self_test.py`: 运行合法、非法合同和 benchmark scorer 自测。

## Relationship to Other Skills

- `ui-ux-design-system` 提供设计事实、设计决策和 Design-to-Code source packet。
- 本 Skill 将 source packet 编译为 Canonical UI IR、iOS bindings 和 Agent Packet。
- `ios-feature-implementation` 是唯一 UIKit / SwiftUI / mixed-ui 产品代码实施入口。
- `ios-automation` 采集截图、accessibility tree 与 UI smoke 证据。
- `ios-verification` 与独立 `code-review` 负责实现链路收口。
