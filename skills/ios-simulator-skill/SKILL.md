---
name: ios-simulator-skill
description: iOS 模拟器自动化技能。提供 21 个生产可用脚本，覆盖构建测试、语义导航、无障碍检查和模拟器生命周期管理，适合 AI agent 低 token 自动化执行。
---

# iOS Simulator 自动化技能 / iOS Simulator Automation

## 角色定位 / Role
- 专项自动化 skill，负责 iOS Simulator 场景下的构建、交互、验证与设备管理。
- 优先通过可访问性树和结构化输出驱动自动化，而不是像素坐标。
- 不负责业务功能实现本身，也不替代通用代码重构或架构设计。

## 适用场景 / Use Cases
- 需要在模拟器中进行稳定的 UI 自动化操作与回归验证。
- 需要语义化导航（按文本、类型、可访问性 ID）而非截图猜测。
- 需要批量管理模拟器生命周期（boot/shutdown/create/delete/erase）。
- 需要自动化执行无障碍检查、视觉差异比对、测试记录与状态抓取。

## 核心工作流 / Core Workflow
1. 环境检查 / Environment check
- `bash scripts/sim_health_check.sh`

2. 启动与状态 / Launch and state
- `python3 scripts/app_launcher.py --launch <bundle_id>`
- `python3 scripts/screen_mapper.py`

3. 语义交互 / Semantic interaction
- `python3 scripts/navigator.py --find-text "Login" --tap`
- `python3 scripts/navigator.py --find-type TextField --enter-text "user@example.com"`

4. 校验与诊断 / Verification and diagnostics
- `python3 scripts/accessibility_audit.py`
- `python3 scripts/app_state_capture.py --app-bundle-id <bundle_id>`

5. 设备维护 / Device lifecycle
- `python3 scripts/simctl_boot.py --name "iPhone 16 Pro"`
- `python3 scripts/simctl_shutdown.py --all`

## 脚本能力分组 / Script Capability Map
- Build & Logs
- `build_and_test.py`, `log_monitor.py`

- Navigation & Interaction
- `screen_mapper.py`, `navigator.py`, `gesture.py`, `keyboard.py`, `app_launcher.py`

- Testing & Analysis
- `accessibility_audit.py`, `visual_diff.py`, `test_recorder.py`, `app_state_capture.py`, `sim_health_check.sh`

- Advanced & Permissions
- `clipboard.py`, `status_bar.py`, `push_notification.py`, `privacy_manager.py`, `sim_list.py`, `simulator_selector.py`

- Simulator Lifecycle
- `simctl_boot.py`, `simctl_shutdown.py`, `simctl_create.py`, `simctl_delete.py`, `simctl_erase.py`

## 执行约定 / Execution Conventions
- 默认优先结构化数据：`screen_mapper.py` + `navigator.py`。
- 仅在视觉回归或展示证据时使用截图能力。
- 脚本默认输出简洁文本；需要机器可读结果时使用 `--json`。
- 未指定 `--udid` 时，脚本通常自动解析当前已启动模拟器。

## 参考资源 / References
- `references/accessibility_checklist.md`
- `references/test_patterns.md`
- `references/simctl_quick.md`
- `references/idb_quick.md`
- `references/troubleshooting.md`

## 与其他技能的关系 / Skill Boundaries
- 需要实现业务 Swift 代码时，切换到 `ios-base`。
- 需要补单元测试或 UI 测试工程代码时，切换到 `testing`。
- 需要 crash/运行时根因排查时，切换到 `debugging`。
- 需要任务收尾的一次性 `xcodebuild` 编译验收时，切换到 `verify-ios-build`。
- 需要改 Build Settings、签名、Archive/Export、CI/CD 时，切换到 `xcode-build`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: ios-simulator-skill`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的配置规范与执行约定
