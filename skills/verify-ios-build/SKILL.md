---
name: verify-ios-build
description: Apple Xcode 工程的按需项目环境构建验证执行器。由用户显式要求或 `final-evidence-gate` 在现有 `xcodebuild test/build` 证据不足、高风险场景下调用；执行一次 `xcodebuild` 验证，iOS 默认优先 `.xcworkspace` 与已连接真机，找不到连接真机时回退 simulator。
---

# Verify iOS Build（项目环境构建验证执行器）

## 角色定位
- 将本 skill 作为按需项目环境验证执行器，而不是所有 Apple Xcode 改动的默认重复步骤。
- 本 skill 不作为 `testing` 的默认后继步骤；默认 testing 不会自动触发真机 / 模拟器验证。
- 在前置 `testing` 与 `code-review` 都已放行、且现有验证证据不足或风险要求完整验证时，执行一次性 `xcodebuild` 项目环境验证。
- 不负责判断低风险场景是否可接受已有证据；该裁决由 `final-evidence-gate` 完成。
- 不负责构建系统设计、签名配置或 Archive/Export 流程。
- 本 skill 应统一复用串行包装入口来执行真正的项目环境 `xcodebuild`：优先目标项目已提供的 repo-tracked `codex_verify.sh`，若项目未接入则回退到本机 `~/.codex/bin/codex_verify`，避免同机同仓多个 CLI 并发验证导致 `build.db` / `SWBBuildService` 锁冲突。

## 触发判定（硬边界）
- 用户明确要求“编译验证 / 跑一下 xcodebuild / 最后确认还能编译”时，使用本 skill。
- `final-evidence-gate` 判定现有证据不足、高风险，或用户需要发布前/完整项目环境验证时，使用本 skill。
- 建议升级的典型场景：`.xcodeproj` / `.xcworkspace` / scheme / xctestplan / xcconfig / Build Settings / 构建脚本、签名/entitlements/plist/capability、`Podfile` / `Podfile.lock` / 私有 Pod 版本或 `:path` 回切线上、资源/Storyboard/XIB/Assets/target membership、consumer app 集成证据缺失。
- 如果最后一次代码变更之后，已经有同等或更强的目标项目环境 `xcodebuild test/build` 成功证据，且 `testing` 与 `code-review` 均放行，不要无条件重复执行本 skill。
- 如果任务核心是签名、证书、Archive、导出、CI、xcconfig、build script 或 destination 策略设计，不要用本 skill 作为主 skill，切换到 `xcode-build`。
- 如果任务核心是写测试代码或选择真机 / 模拟器自动化执行路径，分别切换到 `testing`、`ios-automation`。

## 适用场景
- 当前仓库需要补一条完整项目环境构建证据。
- 现有定向测试没有覆盖最终交付 target / consumer app scheme。
- 用户明确要求单次构建检查。
- 完整 diff/PR 审查或工作区未提交代码审查交给 `code-review`。

## 核心工作流
1. 确认前置 `testing` 与 `code-review` 已完成，且 `code-review` 没有 `blocking_findings`；若是由 `final-evidence-gate` 升级，记录升级原因。
2. 运行当前 skill 自带的 `scripts/build-check.sh <目标仓库根目录>`。
   - `scripts/build-check.sh` 指的是 **本 skill 目录下** 的脚本路径，不是目标仓库根目录里的同名脚本。
   - 不要因为目标仓库没有 `scripts/build-check.sh` 就误判 skill 不可执行。
   - 如果目标仓库根目录存在 repo-tracked `codex_verify.sh`，`build-check.sh` 应先委托给该包装入口获取项目级串行锁；若项目未接入，则自动回退到本机 `~/.codex/bin/codex_verify`；随后再由包装入口回调本 skill 的 `build-check.sh`。不要绕过包装入口并发裸跑 `xcodebuild`。
   - 项目环境验证必须在**目标项目根目录**执行（CC 使用 `Bash` 工具；Codex 使用 `functions.exec_command` + `sandbox_permissions="require_escalated"` / `require_escalated`）；不要把沙箱内构建结果当作最终验收。
   - 本地 `xcodebuild` 命令（含 `-list` / `-showdestinations` / build/test）统一按非沙盒项目环境执行，不做沙盒内降级。
3. `build-check.sh` 的首次校验选择顺序固定为：
   - `.codex/xcodebuild.env` 显式设置了 `XCODE_DESTINATION`：按显式 destination 执行；
   - iOS 工程且同时存在 `.xcworkspace` 与 `.xcodeproj`：始终优先 `.xcworkspace`；
   - 如果同一任务中已经先跑过定向测试或其它 build/test，验证默认复用同一套 workspace / scheme / destination 基线；不要无说明切换 scheme；
   - 私有库 / 私有组件改动默认使用主项目本地 `:path` 私有库依赖执行项目环境验证；未收到明确指令前，不要回切线上版本化依赖或 `Pods/` vendored snapshot 作为验证基线；
   - 如果用户没有显式指定 `XCODE_SCHEME`，默认优先选择绑定了单元测试 `*Tests` target / bundle 的 scheme；若不存在，再回退到其它测试 scheme（例如 `*UITests`、`*_TEST`）；
   - iOS 工程未显式 destination：优先已连接真机；找不到连接中的真机时自动回退到 simulator；
   - macOS Xcode 工程：走宿主机 `xcodebuild build`，不强行拼装 iOS destination。
