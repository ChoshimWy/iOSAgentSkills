---
name: ios-automation
description: iOS 设备自动化 Skill，覆盖 Simulator 与真机两种目标，用于设备发现、模拟器生命周期、安装启动、语义导航、accessibility tree、UI smoke、截图取证与常见设备诊断；不要把 Build Settings、签名、Archive/Export、普通业务实现、测试编写或一次性构建验收误判到本 Skill。
---

# iOS 设备自动化

## Purpose

Automate iOS Simulator and physical-device workflows for install, launch, navigation, accessibility checks, UI smoke, screenshots, device diagnostics, and lifecycle management without replacing build configuration, testing, or final build verification Skills.

## 中文说明

该 Skill 是 iOS 设备自动化统一入口，覆盖两类模式：

- Simulator 模式：模拟器生命周期、安装启动、语义导航、accessibility tree、UI smoke、截图和视觉取证。
- 真机模式：设备发现、build/test 设备选择、安装启动、进程查询和常见真机诊断。

该 Skill 不负责 Build Settings、签名策略、Archive/Export、普通业务实现、测试代码编写或一次性完整构建验收。

## When to Use

Use this Skill when the task needs:

- Simulator boot / shutdown / create / erase / delete。
- App install / launch / terminate on Simulator or device。
- UI navigation by text / accessibility。
- Accessibility tree inspection。
- UI smoke execution。
- Screenshot or visual evidence capture。
- Device discovery and connected-device diagnosis。
- Simulator status bar, clipboard, privacy permission, push notification setup。
- Real-device install / launch / diagnose workflow。

## When Not to Use

Do not use this Skill when:

- The task is Build Settings, signing, certificates, Archive, Export, or CI/CD; use `xcode-build`.
- The task is one-off project-environment build verification; use `verify-ios-build`.
- The task is test writing or affected unit test selection; use `testing` / `ios-affected-tests`.
- The task is normal feature implementation; use implementation Skills.
- The task is crash or runtime root-cause analysis; use `debugging`.
- The task is performance profiling, benchmark, `xctrace`, or Instruments; use `ios-performance`.

## Agent Rules

### Device Mode Rules

- First classify target mode: `simulator` or `device`.
- Once a mode is selected, keep the chain in that mode unless the user asks to switch or the current mode is blocked.
- Do not mix Simulator UDID, `xcodebuild` destination id, and `devicectl` device identifier.
- If the problem narrows to signing/certificates/Archive/CI, route to `xcode-build`.
- If the problem narrows to build verification, route to `verify-ios-build`.

### Simulator Rules

- Prefer structured UI data over pixels: `screen_mapper.py` + `navigator.py`.
- Use text-before-pixels.
- Use screenshots as evidence, not as the only state assertion.
- Prefer accessibility tree and text assertions for UI smoke.
- Explicit `--udid` should override auto-selection.
- Without `--udid`, prefer an already booted Simulator when appropriate.

### Physical Device Rules

- For build/test destination selection, prefer `xcodebuild -showdestinations` real iOS destinations.
- For install/launch/diagnose, prefer `xcrun devicectl list devices` connected devices.
- `connected` devices are preferred over `available (paired)`.
- `unavailable` devices are diagnostic targets only, not default run targets.
- Do not treat paired but disconnected devices as connected devices.
- `xcodebuild` destination id and `devicectl` device identifier are different and must not be mixed.

### Build/Test Rules

- This Skill may call scripts that trigger build/test only as part of device automation.
- Validation-type `xcodebuild` invoked by automation scripts should use the project wrapper / shared build-queue daemon.
- If no scheme is explicit, prefer schemes bound to unit test targets / bundles such as `*Tests`.
- Do not use this Skill as the default final validation step for all code changes.
- If final evidence is required, route through `final-evidence-gate` / `verify-ios-build`.

### Evidence Rules

- Capture structured state when possible.
- Report device/simulator identifier, OS/runtime, bundle id, and command path.
- Record evidence path for screenshots, accessibility dumps, app state, or logs.
- Do not paste huge logs.
- Do not claim UI state from screenshots alone if accessibility/text state contradicts it.

### Token Budget

