# subAgent 模型选择与回退（主 Agent 执行）

目标：coder / tester 可由主 Agent 在运行时工具可用、写集安全且拆分有质量/效率收益时自主调用 Codex 原生 subAgent；实现链路的 reviewer subAgent 是强制独立审查角色。截至 2026-06-15，本仓库共享默认模型为 `gpt-5.5`，默认 reasoning effort 为 `medium`；reviewer subAgent 默认显式使用 `gpt-5.3-codex-spark`。只有用户明确要求模型分工、任务风险需要或预算/吞吐目标明确时，主 Agent 才为 coder / tester 按角色显式指定 `model` / `reasoning_effort`。若指定模型不可用，则回退为继承主 Agent，保证编排不中断。

> 约束：除本仓库明确钉住的 reviewer 默认模型 `gpt-5.3-codex-spark` 外，不写死“永远正确”的模型名；实际可用模型取决于运行时/账号，可能随时间变化。若 reviewer 指定模型不可用，回退为不传 `model`，让 subAgent 继承主 Agent 默认模型。

## 角色 -> 意图

- **coder (worker)**：实现质量优先（强模型）
- **reviewer (explorer)**：吞吐优先（快模型）
- **tester (explorer)**：定位/归因质量优先（强模型 + 中等推理）

## 推荐候选列表（按优先级）

### 强模型（strong）
1. `gpt-5.5`
2. `gpt-5.4`
3. `gpt-5.2`

### 快模型（fast）
1. `gpt-5.3-codex-spark`
2. `gpt-5.4-mini`
3. `gpt-5.4`

> 说明：reviewer 默认优先使用 `gpt-5.3-codex-spark`；若运行时不可用或效果不佳，再按 fast 序列回退，候选全部失败时继承主 Agent 默认模型。

## 推理强度（reasoning_effort）默认值

- coder：默认不指定（继承主 Agent 的默认设置）；如需强推理可显式 `high`
- reviewer：`low`
- tester：`medium`

## 主 Agent 执行算法（必须遵守）

### 0) 默认模型策略

- 未命中“运行时工具可用 / 工具策略允许 / 写集安全 / 拆分有质量或效率收益”时，不为 coder / tester 调用 `spawn_agent`；实现链路 reviewer subAgent 仍必须调用，且默认传 `model="gpt-5.3-codex-spark"`；coder / tester 已启动但未命中模型覆盖条件时，`spawn_agent` 不传 `model`，也不为低风险任务强行指定不同推理强度。
- 角色模板中的 `model_reasoning_effort` 只表达角色偏好；具体是否覆盖由主 Agent 根据当前任务决定。

### 1) 需要显式指定时，为每个角色生成候选模型序列

- coder：`strong` 序列
- reviewer：`fast` 序列
- tester：`strong` 序列（但 `reasoning_effort=medium`）

### 2) spawn_agent：逐个尝试，失败即回退

对每个 subAgent：

1. 用候选模型 #1 调 `spawn_agent(model=...)`
2. 若 tool 返回“模型不可用 / 不支持 / 权限不足 / unknown model”之类错误：
   - 立即尝试候选模型 #2、#3……
3. 若候选全部失败：**回退为不传 `model`**（让 subAgent 继承主 Agent 默认模型），并继续编排。

### 3) 输出要求（可观测性）

主 Agent 在启动任一原生 subAgent 后，用一行说明本次选择结果（只写最终落地策略，不要把所有候选刷屏）：

- `reviewer model: gpt-5.3-codex-spark`（默认 reviewer 策略）
- `subagent model policy: inherit parent`（coder / tester 默认）
- 或 `coder model: ...` / `tester model: ... (reasoning_effort=medium)`（确有覆盖时）

若发生回退（候选失败）：再追加一行：

- `model fallback: <role> from <preferred> -> <fallback> (reason: <short error>)`

## 示例（参数形态）

> 注意：示例仅展示“如何带 model/reasoning_effort”，不保证模型在你当前运行时一定可用；必须按上面的回退算法执行。

```json
{
  "agent_type": "worker",
  "fork_context": true,
  "model": "gpt-5.5",
  "reasoning_effort": "high",
  "message": "你是 coder worker：只改 ownership 内文件；不要无关重构。"
}
```
