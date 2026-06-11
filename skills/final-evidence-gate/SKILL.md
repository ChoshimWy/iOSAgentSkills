---
name: final-evidence-gate
description: Apple Xcode 项目改动的按需证据验证。用于用户显式要求、发布前自检或高风险场景下，在 `testing` 与 `code-review` 放行后判断现有 xcodebuild test/build 证据是否足够；必要时再切到 `verify-ios-build` 执行项目环境验证。
---

# Final Evidence Gate（条件化可选证据验证）

## 角色定位
- 作为 Apple Xcode 项目改动的按需证据裁决层，不参与所有实现任务的默认强制收尾。
- 不默认重复运行 `verify-ios-build`；优先复用最后一次代码变更之后已经成功的 `xcodebuild test` / `xcodebuild build` 证据。
- 当用户显式要求、发布前自检、现有证据不足或风险较高时，可建议升级到 `verify-ios-build`。
- 如果需要补跑项目环境验证，应统一复用串行包装入口：优先目标项目已接入的 repo-tracked `codex_verify.sh`，若项目未接入则回退到本机 `~/.codex/bin/codex_verify`，让同机同仓多个 CLI 的验证请求排队串行执行，而不是并发裸跑 `xcodebuild`。

## 进入条件
- 用户显式要求、发布前自检，或主 Agent 判断当前 Apple Xcode 项目改动需要补强完整项目环境证据。
- `testing` 与 `code-review` 已完成。
- `code-review` 无 `blocking_findings`。
- 主 Agent 已掌握本轮实际验证命令、workspace/project、scheme、destination、结果与验证发生时间点。

## 可接受已有证据的条件
同时满足以下条件时，可不重复运行 `verify-ios-build`：
1. 最后一次 repo-tracked 代码变更之后，已经成功执行过目标项目环境中的 `xcodebuild test` 或 `xcodebuild build`。
   - 对 `code-small` / `code-medium` 的纯逻辑或业务层改动，若最后一次代码变更之后已经成功执行最窄定向单测，且 `code-review` 未发现 consumer app 集成缺口、工程/依赖/签名/资源或设备能力风险，可直接接受为已有充分证据。
2. 验证覆盖最终交付 target 或同等/更强的 consumer app scheme；定向库测试不能替代 consumer app 集成证据。
   - 私有库 / 私有组件改动的 consumer app 集成证据默认必须来自主项目本地 `:path` 私有库依赖基线；未收到明确指令前，不接受线上版本化依赖或 `Pods/` vendored snapshot 作为验证基线。
3. 使用的 workspace/project、scheme、destination 与本轮最终交付基线一致，或明确更严格。
4. `testing` 记录了 `executed_validation`，并给出 `suggested_validation` / `failure_attribution` / `needs_test_code` / `no_test_reason`（如适用）。
5. `code-review` 明确审查验证故事，未发现阻塞风险。

## 建议升级到 `verify-ios-build` 的场景
- 修改 `.xcodeproj`、`.xcworkspace`、scheme、test plan、xcconfig、Build Settings、构建脚本。
- 修改签名、证书、entitlements、plist、capability、App Extension 或真实设备能力相关配置。
- 修改 `Podfile`、`Podfile.lock`、`Pods/Manifest.lock`、私有 Pod 版本，或从本地 `:path` 切回线上依赖。
- 修改资源、Storyboard/XIB、Assets、target membership、InfoPlist.strings、bundle packaging 相关内容。
- 定向测试只覆盖子库/子 target，不能证明主 App/consumer app 已集成通过。
- `testing` 阶段没有低成本单测路径，只给出了 `no_test_reason` 与 `suggested_validation`，且当前风险不足以直接接受已有静态证据。
- 测试后又发生代码、配置、资源或依赖快照变更。
- `code-review` 认为测试覆盖不足、验证基线不一致、或存在必须通过完整 build 暴露的问题。

## 输出合同
最终汇报必须给出：
- `final_evidence_gate`: `accepted_existing_evidence` / `ran_verify_ios_build` / `blocked_insufficient_evidence`
- 已接受或执行的验证命令类型、workspace/project、scheme、destination、结果。
- 是否发生过验证后的代码变更。
- 如果跳过 `verify-ios-build`，说明跳过原因与证据充分性。
- 如果证据不足且无法补跑，明确写出“完整验证证据不足”，并说明默认收口证据与残余风险。

## 与其他技能的关系
- `testing` 负责补测试、执行或建议定向验证，并记录验证证据。
- `code-review` 负责静态审查和验证故事审查。
- `verify-ios-build` 是本技能的升级执行器，只在用户显式要求、证据不足或高风险场景时运行。
- `xcode-build` 仍负责构建配置、签名、Archive/Export、CI/CD 设计。
- `codex_verify.sh` / `~/.codex/bin/codex_verify` 是验证入口层的并发控制机制；它们不替代本门禁的证据裁决，只负责把真正需要执行的项目环境验证串行化。
