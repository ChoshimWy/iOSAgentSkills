# subAgent 模型选择与回退（主 Agent 执行）

目标：Codex CLI 原生 subAgent 可用时，默认优先让 subAgent 继承主 Agent 模型配置；截至 2026-06-12，本仓库共享默认模型为 `gpt-5.5`。只有用户明确要求、任务风险需要或预算/吞吐目标明确时，主 Agent 才按角色显式指定 `model` / `reasoning_effort`。若指定模型不可用，则自动回退，保证编排不中断。

> 约束：本仓库不写死“永远正确”的模型名；实际可用模型取决于运行时/账号，可能随时间变化。无明确理由时不传 `model`，让 subAgent 继承主 Agent 默认模型。

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
1. `gpt-5.4-mini`
2. `gpt-5.4`
3. `gpt-5.3-codex-spark`

> 说明：`gpt-5.4-mini` 通常更快更省；若运行时不可用或效果不佳，再回退到强模型梯队。

## 推理强度（reasoning_effort）默认值

- coder：默认不指定（继承主 Agent 的默认设置）；如需强推理可显式 `high`
- reviewer：`low`
- tester：`medium`

## 主 Agent 执行算法（必须遵守）

### 0) 默认继承主模型

- 未命中“用户明确要求 / 高风险任务 / 明确预算或吞吐目标”时，`spawn_agent` 不传 `model`，也不为低风险任务强行指定不同推理强度。
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

主 Agent 在编排开始时，用一行说明本次选择结果（只写最终落地策略，不要把所有候选刷屏）：

- `subagent model policy: inherit parent`（默认）
- 或 `coder model: ...` / `reviewer model: ...` / `tester model: ... (reasoning_effort=medium)`（确有覆盖时）

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
