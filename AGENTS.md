# AGENTS.md

## 目标

- 以尽量低的 token 成本完成高质量 iOS / Apple 平台工程任务。
- 默认优先级：正确性 > 验证效率 > token 效率 > 输出完整度。
- 默认采用最小可验证改动，不做无关重构、目录搬迁或跨模块改写。

## 默认语言

- 除非用户明确要求其他语言，否则回复、解释、计划、总结、审查意见默认使用简体中文。
- 代码、命令、路径、配置键、API 名称、类名、方法名、日志和报错原文保留原文；必要时补充中文说明。
- 当用户使用“今天 / 昨天 / 明天 / 最新 / 最近 / 当前”等相对时间表达，或问题明显具有时效性时，优先核实，并在回答中写出具体绝对日期。

## 核心工作方式

- 以本地仓库事实为先：先读代码、配置、脚本和现有 Skill，再下结论。
- 不得回滚用户或其他 Agent 未授权的改动。
- 优先更新最接近约束来源的文件，避免同一条规则散落在多个入口重复维护。
- 文档任务默认收敛为最小必要更新；实现任务默认收敛为最小可验证改动。

## 默认工作流

- `doc-only` / `rule-only` 任务：直接修改目标文档或规则文件，并检查相关引用是否仍一致。
- iOS 开发任务默认先进入 `codex-subagent-orchestration`；由主入口按任务分型器归类为 `doc-only` / `rule-only` / `code-small` / `code-medium` / `code-risky`，再决定单 Agent 还是 `lite` / `standard` / `full` 编排，并按需路由到实现、测试、审查与验证模块。
- 使用任何 Skill 前，必须先输出 `>>> Skill: <skill-name>` 声明即将使用的 skill，让用户明确知道当前路由到了哪个 skill。
- 默认进入编排入口不等于默认实际 spawn subAgent；只有用户显式要求 subAgent / parallel agent / delegation，或当前 prompt 明确授权时，才调用 Codex 原生 subAgent。未显式授权时按单 Agent 执行，但仍保留实现链路的定向验证 + `code-review` 收口。
- 默认逻辑角色集合为 `explorer + builder + reporter`；这些角色默认可由主 Agent 串行承担，只有显式授权原生 subAgent 时才拆成独立 subAgent。
- 实现型任务默认三步收口：主入口 Skill / 实现 Skill -> 定向验证 -> `code-review`。
- 审查型任务默认优先输出 blocking findings；没有阻塞项时要明确说明无 blocking findings，并指出剩余风险或验证缺口。
- 高风险任务才升级更强验证；不要把完整 build、Archive、真机验证或 FULL verification 当成默认收尾动作。
- 路由细节、验证升级条件和 Skill 切换规则以下游 Skill 与 `skills/TAXONOMY.md` 为准。

## Apple 平台工程规则

- 当任务与 iOS、macOS、watchOS、tvOS、visionOS、Swift、Objective-C、Xcode、SwiftUI、UIKit、AppKit、Foundation、Swift Package Manager、CocoaPods、Tuist、签名、打包、测试或性能相关时，默认提供专家级 Apple 平台工程指导。
- 将 OS / SDK / Xcode / Swift 语言模式 / 真机或模拟器视为一等约束；结论依赖这些条件时必须显式说明。
- 新实现默认优先 Swift 与结构化并发；UI 更新保持主线程或 `@MainActor` 隔离。
- `public` / `open` 与跨模块复用 API 需提供文档注释，并写清并发边界、副作用和失败语义。
- 新增 `.swift` / `.h` / `.m` / `.mm` 文件且项目要求文件头时，`Created by` 必须使用本机用户名称，不写 `Codex`；日期默认 `YYYY/M/D`。
- 涉及 Apple API、availability 或 WWDC 指导时，优先使用官方文档，并区分“文档事实”和“推断”。

## 验证策略

默认验证等级从低到高：

```text
NONE
LINT
AFFECTED_TESTS
BUILD
UI_SMOKE
FULL
```

规则：

- 默认选择能覆盖当前风险的最低验证等级。
- 涉及代码改动时，优先最窄定向验证：先单个 test case / test class，再最小受影响 test file / bundle。
- 不默认全量测试、完整 build、Archive 或 FULL verification。
- 如果当前改动不适合运行测试，必须给出 `no_test_reason` 与替代验证依据。
- 如果当前改动没有低成本单测路径，必须给出 `no_test_reason` 与 `suggested_validation`；不要自动升级到真机 / 模拟器验证。
- 高风险改动包括：工程配置、依赖基线、签名 / entitlements、plist / capabilities、资源打包、target membership、scheme / xctestplan、私有库集成，以及发布前信心建立。

## Xcode / iOS 验证基线

- 如果同时存在 `.xcworkspace` 和 `.xcodeproj`，验证优先使用 `.xcworkspace`。
- 优先选择绑定单元测试 `*Tests` target / bundle 的 scheme。
- iOS 验证默认优先已连接真机；无真机时再回退 simulator。
- 验证型 `xcodebuild` 优先通过目标项目根目录 `./codex_verify.sh` 执行；若项目未接入，再回退到 `~/.codex/bin/codex_verify`。
- 验证证据必须来自目标项目根目录的项目环境，不把 sandbox 中的构建结果当作完整项目环境证据。
- 可选项目环境验证继续使用 Xcode 系统 DerivedData，并通过 shared build-queue daemon 串行执行；可用 `codex_verify.sh --queue-status` 查看队列状态。

## CocoaPods / 私有组件规则

- 涉及 CocoaPods / 私有组件联调时，先检查目标工程 `Podfile`、`Podfile.lock` 与 `Pods/Manifest.lock`。
- 若目标依赖是本地 `:path` Pod，默认修改真实组件源码仓，不修改 `Pods/` 下的副本快照。
- 未收到明确指令前，不把验证基线切到线上版本化依赖或 `Pods/` vendored snapshot。
- 即使联调阶段允许临时切到本地 `:path` 依赖，`git commit` 前也必须恢复到可提交的远端 / 版本化依赖状态；不要提交带本地 `:path` 引用的依赖文件。

## Checkpoint 与 Fail-Fix-Report

- 编排默认遵守 checkpoint 合同：`CP0 Intent Lock`、`CP1 Anchor Slice`、`CP2 Validation Baseline Freeze`、`CP3 Final Gate`。
- 主 Agent 维护 `checkpoint_status` 作为单一事实源。
- 默认遵守 `fail-fix-report`：先定位失败、修复并重跑，再汇报；同类问题默认最多回环 2 次。

## Skill 与规则维护

- 修改 `skills/*/SKILL.md` 时，默认遵守 `docs/skills/skill-schema-v1.md`。
- 如果变更影响 Skill 的职责边界、入口建议或路由关系，同步更新 `skills/TAXONOMY.md`。
- 新增或修改 Skill 后，默认运行或建议运行：

```bash
python scripts/lint_skill_schema.py
```

- 仅在需要更严格校验时使用：

```bash
python scripts/lint_skill_schema.py --strict
```

## 完成标准

- `doc-only` / `rule-only` 任务：内容已更新，交叉引用一致，无多余改动。
- 实现任务：已完成定向测试或必要验证，且 `code-review` 无 blocking findings；如无法测试，已明确 `no_test_reason` 与替代验证建议。
- 最终回复默认包含：改了什么、如何验证、仍有哪些已知风险或后续动作。
