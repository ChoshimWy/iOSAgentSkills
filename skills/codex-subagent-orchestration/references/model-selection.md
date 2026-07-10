# subAgent 模型选择与运行时回退

目标：让任务类型、角色风险和模型成本形成可执行映射，同时避免把易变化的型号写进 `AGENTS.md` 或依赖当前 `spawn_agent` 不支持的参数。

## 真源分层

- 跨设备工作流与安全边界：`AGENTS.md`、本 Skill。
- 角色模型、推理强度、sandbox、专属 MCP：`config/codex/templates/agents/*.toml`。
- CLI 场景组合：`config/codex/templates/profiles/*.config.toml`，安装到 `~/.codex/<name>.config.toml`。
- 本机当前可用模型：`codex debug models`。
- 语义校验：`python3 scripts/check_codex_model_policy.py`。

共享 `config/codex/codex.shared.toml` 不设置 `model`、`model_reasoning_effort`、`plan_mode_reasoning_effort`、`model_verbosity` 或 `service_tier`。安装脚本必须保留本机已有值，不能把新模型回写成仓库旧 baseline，也不能全局强制 Fast mode。

## 角色策略

| 角色 | 默认模型 | reasoning | 目的 |
| --- | --- | --- | --- |
| builder | `gpt-5.6-sol` | `high` | 复杂实现、工具调用与边界推理质量优先 |
| reviewer | `gpt-5.4` | `high` | 稳定、只读的最终质量门禁 |
| explorer / pm / tester | `gpt-5.6-terra` | `low` / `medium` | 平衡速度、成本与代码理解 |
| reporter | `gpt-5.6-luna` | `low` | 低成本汇总已有证据 |
| docs_researcher | `gpt-5.4-mini` | `medium` | 只读官方资料检索，MCP 仅对该角色启用 |

`gpt-5.3-codex-spark` 只适合近实时、低延迟、文本型局部迭代或快速探索；不得以 `Spark + low` 作为所有实现任务的强制 reviewer 门禁。

## Profile 策略

- `daily`：Terra + medium，普通实现。
- `budget`：Luna + low，机械修改与批处理。
- `readonly`：Terra + low + read-only，探索与资料整理。
- `deep`：Sol + high，跨文件复杂实现。
- `extreme`：Sol + xhigh，高风险迁移与最难推理。
- `interactive-fast`：GPT-5.5 + medium + Fast，仅用于人在屏幕前等待的交互任务。

除 `interactive-fast` 外，Profile 和共享 baseline 都不得默认设置 `service_tier = "fast"`。

## 当前工具合同

当前协作 surface 的 `spawn_agent` 只使用运行时公开字段，例如 `task_name`、`message`、`fork_turns`。不要在调用里虚构 `agent_type`、`model`、`reasoning_effort` 或 `fork_context`。

后续控制按当前 runtime 使用：

- `send_message`：向正在运行的 Agent 传递信息，不触发新 turn。
- `followup_task`：向空闲 Agent 追加任务并触发新 turn。
- `wait_agent`：仅在下一步依赖结果时等待。
- `interrupt_agent`：仅在必须停止正在执行的 turn 时使用。

模型与 reasoning 应由 custom-agent TOML 决定。如果当前 runtime 不暴露 custom agent 选择或目标模型不可用：

1. 不向 `spawn_agent` 注入未支持字段。
2. 回退到 runtime 默认 subAgent / 继承父 Agent。
3. 输出 `model fallback: <role> -> inherit parent (reason: <capability or availability>)`。
4. reviewer 仍必须保持独立；无法启动独立 reviewer 时报告 blocked / pending review，不能降级自审。

## 校验

```bash
# 仓库确定性检查，不访问 runtime catalog
python3 scripts/check_codex_model_policy.py --offline

# 对照当前账号/runtime 的实际模型目录
python3 scripts/check_codex_model_policy.py

# 可选诊断本机旧 profile 与不可解析 MCP 命令
python3 scripts/check_codex_model_policy.py --local-config ~/.codex/config.toml
```
