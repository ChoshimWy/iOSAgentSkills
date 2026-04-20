---
name: ios-device-automation
description: iOS 真机自动化技能。只在连接或已配对的 physical device 上发现与选择目标设备、执行 build/test、安装 app、启动/终止进程、查询设备信息并做常见真机诊断；如果目标是 Simulator、Build Settings / 签名策略设计或普通业务代码实现，不要使用本 skill 作为主 skill；若任务产出修改了 Apple Xcode 项目相关内容，收尾必须切到 `verify-ios-build` 并在项目环境完成最终验证。
---

# iOS 真机自动化

## 角色定位
- 专项自动化 skill，负责连接中的 iPhone / iPad 真机选择、构建、安装、启动、测试与诊断。
- 默认优先使用 Apple 官方工具链：`xcrun devicectl` 与 `xcodebuild -destination 'id=...'`。
- 不负责 Build Settings / 签名策略设计，也不替代普通业务实现与代码重构。

## 触发判定（硬边界）
- 先按设备维度判断：目标是连接中的 iPhone / iPad 真机时才使用本 skill。
- 如果任务核心是 Simulator、语义 UI 导航或模拟器生命周期，不要用本 skill 作为主 skill，切换到 `ios-simulator-automation`。
- 如果阻塞点已经收缩成签名、证书、Build Settings、Archive 或 CI，不要继续把本 skill 当作主 skill，切换到 `xcode-build`。

## 适用场景
- 需要在已连接或已配对的真机上跑 build、test、install、launch。
- 需要在多台连接中的设备里自动选择最合适的真机目标。
- 需要查看设备详情、已装 app、运行中进程，或收集真机侧诊断信息。
- 需要对 pairing、DDI、锁屏、开发者模式、信任关系等常见真机问题做初步排查。

## 核心工作流
1. 手动查看真机时直接用官方命令：
   - `xcrun devicectl list devices`：查看 `devicectl` 设备标识（安装 / 启动 / 诊断使用）
   - `xcodebuild -showdestinations -workspace <workspace> -scheme <scheme>`：查看 `xcodebuild` destination id（build / test 使用）
2. 对真机执行构建或测试：`bash scripts/device_build_and_test.sh <repo-root>`
3. 需要安装或启动 app 时，执行：`bash scripts/device_install_and_launch.sh --app <path> --bundle-id <bundle_id>`
4. 需要设备详情或诊断时，执行：`bash scripts/device_diagnose.sh --device <devicectl-device-id>`

## 默认设备选择策略
1. build / test：优先使用 `xcodebuild -showdestinations` 返回的首个真实 iOS destination；若显式传 `--device-id`，直接使用该 destination id
2. install / launch / diagnose：优先 `connected`
3. 其次 `available (paired)`
4. 再使用用户显式指定的设备名称或 identifier
5. `unavailable` 仅作为诊断对象，不作为默认运行目标

## 默认 scheme 选择策略
1. 如果用户或 `.codex/xcodebuild.env` 显式指定了 scheme，直接复用
2. 如果未显式指定且仓库存在带测试标记的 scheme，默认优先选择这类 scheme（例如 `*Tests`、`*UITests`、`*_TEST`）
3. 如果不存在带测试标记的 scheme，再回退到其他共享 scheme
4. 如果同一任务后续还要执行 `verify-ios-build`，最终门禁默认复用这次 build / test 的 workspace / scheme / destination 基线；不要无说明切换

## 执行约定
- 真机构建默认用 `xcodebuild -destination 'id=<destination-id>'`，不替代签名配置；签名问题交给 `xcode-build`。
- 安装、启动、进程查询与诊断使用 `devicectl` 的 device identifier；不要把 `xcodebuild` destination id 与 `devicectl` device identifier 混用。
- 如果自动设备发现暂时不可用，优先回退到用户显式提供的 `--device-id` / 设备名称，而不是伪造设备选择结果。
- 输出中必须明确写出：设备范围、最终选择结果、实际命令、执行结果与阻塞点。
- 如果任务中新建 `.swift`、`.h`、`.m`、`.mm` 等源码文件且项目要求文件头，`Created by` 必须使用本机用户名称 `Choshim.Wei`，不要写 `Codex`；日期默认使用 `YYYY/M/D`，例如 `Created by Choshim.Wei on 2026/4/11.`。

## 参考资源
- `references/devicectl-quick.md`
- `references/troubleshooting.md`

## 强制收尾验证
- 只要当前任务产出修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、构建脚本、plist / entitlements / xcconfig / scheme 或项目内环境配置），最终必须切到 `verify-ios-build`。
- 最终门禁必须在目标项目根目录的项目环境执行；沙箱内的构建结果不能作为最终验收结论。
- 如果同一任务里已经先跑过定向测试或真机构建，`verify-ios-build` 默认复用同一套 workspace / scheme / destination 基线；不要无说明切到另一个 scheme。
- 如果用户没有显式指定 scheme，定向测试与最终门禁默认优先选择带测试标记的 scheme（例如 `*Tests`、`*UITests`、`*_TEST`）。
- 对 iOS 项目，`verify-ios-build` 必须优先 `.xcworkspace`（当 `.xcworkspace` 与 `.xcodeproj` 同时存在时），并默认优先已连接真机；找不到连接中的真机时再回退到 simulator。
- 在 `verify-ios-build` 成功前，不得把任务表述为“已完成”；只能明确说明“实现已完成，但验证未完成/失败，任务未完成”。

## 与其他技能的关系
- 需要 Simulator 自动化、语义导航或模拟器生命周期管理时，切换到 `ios-simulator-automation`。
- 需要普通 iOS 业务实现时，切换到 `ios-feature-implementation`、`swiftui-feature-implementation` 或 `uikit-feature-implementation`。
- 需要 Build Settings、签名、Archive/Export 或 CI/CD 时，切换到 `xcode-build`。
- 需要收尾的一次性构建验收时，切换到 `verify-ios-build`。
- 需要补单元测试或 UI 测试代码时，切换到 `testing`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定当前任务已经加载并正在使用本 Skill 时：

- 在回复末尾追加一行：`// skill-used: ios-device-automation`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的配置规范与执行约定
