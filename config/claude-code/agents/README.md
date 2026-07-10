# Claude Code Agent Prompt Templates

本目录存放 Claude Code 子 Agent 的 prompt 模板，对应 Codex `config/codex/templates/agents/` 的 TOML agent 定义。

## 角色映射

| 文件 | 角色 | Claude Code subagent_type |
|---|---|---|
| `explorer.md` | 上下文收集 / 文件定位 | `Explore` |
| `builder.md` | 最小可验证实现 | `general-purpose` |
| `tester.md` | 验证建议 / 失败归因 / 补测试 | `general-purpose` |
| `reviewer.md` | 静态审查 | `Explore` |
| `pm.md` | 需求拆解 / 范围控制 | `Plan` |
| `reporter.md` | 交付汇总 | `general-purpose` |
| `docs_researcher.md` | Apple / OpenAI 官方事实核实 | `Explore` |
| `orchestration.md` | 主 Agent 编排指令 | (主 Agent 直接使用) |

## 使用方式

通过 `Agent` 工具调用，在 `prompt` 参数中引用对应模板内容：

```
Agent(
  subagent_type="Explore",
  description="Code review",
  prompt="<reviewer.md 的内容> + 具体任务上下文"
)
```

主 Agent 负责聚合结果、回写修正、执行门禁裁决。

## 合同字段

所有角色输出必须包含：
- `checkpoint_status`: CP0|CP1|CP2|CP3 pass|fail|blocked
- `first_failure`: none | 具体描述
- `next_action`: proceed | fix-and-rerun | blocked | complete

## 与 Codex 的区别

- Codex 用 TOML 预定义 agent（含 model / sandbox / reasoning 配置）
- Claude Code 用 Markdown prompt 模板，model 由 runtime 决定
- Codex 的 `send_message` / `followup_task` / `interrupt_agent` 回写机制 → Claude Code 的 post-completion 再 spawn 修正循环
- 不复制 Codex 的 Profile、Fast mode 或模型名；Claude Code 的模型选择继续由其 runtime / 用户设置决定
- `docs_researcher` 只在需要官方事实时按需使用 Claude 全局 MCP 或 `WebSearch` / `WebFetch`，不新增未经验证的全局 MCP