- Prefer structured summaries from scripts.
- Do not paste full simulator logs.
- Do not paste full device logs.
- Do not dump full accessibility tree unless requested.
- Include only relevant nodes or failure excerpts.
- For build/test failure logs, use `ios-build-log-digest`.

## Device Selection Strategy

### Simulator

1. Use explicit `--udid` when provided.
2. Otherwise resolve current booted Simulator.
3. If none is booted and a device name is provided, boot that device.
4. If no device is specified, choose the project/default simulator policy.

### Physical Device

1. For build/test: prefer first real iOS destination from `xcodebuild -showdestinations` that is usable.
2. For install/launch/diagnose: prefer `connected` device from `xcrun devicectl list devices`.
3. Then match user-provided device name or identifier.
4. Use `available (paired)` only when explicitly acceptable.
5. Use `unavailable` only for diagnosis.

## Core Workflow

1. Classify target mode: simulator or physical device.
2. Resolve target identifier and verify availability.
3. Identify app bundle id, app path, workspace/scheme if needed.
4. Run the narrowest automation task: install, launch, navigate, inspect, screenshot, diagnose, or UI smoke.
5. Capture structured evidence.
6. Report result and next action.
7. If the issue is build/signing/configuration, route to the correct Skill.

## Simulator Workflow

1. Health check: `bash scripts/simulator/sim_health_check.sh`.
2. Boot / shutdown / lifecycle:
   - `python3 scripts/simulator/simctl_boot.py --name "iPhone 16 Pro"`
   - `python3 scripts/simulator/simctl_shutdown.py --all`
3. Launch and state:
   - `python3 scripts/simulator/app_launcher.py --launch <bundle_id>`
   - `python3 scripts/simulator/screen_mapper.py`
4. Semantic interaction:
   - `python3 scripts/simulator/navigator.py --find-text "Login" --tap`
5. Validation and diagnostics:
   - `python3 scripts/simulator/accessibility_audit.py`
   - `python3 scripts/simulator/app_state_capture.py --app-bundle-id <bundle_id>`
   - `python3 scripts/simulator/ui_smoke_runner.py --spec .codex/ui-smoke.yml`

## Physical Device Workflow

1. List devices: `xcrun devicectl list devices`.
2. Build/test if needed: `bash scripts/device/device_build_and_test.sh <repo-root>`.
3. Install/launch:
   - `bash scripts/device/device_install_and_launch.sh --app <path> --bundle-id <bundle_id>`
4. Diagnose:
   - `bash scripts/device/device_diagnose.sh --device <devicectl-device-id>`

## Script Groups

### Simulator

- Build & Logs: `scripts/simulator/build_and_test.py`, `scripts/simulator/log_monitor.py`
- Navigation & Interaction: `scripts/simulator/screen_mapper.py`, `scripts/simulator/navigator.py`, `scripts/simulator/gesture.py`, `scripts/simulator/keyboard.py`, `scripts/simulator/app_launcher.py`
- Testing & Analysis: `scripts/simulator/accessibility_audit.py`, `scripts/simulator/visual_diff.py`, `scripts/simulator/test_recorder.py`, `scripts/simulator/app_state_capture.py`, `scripts/simulator/ui_smoke_runner.py`, `scripts/simulator/sim_health_check.sh`
- Advanced & Permissions: `scripts/simulator/clipboard.py`, `scripts/simulator/status_bar.py`, `scripts/simulator/push_notification.py`, `scripts/simulator/privacy_manager.py`, `scripts/simulator/sim_list.py`, `scripts/simulator/simulator_selector.py`
- Simulator Lifecycle: `scripts/simulator/simctl_boot.py`, `scripts/simulator/simctl_shutdown.py`, `scripts/simulator/simctl_create.py`, `scripts/simulator/simctl_delete.py`, `scripts/simulator/simctl_erase.py`

### Physical Device

- Build & Test: `scripts/device/device_build_and_test.sh`
- Install & Launch: `scripts/device/device_install_and_launch.sh`
- Diagnose: `scripts/device/device_diagnose.sh`

## Inputs

Expected input contract:

