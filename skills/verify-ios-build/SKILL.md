---
name: verify-ios-build
description: Apple Xcode 工程任务的强制收尾验证技能。只要任务产出修改了 Apple Xcode 项目相关内容，就必须在项目环境切到本 skill：先对当前未提交代码（staged、unstaged、untracked）做静态代码审查，再在没有 🔴 严重问题时执行一次 `xcodebuild` 最终门禁；iOS 工程默认优先 `.xcworkspace` 与已连接真机，找不到连接中的真机时回退到 simulator；当命中 UI 敏感改动并启用 UI smoke 时，追加结构化 UI 断言门禁。
---

# Verify iOS Build（收尾审查 + 编译校验）

## 角色定位
- 将本 skill 作为 Apple Xcode 项目任务末尾的强制质量门禁。
- 先审查当前工作区未提交变更，再决定是否执行一次性 `xcodebuild`。
- 不负责构建系统设计、签名配置或 Archive/Export 流程。

## 触发判定（硬边界）
- 用户在任务收尾阶段要求“编译验证 / 跑一下 xcodebuild / 最后确认还能编译”时，使用本 skill。
- 只要当前任务产出修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、plist / entitlements / xcconfig / scheme、构建脚本或项目内环境配置），即使用户没单独要求，也必须在最终回复前切到本 skill。
- 如果任务核心是签名、证书、Archive、导出、CI、xcconfig、build script 或 destination 策略设计，不要用本 skill 作为主 skill，切换到 `xcode-build`。
- 如果任务核心是写测试代码或选择真机 / 模拟器自动化执行路径，分别切换到 `testing`、`ios-device-automation` 或 `ios-simulator-automation`。

## 适用场景
- 本次任务修改了会影响 iOS 构建的文件。
- 用户明确要求“编译验证”“构建检查”“跑一下 xcodebuild”。
- 在最终回复前需要确认当前仓库既没有明显严重问题，又仍能编译。
- 只对当前工作区未提交变更负责；完整 PR 审查或历史代码审查交给 `code-review`。

## 核心工作流
1. 先收集本次未提交变更，默认覆盖：
   - `git diff --cached`
   - `git diff`
   - `git ls-files --others --exclude-standard`
2. 基于这些变更做静态代码审查，优先级固定为：正确性 → 安全性 → 内存 → 并发 → 性能 → 可维护性 → 一致性。
3. 复用 `code-review` 的分级语义输出 findings：
   - `🔴` 严重问题：阻塞 `xcodebuild`
   - `🟡` 建议问题：记录但不阻塞
   - `✅` 优点：按需补充
4. 尽量为每条 finding 绑定文件与行号；如果无法精确定位，明确说明原因。
5. 如果存在任意 `🔴`，立即停止，并在最终回复中明确写出“因审查发现严重问题，未执行 xcodebuild，任务未完成”。
6. 如果没有 `🔴`，再运行当前 skill 自带的 `scripts/build-check.sh <目标仓库根目录>`。
   - `scripts/build-check.sh` 指的是 **本 skill 目录下** 的脚本路径，不是目标仓库根目录里的同名脚本。
   - 不要因为目标仓库没有 `scripts/build-check.sh` 就误判 skill 不可执行。
   - 最终门禁必须通过 `functions.exec_command` 在**目标项目根目录**执行，并显式使用 `sandbox_permissions=\"require_escalated\"` 获取项目环境；不要把沙箱内构建结果当作最终验收。
7. `build-check.sh` 的首次校验选择顺序固定为：
   - `.codex/xcodebuild.env` 显式设置了 `XCODE_DESTINATION`：按显式 destination 执行；
   - iOS 工程且同时存在 `.xcworkspace` 与 `.xcodeproj`：始终优先 `.xcworkspace`；
   - 如果同一任务中已经先跑过定向测试或其它 build/test，最终门禁默认复用同一套 workspace / scheme / destination 基线；不要无说明切换 scheme；
   - 如果用户没有显式指定 `XCODE_SCHEME`，默认优先选择绑定了单元测试 `*Tests` target / bundle 的 scheme；若不存在，再回退到其它测试 scheme（例如 `*UITests`、`*_TEST`）；
   - iOS 工程未显式 destination：优先已连接真机；找不到连接中的真机时自动回退到 simulator；
   - macOS Xcode 工程：走宿主机 `xcodebuild build`，不强行拼装 iOS destination。
