---
name: ios-automation
description: iOS 设备自动化技能（模拟器 + 真机统一入口）。按目标设备类型自动路由到 Simulator 或真机子模式；Simulator 场景覆盖构建测试、语义导航、无障碍检查、视觉比对与模拟器生命周期管理；真机场景覆盖设备发现、build/test、安装、启动、进程查询与常见真机诊断；如果问题核心是签名、Build Settings 设计或普通业务代码实现，不要使用本 skill 作为主 skill；若任务产出修改了 Apple Xcode 项目相关内容，收尾必须进入 `final-evidence-gate`；证据不足、高风险或命中工程/依赖/签名/资源打包类改动时，再切到 `verify-ios-build` 在项目环境完成最终验证。
---

# iOS 设备自动化

## 角色定位

统一的 iOS 设备自动化 skill，覆盖 Simulator 和真机两种目标。根据任务中的设备类型自动选择子模式。不负责 Build Settings / 签名策略设计，也不替代普通业务实现与代码重构。

## 触发判定（硬边界）

首次判断设备维度后，后续链路固定在同一设备模式下：
- **Simulator 模式**：目标为模拟器时使用。语义导航、UI smoke、无障碍检查、模拟器生命周期。
- **真机模式**：目标为已连接/已配对的 iPhone/iPad 时使用。`xcrun devicectl` + `xcodebuild -destination 'id=...'`。
- 如果阻塞点收缩成签名、证书、Archive 或 CI，切换到 `xcode-build`。

## 设备选择策略

### Simulator
1. 未指定 `--udid` 时，自动解析当前已启动模拟器
2. 脚本默认支持 `--udid` 显式指定

### 真机
1. build/test：优先 `xcodebuild -showdestinations` 返回的首个真实 iOS destination
2. install/launch/diagnose：优先 `connected`，其次 `available (paired)`
3. 再使用用户显式指定的设备名称或 identifier
4. `unavailable` 仅作为诊断对象，不作为默认运行目标

## 核心工作流

### Simulator 模式
1. 环境检查：`bash scripts/simulator/sim_health_check.sh`
2. 启动与状态：`python3 scripts/simulator/app_launcher.py --launch <bundle_id>`、`python3 scripts/simulator/screen_mapper.py`
3. 语义交互：`python3 scripts/simulator/navigator.py --find-text "Login" --tap`
4. 校验与诊断：`python3 scripts/simulator/accessibility_audit.py`、`python3 scripts/simulator/app_state_capture.py --app-bundle-id <bundle_id>`
   - 结构化 UI smoke：`python3 scripts/simulator/ui_smoke_runner.py --spec .codex/ui-smoke.yml`
5. 设备维护：`python3 scripts/simulator/simctl_boot.py --name "iPhone 16 Pro"`、`python3 scripts/simulator/simctl_shutdown.py --all`

### 真机模式
1. 查看设备：`xcrun devicectl list devices`
2. 构建/测试：`bash scripts/device/device_build_and_test.sh <repo-root>`
3. 安装启动：`bash scripts/device/device_install_and_launch.sh --app <path> --bundle-id <bundle_id>`
4. 诊断：`bash scripts/device/device_diagnose.sh --device <devicectl-device-id>`

## 脚本能力分组

### Simulator
- Build & Logs：`scripts/simulator/build_and_test.py`、`scripts/simulator/log_monitor.py`
- Navigation & Interaction：`scripts/simulator/screen_mapper.py`、`scripts/simulator/navigator.py`、`scripts/simulator/gesture.py`、`scripts/simulator/keyboard.py`、`scripts/simulator/app_launcher.py`
- Testing & Analysis：`scripts/simulator/accessibility_audit.py`、`scripts/simulator/visual_diff.py`、`scripts/simulator/test_recorder.py`、`scripts/simulator/app_state_capture.py`、`scripts/simulator/ui_smoke_runner.py`、`scripts/simulator/sim_health_check.sh`
- Advanced & Permissions：`scripts/simulator/clipboard.py`、`scripts/simulator/status_bar.py`、`scripts/simulator/push_notification.py`、`scripts/simulator/privacy_manager.py`、`scripts/simulator/sim_list.py`、`scripts/simulator/simulator_selector.py`
- Simulator Lifecycle：`scripts/simulator/simctl_boot.py`、`scripts/simulator/simctl_shutdown.py`、`scripts/simulator/simctl_create.py`、`scripts/simulator/simctl_delete.py`、`scripts/simulator/simctl_erase.py`

### 真机
- Build & Test：`scripts/device/device_build_and_test.sh`
- Install & Launch：`scripts/device/device_install_and_launch.sh`
- Diagnose：`scripts/device/device_diagnose.sh`

## 执行约定

- Simulator 默认优先结构化数据：`screen_mapper.py` + `navigator.py`，text-before-pixels
- 真机默认用 `xcodebuild -destination 'id=<destination-id>'`，不替代签名配置；签名交给 `xcode-build`
- 真机注意：`xcodebuild` destination id 与 `devicectl` device identifier 是不同的标识符，不能混用
- 本地执行 `xcodebuild` 默认在项目环境直接执行（CC 使用 `Bash` 工具；Codex 使用 `functions.exec_command` + `require_escalated`）
- 本地缓存统一复用 Xcode 系统 DerivedData（`~/Library/Developer/Xcode/DerivedData`）
- 如果未显式指定 scheme，默认优先选择绑定了单元测试 `*Tests` target/bundle 的 scheme
- 如果同一任务后续还要进入 `final-evidence-gate`，最终证据门禁默认复用本次定向测试的 workspace/scheme/destination 基线

## 参考资源

- `references/accessibility_checklist.md`
- `references/test_patterns.md`
- `references/simctl_quick.md`
- `references/idb_quick.md`
- `references/devicectl-quick.md`
- `references/device-troubleshooting.md`

## 最终证据门禁

- 只要当前任务产出修改了 Apple Xcode 项目相关内容，最终必须进入 `final-evidence-gate`；证据不足、高风险或命中工程/依赖/签名/资源打包类改动时，再切到 `verify-ios-build`
- 最终验证证据必须来自目标项目根目录的项目环境；沙箱内的构建结果不能作为最终验收结论
- 对 iOS 项目，若升级到 `verify-ios-build`，必须优先 `.xcworkspace`，并默认优先已连接真机
- 在 `final-evidence-gate` 接受现有证据或 `verify-ios-build` 成功前，不得把任务表述为"已完成"

## 与其他技能的关系

- 普通 iOS 业务实现：`ios-feature-implementation` / `swiftui-feature-implementation` / `uikit-feature-implementation`
- Build Settings、签名、Archive/Export、CI/CD：`xcode-build`
- 收尾一次性构建验收：`verify-ios-build`
- 补单元测试或 UI 测试代码：`testing`
- Crash/运行时根因排查：`debugging`

