---
name: final-evidence-gate
description: Apple Xcode 项目改动的条件化最终证据门禁。用于在 `testing` 与 `code-review` 放行后判断现有 xcodebuild test/build 证据是否足够；证据不足、高风险或命中工程/依赖/签名类改动时，再切到 `verify-ios-build` 执行项目环境最终验证。
---

# Final Evidence Gate（条件化最终证据门禁）

## 角色定位
- 作为 Apple Xcode 项目改动的最终完成态裁决层。
- 不默认重复运行 `verify-ios-build`；优先复用最后一次代码变更之后已经成功的 `xcodebuild test` / `xcodebuild build` 证据。
- 当现有证据不足、风险较高或变更类型要求完整项目环境验证时，升级到 `verify-ios-build`。
- 如果需要补跑项目环境验证，应统一复用串行包装入口：优先目标项目已接入的 repo-tracked `codex_verify.sh`，若项目未接入则回退到本机 `~/.codex/bin/codex_verify`，让同机同仓多个 CLI 的验证请求排队串行执行，而不是并发裸跑 `xcodebuild`。

## 进入条件
- 当前任务修改了 Apple Xcode 项目相关内容，且 `testing` 与 `code-review` 已完成。
- `code-review` 无 `blocking_findings`。
- 主 Agent 已掌握本轮实际验证命令、workspace/project、scheme、destination、结果与验证发生时间点。

## 可接受已有证据的条件
同时满足以下条件时，可不重复运行 `verify-ios-build`：
1. 最后一次 repo-tracked 代码变更之后，已经成功执行过目标项目环境中的 `xcodebuild test` 或 `xcodebuild build`。
2. 验证覆盖最终交付 target 或同等/更强的 consumer app scheme；定向库测试不能替代 consumer app 集成证据。
3. 使用的 workspace/project、scheme、destination 与本轮最终交付基线一致，或明确更严格。
4. `testing` 记录了 `executed_validation`，并给出 `suggested_validation` / `failure_attribution` / `needs_test_code` / `no_test_reason`（如适用）。
5. `code-review` 明确审查验证故事，未发现阻塞风险。

## 必须升级到 `verify-ios-build` 的场景
- 修改 `.xcodeproj`、`.xcworkspace`、scheme、test plan、xcconfig、Build Settings、构建脚本。
- 修改签名、证书、entitlements、plist、capability、App Extension 或真实设备能力相关配置。
- 修改 `Podfile`、`Podfile.lock`、`Pods/Manifest.lock`、私有 Pod 版本，或从本地 `:path` 切回线上依赖。
- 修改资源、Storyboard/XIB、Assets、target membership、InfoPlist.strings、bundle packaging 相关内容。
- 定向测试只覆盖子库/子 target，不能证明主 App/consumer app 已集成通过。
- 测试后又发生代码、配置、资源或依赖快照变更。
- `code-review` 认为测试覆盖不足、验证基线不一致、或存在必须通过完整 build 暴露的问题。

## 输出合同
最终汇报必须给出：
- `final_evidence_gate`: `accepted_existing_evidence` / `ran_verify_ios_build` / `blocked_insufficient_evidence`
- 已接受或执行的验证命令类型、workspace/project、scheme、destination、结果。
- 是否发生过验证后的代码变更。
- 如果跳过 `verify-ios-build`，说明跳过原因与证据充分性。
- 如果证据不足且无法补跑，明确写出“验证证据不足，任务未完成”。

## 与其他技能的关系
- `testing` 负责补测试、执行或建议定向验证，并记录验证证据。
- `code-review` 负责静态审查和验证故事审查。
- `verify-ios-build` 是本门禁的升级执行器，只在证据不足、高风险或命中强制场景时运行。
- `xcode-build` 仍负责构建配置、签名、Archive/Export、CI/CD 设计。
- `codex_verify.sh` / `~/.codex/bin/codex_verify` 是验证入口层的并发控制机制；它们不替代本门禁的证据裁决，只负责把真正需要执行的项目环境验证串行化。
