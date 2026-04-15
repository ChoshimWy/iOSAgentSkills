---
name: verify-ios-build
description: 在 iOS/Swift/Objective-C/Xcode 工程任务收尾阶段，处理“编译验证 / 构建验证 / 构建检查 / 门禁验收 / 最后确认还能编译 / 跑一下 xcodebuild / 最后验证一下”这类请求：先对当前未提交代码（staged、unstaged、untracked）做一次静态代码审查，再在没有 🔴 严重问题时执行一次默认优先真机的 `xcodebuild` 构建校验。只用于最终质量门禁与编译确认；不要把它当作 Build Settings、签名、Archive/Export、CI/CD、复杂设备选择、运行时排障或测试编写 skill。
---

# Verify iOS Build（收尾审查 + 编译校验）

## 角色定位
- 将本 skill 作为任务末尾的质量门禁。
- 先审查当前工作区未提交变更，再决定是否执行一次性 `xcodebuild`。
- 不负责构建系统设计、签名配置或 Archive/Export 流程。

## 触发判定（硬边界）
- 用户在任务收尾阶段要求“编译验证 / 跑一下 xcodebuild / 最后确认还能编译”时，使用本 skill。
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
5. 如果存在任意 `🔴`，立即停止，并在最终回复中明确写出“因审查发现严重问题，未执行 xcodebuild”。
6. 如果没有 `🔴`，再运行当前 skill 自带的 `scripts/build-check.sh <目标仓库根目录>`。
   - `scripts/build-check.sh` 指的是 **本 skill 目录下** 的脚本路径，不是目标仓库根目录里的同名脚本。
   - 不要因为目标仓库没有 `scripts/build-check.sh` 就误判 skill 不可执行。
7. `build-check.sh` 默认优先使用真机做 `build` 校验；如果仓库根目录的 `.codex/xcodebuild.env` 显式设置了 `XCODE_DESTINATION`，则按该 destination 执行首次校验。
8. 默认真机自动选择基于 `xcodebuild -showdestinations` 的真实 iOS destination，不依赖 `devicectl` device identifier。
9. 只有当首次校验被显式配置为 simulator，且 simulator 失败、首个真实失败点命中“第三方依赖导致的 simulator-only 链接白名单错误”、同时失败点不在本次未提交改动文件中时，脚本才自动切换到真机再校验一次。
10. 如果首次 simulator 失败但首个真实失败点在本次改动范围内，或不属于白名单错误，则不要切真机，直接按真实失败收口；如果默认真机校验或 simulator → 真机回退需要设备，但当前没有真实 iOS destination，明确写出阻塞原因。
11. 最终回复先给审查结论，再给构建结果；如果用户显式走 simulator 且触发真机回退，要分别说明 simulator 阶段与真机阶段的结果。

## 特殊情况
- 如果工作区没有未提交改动，明确说明“没有待审查 diff”，然后直接执行当前 skill 自带的 `scripts/build-check.sh <目标仓库根目录>`。
- 不要让 `.codex/xcodebuild.env` 覆盖配置绕过前置审查；它只用于指定 workspace/project/scheme/configuration/destination。
- `.codex/xcodebuild.env` 可以额外控制默认真机 destination 选择，或显式切到 simulator 首次校验并控制回退行为，但不能绕过“先审查、再判定是否放行构建”的总流程。
- 如果仓库不是 Xcode 工程，直接说明本 skill 不适用，而不是伪造构建结论。
- 真机是默认最终 `build` 校验路径；simulator 仅在显式配置 destination 时作为首次校验路径。如果任务已经变成 test / install / launch / 签名策略设计，不要继续扩展本 skill，切换到 `ios-device-automation` 或 `xcode-build`。

## 输出要求
按以下顺序组织最终回复：
1. 未提交代码范围（staged / unstaged / untracked 的实际情况）
2. 审查 findings（按严重度排序；`🔴` 优先）
3. 是否放行 `xcodebuild`
4. 首次构建阶段使用的 workspace/project、scheme、configuration、destination、结果；如果是默认真机路径，再补充选中的 device destination 与选择原因；如果失败，给出首个真实失败点
5. 若显式 simulator 且触发真机回退，再补充：选中的 device destination、结果，以及是否成功完成回退校验
6. 如果被阻塞或失败，明确阻塞点或首个真实错误

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
