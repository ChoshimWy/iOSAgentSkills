---
name: ios-simulator-automation
description: iOS 模拟器自动化技能。只在 Simulator 场景下进行构建测试、语义导航、无障碍检查、视觉比对与模拟器生命周期管理；如果目标是 physical device、Build Settings / 签名策略设计或普通业务代码实现，不要使用本 skill 作为主 skill；若任务产出修改了 Apple Xcode 项目相关内容，收尾必须切到 `verify-ios-build` 并在项目环境完成最终验证。
---

# iOS Simulator 自动化

## 角色定位
- 专项自动化 skill，负责 iOS Simulator 场景下的构建、交互、验证与设备管理。
- 优先通过可访问性树和结构化输出驱动自动化，而不是像素坐标。
- 不负责普通业务功能实现，也不替代通用代码重构或架构设计。

## 触发判定（硬边界）
- 先按设备维度判断：目标是 Simulator 时才使用本 skill。
- 如果目标已经明确为连接中的真机或 `devicectl`，不要用本 skill 作为主 skill，切换到 `ios-device-automation`。
- 如果问题核心是签名、Build Settings、Archive 或 CI，不要用本 skill 作为主 skill，切换到 `xcode-build`。

## 适用场景
- 需要在模拟器中进行稳定的 UI 自动化操作与回归验证。
- 需要语义化导航（按文本、类型、可访问性 ID）而非截图猜测。
- 需要批量管理模拟器生命周期（boot / shutdown / create / delete / erase）。
- 需要自动化执行无障碍检查、视觉差异比对、测试记录与状态抓取。

## 核心工作流
1. 环境检查：`bash scripts/sim_health_check.sh`
2. 启动与状态：`python3 scripts/app_launcher.py --launch <bundle_id>`、`python3 scripts/screen_mapper.py`
3. 语义交互：`python3 scripts/navigator.py --find-text "Login" --tap`
4. 校验与诊断：`python3 scripts/accessibility_audit.py`、`python3 scripts/app_state_capture.py --app-bundle-id <bundle_id>`
5. 设备维护：`python3 scripts/simctl_boot.py --name "iPhone 16 Pro"`、`python3 scripts/simctl_shutdown.py --all`

## 脚本能力分组
- Build & Logs：`build_and_test.py`、`log_monitor.py`
- Navigation & Interaction：`screen_mapper.py`、`navigator.py`、`gesture.py`、`keyboard.py`、`app_launcher.py`
- Testing & Analysis：`accessibility_audit.py`、`visual_diff.py`、`test_recorder.py`、`app_state_capture.py`、`sim_health_check.sh`
- Advanced & Permissions：`clipboard.py`、`status_bar.py`、`push_notification.py`、`privacy_manager.py`、`sim_list.py`、`simulator_selector.py`
- Simulator Lifecycle：`simctl_boot.py`、`simctl_shutdown.py`、`simctl_create.py`、`simctl_delete.py`、`simctl_erase.py`

## 执行约定
- 默认优先结构化数据：`screen_mapper.py` + `navigator.py`。
- 仅在视觉回归或展示证据时使用截图能力。
- 脚本默认输出简洁文本；需要机器可读结果时使用 `--json`。
- 未指定 `--udid` 时，脚本通常自动解析当前已启动模拟器。

## 参考资源
- `references/accessibility_checklist.md`
- `references/test_patterns.md`
- `references/simctl_quick.md`
- `references/idb_quick.md`
- `references/troubleshooting.md`

## 强制收尾验证
- 只要当前任务产出修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、构建脚本、plist / entitlements / xcconfig / scheme 或项目内环境配置），最终必须切到 `verify-ios-build`。
- 最终门禁必须在目标项目根目录的项目环境执行；沙箱内的构建结果不能作为最终验收结论。
- 对 iOS 项目，`verify-ios-build` 必须优先 `.xcworkspace`（当 `.xcworkspace` 与 `.xcodeproj` 同时存在时），并默认优先已连接真机；找不到连接中的真机时再回退到 simulator。
- 在 `verify-ios-build` 成功前，不得把任务表述为“已完成”；只能明确说明“实现已完成，但验证未完成/失败，任务未完成”。

## 与其他技能的关系
- 需要实现通用业务代码时，切换到 `ios-feature-implementation`、`swiftui-feature-implementation` 或 `uikit-feature-implementation`。
- 需要在连接中的真机上构建、安装、启动或测试时，切换到 `ios-device-automation`。
- 需要补单元测试或 UI 测试工程代码时，切换到 `testing`。
- 需要 crash / 运行时根因排查时，切换到 `debugging`。
- 需要任务收尾的一次性 `xcodebuild` 编译验收时，切换到 `verify-ios-build`。
- 需要改 Build Settings、签名、Archive/Export、CI/CD 时，切换到 `xcode-build`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定当前任务已经加载并正在使用本 Skill 时：

- 在回复末尾追加一行：`// skill-used: ios-simulator-automation`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的配置规范与执行约定