8. 真机选择必须基于 `xcodebuild -showdestinations` 的真实 iOS destination，并结合 `xcrun devicectl list devices` 只选择 `connected` 设备；不要把已配对但未连接的设备当作默认最终门禁目标。
9. 只有当首次校验是 simulator，且 simulator 失败、首个真实失败点命中“第三方依赖导致的 simulator-only 链接白名单错误”、同时失败点不在本次未提交改动文件中时，脚本才自动切换到已连接真机再校验一次。
10. 如果首次 simulator 失败但首个真实失败点在本次改动范围内，或不属于白名单错误，则不要切真机，直接按真实失败收口；如果需要真机回退但当前没有连接中的真实 iOS destination，明确写出阻塞原因。
11. 只有当本 skill 成功完成时，任务才算真正完成；若验证失败、被环境阻塞、或还没拿到项目环境结果，最终回复必须明确写成“实现已完成，但验证未完成/失败，任务未完成”。
12. 最终回复先给审查结论，再给构建结果；如果用户显式走 simulator 且触发真机回退，要分别说明 simulator 阶段与真机阶段的结果。
13. 如果首次构建成功且满足以下条件，执行 UI smoke：
   - `XCODE_UI_SMOKE_MODE=auto|required`；
   - 当前变更命中 UI 敏感文件（View/ViewController/Router/Coordinator/Storyboard/XIB/Assets）；
   - 首次 destination 为 simulator；
   - `XCODE_UI_SMOKE_SPEC` 指向的 spec 文件存在（默认 `.codex/ui-smoke.yml`）。
14. UI smoke 采用 text-first 验证：优先基于 accessibility tree 的结构化断言；截图只用于视觉证据和失败取证，不作为唯一状态判断依据。

## 特殊情况
- 如果工作区没有未提交改动，明确说明“没有待审查 diff”，然后直接执行当前 skill 自带的 `scripts/build-check.sh <目标仓库根目录>`。
- 不要让 `.codex/xcodebuild.env` 覆盖配置绕过前置审查；它只用于指定 workspace/project/scheme/configuration/destination。
- `.codex/xcodebuild.env` 可以额外控制默认真机 destination 选择，或显式切到 simulator 首次校验并控制回退行为，但不能绕过“先审查、再判定是否放行构建”的总流程，也不能把最终门禁从项目环境降级回沙箱。
- 如果当前 turn 已经先执行过定向测试，最终门禁应优先复用同一套 workspace / scheme / destination 基线；若先前执行路径与默认策略不一致，必须在回复里明确说明为什么切换。
- 如果仓库不是 Xcode 工程，直接说明本 skill 不适用，而不是伪造构建结论。
- 真机是 iOS 最终 `build` 校验的默认首选路径；找不到连接中的真机时才切 simulator。若是 macOS Xcode 工程，则直接走宿主机 build。
- 如果任务已经变成 test / install / launch / 签名策略设计，不要继续扩展本 skill，切换到 `ios-device-automation` 或 `xcode-build`。
- UI smoke 控制变量：
  - `XCODE_UI_SMOKE_MODE=off|auto|required`（默认 `auto`）
  - `XCODE_UI_SMOKE_SPEC=<relative-path>`（默认 `.codex/ui-smoke.yml`）
  - `auto` 模式下 spec 不存在只告警不阻塞；`required` 模式下 spec 不存在或 smoke 失败会阻塞门禁。

## 输出要求
按以下顺序组织最终回复：
1. 未提交代码范围（staged / unstaged / untracked 的实际情况）
2. 审查 findings（按严重度排序；`🔴` 优先）
3. 是否放行 `xcodebuild`
4. 首次构建阶段使用的 workspace/project、scheme、configuration、destination、结果；如果是默认真机路径，再补充选中的 connected device destination 与选择原因；如果是 simulator / macOS 路径，也写明回退或选择原因；如果失败，给出首个真实失败点
5. 若显式 simulator 且触发真机回退，再补充：选中的 device destination、结果，以及是否成功完成回退校验
6. 如果被阻塞或失败，明确阻塞点或首个真实错误，并明确写出“任务未完成”
7. 如果触发了 UI smoke，补充说明：spec 路径、是否执行、结果，以及失败证据目录（如有）

## 参考资源
- `scripts/build-check.sh`
- `references/override-config.md`

## 与其他技能的关系
- 当任务已经实现完成，需要在最终回复前确认“没有严重问题且还能编译”时，优先使用本技能。
- 需要完整 diff/PR 审查、API 设计评审或非收尾阶段 code review 时，切换到 `code-review`。
- 如果任务本身是在改 Build Settings、签名、Archive/Export、CI 或构建脚本，主技能应是 `xcode-build`。
- 本技能不替代测试编写；需要补单元测试或 UI 测试时切换到 `testing`。
- 本技能只在“收尾门禁 + 最终构建确认”场景下复用审查标准，不替代通用 code review 流程。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: verify-ios-build`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的配置规范与构建流程
