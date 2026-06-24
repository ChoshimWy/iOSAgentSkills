# iOS 开发 Agent 与 Skill 生态对比（代表性调研）

- 创建日期：2026-06-24
- 调研范围：面向 iOS / Apple 平台开发的通用 coding agent、Agent Skill 机制、Xcode / Simulator / PR 自动化相关工具链。
- 输出目标：为 `iOSAgentSkills` 后续 Skill 设计、路由边界、工具接入与可发布形态提供外部对比基线。
- 结论级别：代表性调研，不是全量市场名录；优先采用官方文档、官方仓库与一手产品说明。

## 1. 结论摘要

| # | 结论 | 对 iOS 开发的含义 | 对本仓的启发 |
| --- | --- | --- | --- |
| 1 | 主流 Agent 正从“代码补全 / Chat”转向“可读写仓库、可运行命令、可开 PR 的执行体” | 仅会写 Swift 不够，关键是能否安全地跑 `xcodebuild`、XCTest、Simulator、签名/构建诊断 | 本仓保持 `codex-subagent-orchestration -> implementation -> verification -> review` 链路是必要的 |
| 2 | Skill 形态高度收敛到 `SKILL.md + 可选 scripts/references/assets` | 复杂 iOS 流程应沉淀为可复用 Skill，而不是每轮 prompt 重写 | 本仓目录结构与 Codex / Claude / Copilot 的主流 Skill 模式基本一致 |
| 3 | 公开生态里真正“iOS / Xcode 原生”的 Agent 很少 | 通用 Agent 需要 XcodeBuildMCP、Apple Docs、验证 wrapper、设备自动化脚本补齐平台能力 | 本仓的 `ios-verification`、`ios-automation`、`xcode-build` 是差异化资产 |
| 4 | Cloud agent 擅长 issue/PR、后台分支、CI；本地 agent 擅长真机/模拟器、私有依赖、Keychain/签名环境 | iOS 项目不能只依赖云端，因为很多问题必须在 macOS + Xcode + 本地证书链上复现 | 推荐保留“本地验证权威 + 云端 PR 辅助”的混合策略 |
| 5 | Subagent / 多 Agent 的价值集中在隔离上下文、并行研究、独立审查 | iOS 任务里 reviewer / tester / explorer 分离能降低误判与上下文污染 | 本仓“独立 reviewer subAgent 强制收口”方向与外部趋势一致 |

一句话判断：**iOS Agent 的竞争点不在“哪个模型会写 Swift”，而在是否把 Apple 平台约束、Xcode 验证证据、设备自动化、签名/私有库 ownership 与独立审查固化成可执行 Skill / Tool / Workflow。**

## 2. 概念边界

| 概念 | 本文定义 | iOS 场景例子 |
| --- | --- | --- |
| Agent | 可围绕目标自主读取上下文、编辑文件、运行命令、调用工具、产出变更的 AI 执行体 | Codex CLI、Claude Code、Copilot cloud agent、Cursor Agent、Windsurf Cascade |
| Skill | 可复用的任务说明、流程、约束与资源包；通常按需加载，降低重复 prompt 与上下文成本 | `ios-verification`、`code-review`、`swiftui-patterns`、`xcode-signing` |
| Tool / MCP | Agent 可调用的外部能力，提供真实操作或数据访问 | XcodeBuildMCP、GitHub MCP、Apple Docs、browser/computer-use、xcodebuild wrapper |
| Workflow | 多步骤执行合同，通常包含 checkpoint、验证、失败回环和交付格式 | CP0/CP1/CP2/CP3、fail-fix-report、PR review loop |

## 3. 代表性生态对比

