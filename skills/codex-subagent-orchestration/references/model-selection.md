# subAgent 模型选择与回退（主 Agent 执行）

目标：当用户要求“coder=强模型 / reviewer=快模型 / tester=强模型（中推理）”时，让主 Agent **每次都自动按角色挑模型**；若指定模型不可用，则 **自动回退**，保证编排不中断。

> 约束：本仓库不写死“永远正确”的模型名；但允许提供“候选列表 + 失败回退”的策略。实际可用模型取决于运行时/账号，可能随时间变化。

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

### 1) 为每个角色生成候选模型序列

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

主 Agent 在编排开始时，用一行说明本次选择结果（只写最终落地的模型名，不要把所有候选刷屏）：

- `coder model: ...`
- `reviewer model: ...`
- `tester model: ... (reasoning_effort=medium)`

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