4. 真机选择必须基于 `xcodebuild -showdestinations` 的真实 iOS destination，并结合 `xcrun devicectl list devices` 只选择 `connected` 设备；不要把已配对但未连接的设备当作默认最终验证目标。
5. 只有当首次校验是 simulator，且 simulator 失败、首个真实失败点命中“第三方依赖导致的 simulator-only 链接白名单错误”时，脚本才自动切换到已连接真机再校验一次。
6. 如果首次 simulator 失败但首个真实失败点属于本次实现链路自己的真实错误，或不属于白名单错误，则不要切真机，直接按真实失败收口；如果需要真机回退但当前没有连接中的真实 iOS destination，明确写出阻塞原因。
7. 只有当本 skill 成功完成时，`final-evidence-gate` 才能接受该验证证据；若验证失败、被环境阻塞、或还没拿到项目环境结果，最终回复必须明确完整验证失败点、默认收口证据与残余风险。
8. 最终回复直接给构建结果；如果用户显式走 simulator 且触发真机回退，要分别说明 simulator 阶段与真机阶段的结果。
9. 如果首次构建成功且满足以下条件，执行 UI smoke：
   - `XCODE_UI_SMOKE_MODE=auto|required`；
   - 当前变更命中 UI 敏感文件（View/ViewController/Router/Coordinator/Storyboard/XIB/Assets）；
   - 首次 destination 为 simulator；
   - `XCODE_UI_SMOKE_SPEC` 指向的 spec 文件存在（默认 `.codex/ui-smoke.yml`，该文件属于目标仓库可选文件，不存在时按 mode 规则处理）。
10. UI smoke 采用 text-first 验证：优先基于 accessibility tree 的结构化断言；截图只用于视觉证据和失败取证，不作为唯一状态判断依据。

## 特殊情况
- 不要求本 skill 再自行审查本次任务全量差异与直接影响面；这些属于前置 `code-review` 职责。
- 不要让 `.codex/xcodebuild.env` 覆盖配置绕过前置 `testing` / `code-review`；它只用于指定 workspace/project/scheme/configuration/destination。
- `codex_verify.sh` / `~/.codex/bin/codex_verify` 只负责串行化项目环境验证，不改变本 skill 的 workspace / scheme / destination 选择策略，也不能绕过前置 `testing` / `code-review`。
- 本地 `verify-ios-build` 不支持 `XCODE_DERIVED_DATA` 覆盖；统一使用 Xcode 默认 DerivedData（`~/Library/Developer/Xcode/DerivedData`）。
- `.codex/xcodebuild.env` 可以额外控制默认真机 destination 选择，或显式切到 simulator 首次校验并控制回退行为，但不能绕过固定链路里的 `testing` / `code-review` 放行，也不能把项目环境验证降级回沙箱。
- 如果当前 turn 已经先执行过定向测试，验证应优先复用同一套 workspace / scheme / destination 基线；若先前执行路径与默认策略不一致，必须在回复里明确说明为什么切换。
- 如果仓库不是 Xcode 工程，直接说明本 skill 不适用，而不是伪造构建结论。
- 真机是 iOS 最终 `build` 校验的默认首选路径；找不到连接中的真机时才切 simulator。若是 macOS Xcode 工程，则直接走宿主机 build。
- 如果任务已经变成 test / install / launch / 签名策略设计，不要继续扩展本 skill，切换到 `ios-automation` 或 `xcode-build`。
- UI smoke 控制变量：
  - `XCODE_UI_SMOKE_MODE=off|auto|required`（默认 `auto`）
  - `XCODE_UI_SMOKE_SPEC=<relative-path>`（默认 `.codex/ui-smoke.yml`）
  - `auto` 模式下 spec 不存在只告警不阻塞；`required` 模式下 spec 不存在或 smoke 失败会阻塞门禁。

## 输出要求
按以下顺序组织最终回复：
1. 前置阶段状态（`testing` 是否完成、`code-review` 是否放行）与升级原因（如来自 `final-evidence-gate`）
2. 首次构建阶段使用的 workspace/project、scheme、configuration、destination、结果；如果是默认真机路径，再补充选中的 connected device destination 与选择原因；如果是 simulator / macOS 路径，也写明回退或选择原因；如果失败，给出首个真实失败点
3. 若显式 simulator 且触发真机回退，再补充：选中的 device destination、结果，以及是否成功完成回退校验
4. 如果被阻塞或失败，明确阻塞点或首个真实错误，并说明默认收口证据与残余风险
5. 如果触发了 UI smoke，补充说明：spec 路径、是否执行、结果，以及失败证据目录（如有）

## 参考资源
- `scripts/build-check.sh`
- `references/override-config.md`

## 与其他技能的关系
- 当任务已经实现完成，且 `final-evidence-gate` 判定需要补完整项目环境构建证据时，使用本技能。
- 如果当前任务属于非编排 / 单 Agent 的实现链路，本 skill 只作为 `final-evidence-gate` 的升级执行器，不再无条件承接第四步。
- 需要完整 diff/PR 审查、API 设计评审或非收尾阶段 code review 时，切换到 `code-review`。
- 如果任务本身是在改 Build Settings、签名、Archive/Export、CI 或构建脚本，主技能应是 `xcode-build`。
- 本技能不替代测试编写；需要补单元测试或 UI 测试时切换到 `testing`。
- 本技能只负责“项目环境构建验证”，不替代默认的定向验证、`testing`、`code-review` 流程，也不替代 `final-evidence-gate` 的完成态裁决。