| 生态 / 工具 | Agent 形态 | Skill / 扩展机制 | iOS / Xcode 适配度 | 强项 | 主要限制 | 代表性来源 |
| --- | --- | --- | --- | --- | --- | --- |
| OpenAI Codex | 本地 CLI、IDE/App/Web，能读写目录并运行代码 | Agent Skills；`SKILL.md` + scripts/references/assets；progressive disclosure；plugin 分发 | 中高：本地 Mac 可接 Xcode 工具；深度取决于 skills/MCP/wrapper | 本地执行、Skill/Plugin、subagent、code review、MCP 生态 | 原生 iOS 细分能力需要额外封装 | [Codex CLI](https://developers.openai.com/codex/cli)、[Agent Skills](https://developers.openai.com/codex/skills) |
| Claude Code | 终端/IDE/云侧 agent，可配 subagents | `.claude/skills/<name>/SKILL.md`；内置 `/code-review`、`/debug`、`/run`、`/verify` 等；支持 subagent 执行 | 中高：适合本地 Mac + 自定义 Xcode Skill；无内建完整 iOS 工程策略 | Subagent 上下文隔离、动态上下文注入、内置 review/debug/run/verify | iOS 签名、workspace、真机策略仍需项目级 Skill/脚本 | [Claude Skills](https://code.claude.com/docs/en/skills)、[Subagents](https://code.claude.com/docs/en/sub-agents) |
| GitHub Copilot cloud agent | GitHub Actions 驱动的后台 cloud agent，可从 issue/PR/Chat 触发 | `.github/skills` / `.claude/skills` / `.agents/skills` / personal skills；`SKILL.md` | 中：适合 PR、CI、文档、测试覆盖；受 macOS runner、证书、私有依赖限制 | GitHub 原生 PR/branch/automation、企业治理、metrics | 对本地 Simulator/真机/Keychain 的真实性弱于本地 Mac | [Cloud agent](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent)、[Agent skills](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills) |
| Cursor Agent | IDE / CLI / Cloud agent，强调代码库理解和并行 agent | Rules、Agent、Cloud、CLI；公开文档偏产品化 | 中：适合作为 VS Code-like IDE 辅助；Xcode 工程验证需外接工具 | 代码库索引、云端 agents、并行构建/测试/demo | 不是 Xcode 原生 IDE；iOS 设备/签名链仍靠外部 | [Cursor features](https://cursor.com/features) |
| Windsurf Cascade | IDE 内 agentic assistant，支持 Code/Chat、工具调用、checkpoints | `AGENTS.md`、Rules/Memories、MCP、Hooks、Workflows、Skills | 中：支持通用 IDE/插件生态，可接 MCP；iOS 深度仍依赖外部 Xcode 工具 | Agent Command Center、AGENTS.md、Arena 并行、MCP/Hook/Workflow | 公开说明以通用软件工程为主，iOS 策略需自建 | [Windsurf docs index](https://docs.windsurf.com/llms.txt) |
| XcodeBuildMCP | 不是完整 coding agent，而是 iOS/macOS 专用 MCP server + CLI | 自带 MCP Skill / CLI Skill，可给 Codex、Claude、Cursor 等 agent 使用 | 高：专门面向 iOS/macOS 项目的 build/test/simulator/device 工具 | Xcode / Simulator / CLI / MCP 一体，补齐 Agent 的 Apple 工具层 | 不是产品级 orchestrator；仍需上层 workflow 和审查策略 | [XcodeBuildMCP](https://github.com/getsentry/XcodeBuildMCP) |
| Replit Agent | 浏览器/云端应用生成 Agent | Agent modes、Plan mode、Agent Skills、MCP、mobile artifact | 低到中：更偏应用生成/发布；Native iOS/Xcode 项目不是核心 | 从自然语言生成 web/mobile artifacts、低门槛发布 | 对现有大型 Xcode workspace、私有 Pod、签名/真机验证不适合作为主链路 | [Replit Agent](https://docs.replit.com/references/agent/overview) |
| Devin / Cognition | 云端自治软件工程 Agent，会话/API/Playbook/PR 指标 | Knowledge、Playbooks、Sessions、API | 中：适合后台任务和 PR，iOS 本地验证仍需 macOS/Xcode 环境 | 异步任务、会话管理、团队/企业 API | 对本地设备链路与私有签名环境仍需额外集成 | [Devin docs index](https://docs.devin.ai/llms.txt) |

## 4. iOS 能力矩阵

| 能力维度 | Codex | Claude Code | Copilot cloud | Cursor | Windsurf | XcodeBuildMCP | Replit / Devin |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Swift / SwiftUI / UIKit 代码生成 | 高 | 高 | 中高 | 高 | 高 | 低（工具层） | 中 |
| 本地 Xcode build/test | 高，需本地 Mac + wrapper/MCP | 高，需本地 Mac + Skill/MCP | 中，依赖 GitHub Actions macOS runner | 中，需外接 shell/MCP | 中，需外接 shell/MCP | 高 | 低到中 |
| Simulator / 真机操作 | 中高，需 MCP/automation | 中高，需 MCP/automation | 低到中 | 中，需外接工具 | 中，需外接工具 | 高 | 低 |
| 签名 / Entitlements / Archive | 中，需项目 Skill | 中，需项目 Skill | 中，适合 CI 但证书治理复杂 | 中 | 中 | 中高（工具执行，不替代策略） | 低到中 |
| 私有 Pod / 本地 `:path` ownership | 高，若本地规则清晰 | 高，若本地规则清晰 | 中，云端权限和路径限制明显 | 中 | 中 | 中（执行层） | 低到中 |
| 独立 review / 多 Agent | 高 | 高 | 中高 | 中高 | 中高 | 低（非 orchestrator） | 中 |
| Skill 可移植性 | 高，采用 Agent Skills | 高，采用 Agent Skills | 高，兼容多个 skills 目录 | 中 | 中 | 中，提供专用 skills | 中 |
| 团队治理 / 审计 | 中高 | 中高 | 高 | 高（企业版） | 高（企业版） | 中 | 高（企业版） |

## 5. Skill 设计趋势

| 趋势 | 外部证据 | iOS Skill 设计建议 |
| --- | --- | --- |
| `SKILL.md` 成为事实格式 | Codex、Claude、Copilot 都围绕 `SKILL.md`、description、可选脚本/资源组织技能 | 本仓继续保持每个 Skill 独立目录，脚本放 `scripts/`，资料放 `references/` |
| Progressive disclosure / 按需加载 | Codex 和 Claude 都强调 Skill 只在相关时加载，降低上下文成本 | `ios-feature-implementation` 应保留单入口 + 内部分型，避免暴露过多并列 Skill 挤占 context |
| Skill 与 subagent 分工 | Claude 把 subagent 定义为隔离上下文的专用助手，Skill 更像可复用流程 | 复杂 iOS 任务：Skill 定义流程，subAgent 承担 explorer/reviewer/tester 等角色 |
| Script-first / artifact-first | GitHub skills 示例和本仓策略都强调脚本先摘要大日志再交给 Agent | Xcode 日志、xctrace、diagnostics 必须先结构化，Agent 只读摘要 |
| AGENTS.md / Rules / Memory 普及 | Windsurf、Codex、本仓都使用 AGENTS.md / rules 作为目录级规则 | Apple 平台约束、私有库 ownership、验证基线应留在 AGENTS.md / TAXONOMY 层 |

## 6. 对 `iOSAgentSkills` 的差距与机会

| # | 观察 | 本仓当前状态 | 建议 |
| --- | --- | --- | --- |
| 1 | 外部通用 Agent 多，iOS 原生 Skill 少 | 本仓已有 `ios-feature-implementation`、`ios-verification`、`ios-automation`、`xcode-build` | 继续强化“iOS 平台事实 + 验证证据”差异化，不盲目扩散通用 coding Skill |
| 2 | 公共 Skill 格式趋同 | 本仓已是 `skills/<skill>/SKILL.md` | 若未来对外发布，可补 `license`、更短 `description`、示例输出和兼容 `.agents/skills` 安装说明 |
| 3 | XcodeBuildMCP 是最接近 iOS 原生工具层的公开项目 | 本仓已有自研 `codex_verify` wrapper 与验证策略 | 可在 docs 中明确：XcodeBuildMCP 适合作为工具补强，但项目权威验证仍走本仓 wrapper / queue / structured artifacts |
| 4 | Copilot / GitHub cloud agent 强在 PR 自动化 | 本仓主要偏本地执行与 Skill 规则 | 可补一份 “GitHub cloud agent 使用边界”：只做 PR/文档/CI-friendly 任务，不作为真机/签名/私有 Pod 权威验证 |
| 5 | Claude / Cursor / Windsurf 都在强化多 Agent / agent center | 本仓已强制独立 reviewer subAgent | 可把 `reviewer subAgent` 的输入/输出契约进一步机器可读化，便于跨 Agent 产品复用 |

## 7. 推荐的 iOS Agent 架构

```text
User Request
  ↓
Entry Orchestrator Skill
  - task classification: doc-only / code-small / code-medium / code-risky
  - checkpoint: CP0 / CP1 / CP2 / CP3
  ↓
Implementation Skill
  - business / SwiftUI / UIKit / Liquid Glass / SDK contract / test implementation
  ↓
Tool Layer
  - Apple docs / XcodeBuildMCP / codex_verify wrapper / GitHub MCP / device automation
  ↓
Verification Skill
  - affected tests
  - xcodebuild through non-sandbox wrapper
  - structured artifacts: verification-report.json / diagnostics.json / build-summary.txt
  ↓
Independent Reviewer SubAgent
  - code-review blocking findings first
  ↓
Reporter
  - changed files / validation / residual risk / next action
```

## 8. 适合沉淀的 iOS Skill 清单

| 分类 | 推荐 Skill | 说明 |
| --- | --- | --- |
| 入口编排 | `codex-subagent-orchestration` | 对齐多 Agent / checkpoint / fail-fix-report |
| 实施 | `ios-feature-implementation` | 单入口，内部细分 SwiftUI/UIKit/business/SDK/test |
| 验证 | `ios-verification` | 受影响测试选择、wrapper 执行、摘要判读、final gate |
| 设备 | `ios-automation` | Simulator / 真机 / UI smoke / screenshots / accessibility tree |
| 构建 | `xcode-build` | Build Settings、签名、Archive、Export、CI/CD |
| 诊断 | `debugging`、`ios-performance` | crash/LLDB/泄漏/trace/benchmark |
| 审查 | `code-review` | 必须由独立 reviewer subAgent 执行 |
| 外部事实 | `apple-docs` | Apple API / availability / WWDC / sample code |
| 发布 | `app-store-changelog` | 从 git diff/tag 生成用户可见更新文案 |

## 9. 采用建议

1. **不要把 iOS Skill 设计成“越多越好”。** 外部趋势是 Skill 以 description 进入初始上下文，数量过多会稀释选择质量；本仓“一个实施入口 + 一个验证入口 + 少量专项”更适合大型 iOS 项目。
2. **把 Xcode 真实性留给本地项目环境。** Cloud agent 可做 issue/PR/CI-friendly 工作，但 iOS 的真机、签名、私有 Pod、本地 `:path`、Keychain 与 Simulator 状态，仍应以本地 Mac 的 wrapper artifact 为准。
3. **将 XcodeBuildMCP 视为工具层，不替代 workflow。** 它能补齐 Agent 调 Xcode 的工具能力，但是否需要测试、跑哪些测试、如何判定 env_issue，仍应由 `ios-verification` 负责。
4. **优先把重复高成本判断脚本化。** 例如 destination 选择、xcodebuild log digest、trace 摘要、签名错误归类，应由脚本产出低 token artifact。
5. **对外兼容 Skill 标准，对内保留本仓约束。** 如果未来面向 Claude/Copilot/Codex 复用，建议保持 `SKILL.md` 标准结构，同时保留本仓 AGENTS/TAXONOMY 作为权威路由源。

## 10. 参考来源

- OpenAI Codex CLI：https://developers.openai.com/codex/cli
- OpenAI Agent Skills：https://developers.openai.com/codex/skills
- Claude Code Skills：https://code.claude.com/docs/en/skills
- Claude Code Subagents：https://code.claude.com/docs/en/sub-agents
- GitHub Copilot cloud agent：https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent
- GitHub Copilot agent skills：https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills
- Cursor product/features：https://cursor.com/features
- Windsurf docs index：https://docs.windsurf.com/llms.txt
- XcodeBuildMCP GitHub：https://github.com/getsentry/XcodeBuildMCP
- Replit Agent：https://docs.replit.com/references/agent/overview
- Devin docs index：https://docs.devin.ai/llms.txt