```json
{
  "mode": "simulator | device | auto",
  "task": "boot | install | launch | navigate | inspect | screenshot | ui-smoke | diagnose | shutdown",
  "bundle_id": "com.example.app",
  "app_path": "optional",
  "udid": "optional-simulator-udid",
  "device_identifier": "optional-devicectl-id",
  "xcode_destination_id": "optional-xcodebuild-destination-id",
  "workspace": "optional",
  "scheme": "optional",
  "ui_smoke_spec": ".codex/ui-smoke.yml",
  "constraints": []
}
```

## Outputs

Return compact structured output:

```json
{
  "status": "passed | failed | skipped | blocked",
  "mode": "simulator | device",
  "task": "launch | navigate | ui-smoke | diagnose",
  "target": {
    "name": "iPhone 16 Pro",
    "udid": "...",
    "device_identifier": "...",
    "xcode_destination_id": "...",
    "runtime": "iOS 18.x"
  },
  "bundle_id": "com.example.app",
  "executed_commands": [],
  "evidence": {
    "accessibility_tree": "path-or-summary",
    "screenshot": "path",
    "app_state": "path-or-summary",
    "logs": "path-or-summary"
  },
  "first_failure": null,
  "next_action": "none | retry | route-xcode-build | route-verify-ios-build | route-debugging | blocked"
}
```

## Exit Conditions

Return `passed` when:

- The requested automation task completed.
- Target device/simulator identity is recorded.
- Evidence or structured state is captured when relevant.

Return `failed` when:

- The task executed but app launch, navigation, UI smoke, install, or diagnosis failed.
- First failure is captured with enough context.

Return `blocked` when:

- Required device/simulator is unavailable.
- App path or bundle id is missing.
- Signing/install permission prevents progress.
- Required simulator runtime is missing.
- Tooling such as `simctl` or `devicectl` is unavailable.

Return `skipped` when:

- Automation is not needed for the current risk level.
- A higher-level Skill decides targeted tests + review are sufficient.

## Escalation Rules

Escalate to `xcode-build` when:

- Signing, certificates, profiles, Build Settings, Archive, Export, or CI configuration blocks automation.

Escalate to `verify-ios-build` when:

- The user asks for final build verification.
- The issue is project-environment build evidence, not device automation.

Escalate to `testing` when:

- The task is writing XCTest/XCUITest code or selecting affected tests.

Escalate to `debugging` when:

- The app launches but crashes, hangs, leaks, or shows runtime symptoms.

Escalate to `ios-performance` when:

- The task becomes startup performance, frame rate, CPU/memory/energy profiling, `xctrace`, or Instruments.

Escalate to `ios-build-log-digest` when:

- Automation-triggered build/test logs need compact failure attribution.

## Reporting Format

```text
Automation status: passed | failed | skipped | blocked
Mode: simulator | device
Task: launch | navigate | inspect | ui-smoke | diagnose
Target: <name / udid / device id>
Bundle ID: <bundle id>
Evidence:
- accessibility: <path or summary>
- screenshot: <path or none>
- app_state: <path or summary>
First failure: none | ...
Next action: none | route-xcode-build | route-debugging | blocked
```

## Optional Evidence Verification

- `ios-automation` is not the default final validation step for all code changes.
- Default closure remains targeted testing / necessary validation plus independent reviewer subAgent `code-review`.
- Use automation only when user asks, UI/device evidence is needed, or the main Agent decides device-level evidence is required.
- If full project-environment build evidence is needed, use `final-evidence-gate` / `verify-ios-build`.
- Any optional full verification evidence must come from target project root, not sandbox-only results.

## Reference Resources

- `references/accessibility_checklist.md`
- `references/test_patterns.md`
- `references/simctl_quick.md`
- `references/idb_quick.md`
- `references/devicectl-quick.md`
- `references/device-troubleshooting.md`

## Relationship to Other Skills

- Business, SwiftUI, UIKit, mixed UI, advanced Swift, and refactor implementation: `ios-feature-implementation` with the matching internal mode.
- Build Settings, signing, Archive/Export, CI/CD: `xcode-build`.
- Final build verification: `verify-ios-build`.
- Test writing and affected tests: `testing`, `ios-affected-tests`.
- Runtime root-cause analysis: `debugging`.
- Performance profiling: `ios-performance`.
- Build/test log attribution: `ios-build-log-digest`.
