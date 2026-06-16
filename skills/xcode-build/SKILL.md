---
name: xcode-build
description: Xcode 构建配置与交付链路 Skill。用于 Build Settings、scheme、xcconfig、构建脚本、签名、证书、Archive、Export、CI/CD、XCFramework 与构建性能策略；不要把一次性 xcodebuild 验证、Simulator/真机执行路径、测试编写、代码审查或运行时排障误判到本 Skill。
---

# Xcode 构建与配置

## Purpose

Design, modify, or review Xcode build configuration, signing, archive/export, CI/CD, and distribution workflows while keeping one-off build verification delegated to verification-specific Skills.

## 中文说明

该 Skill 是 Xcode 构建配置与交付链路专项 Skill。

负责：
- Build Settings。
- scheme / configuration / xcconfig。
- 构建脚本。
- Signing、证书、Provisioning Profile、entitlements。
- Archive / Export / IPA 导出。
- CI/CD 中的 `xcodebuild` 流程。
- XCFramework 打包与分发策略。
- 构建性能优化策略。

不负责：
- 任务末尾一次性 `xcodebuild` 验证。
- 真机 / Simulator 自动化执行路径。
- 测试代码编写。
- 静态代码审查。
- 运行时 crash / 泄漏 / 卡顿排障。

## When to Use

Use this Skill when the user asks about:

- `Build Settings`。
- scheme、target、configuration。
- `.xcconfig` 管理。
- build phases / run scripts。
- code signing、certificates、profiles、entitlements、capabilities。
- Archive / Export / IPA。
- CI/CD build pipeline。
- `xcodebuild archive` / `-exportArchive` 策略。
- XCFramework 构建或分发。
- 构建性能优化。
- workspace / project / scheme 选择策略。

## When Not to Use

Do not use this Skill when:

- 用户只是要求“最后编译验证一下”或“跑一次 xcodebuild”；使用 `verify-ios-build`。
- 用户主要在问在哪个 Simulator / 真机上安装、启动、截图、导航；使用 `ios-automation`。
- 用户需要编写或执行最窄测试；使用 `testing`。
- 用户需要代码质量审查；使用 `code-review`。
- 用户需要分析 crash、泄漏、卡顿；使用 `debugging` / `ios-performance`。
- 用户需要判断现有验证证据是否足够；使用 `final-evidence-gate`。

## Agent Rules

### Boundary Rules

- Treat this Skill as build configuration / delivery design, not default final verification.
- Do not run validation-type `xcodebuild` as the main purpose of this Skill.
- If actual project-environment verification is required, hand off to `verify-ios-build`.
- If device / simulator automation is required, hand off to `ios-automation`.
- If a build error log must be analyzed, prefer `ios-build-log-digest` first.

### Build Configuration Rules

- Identify build entry first: `.xcworkspace` / `.xcodeproj` / target / scheme.
- For iOS projects with both `.xcworkspace` and `.xcodeproj`, prefer `.xcworkspace`.
- Identify the goal: local build, test pipeline, archive, export, signing, CI, XCFramework, or build performance.
- Separate configuration design from verification execution.
- Prefer explicit configuration over hidden environment assumptions.
- Keep project changes minimal and scoped to the build issue.

### Signing Rules

When handling signing, always clarify:

- Bundle identifier.
- Team ID.
- Signing style: automatic or manual.
- Certificate type.
- Provisioning profile type.
- Entitlements and capabilities.
- Debug vs Release differences.
- Local vs CI signing environment.

Do not claim signing is fixed unless the evidence confirms it.

### Archive / Export Rules

For Archive / Export work, specify:

- Archive action.
- Export method.
- Export options plist.
- Signing style.
- Destination path.
- App Store / Ad Hoc / Enterprise / Development intent.
- CI artifact output expectations.

### Private Dependency Rules

- If build configuration involves private Pods or local components, inspect `Podfile`, `Podfile.lock`, and `Pods/Manifest.lock`.
- If a local `:path` Pod is active, modify the real component repository, not `Pods/<LibraryName>`.
- For private library / component changes, keep or switch the main project to local `:path` dependency for development and validation unless the user explicitly asks to restore versioned dependency.
- Do not commit local `:path` dependency references unless explicitly requested.

### DerivedData Rules

- Default local builds should use Xcode system DerivedData: `~/Library/Developer/Xcode/DerivedData`.
- Do not introduce temporary public `-derivedDataPath` strategies as default.
- Do not reintroduce old public `XCODE_DERIVED_DATA_*` or `CODEX_DERIVED_DATA_SLOT` configuration.
- For validation-type builds, delegate to wrapper / build-queue policy through `verify-ios-build`.

### File Header Rules

When adding `.swift`, `.h`, `.m`, `.mm` files and headers are required:

- `Created by` must use local `whoami`.
- Do not use `Codex` as creator.
- Date format: `YYYY/M/D`.

### Token Budget

- Do not paste full build logs.
- Do not dump full `.xcresult` JSON.
- Do not scan DerivedData recursively.
- Prefer targeted build setting snippets.
- Prefer `diagnostics.json` and `build-summary.txt` for error context.
- Summarize only actionable configuration deltas.

## Core Workflow

1. Identify target project entry: workspace / project / scheme / target.
2. Identify task goal: build config, signing, archive, export, CI, XCFramework, or performance strategy.
3. Inspect only relevant files: project settings, xcconfig, scheme, plist, entitlements, Podfile, CI config, export options.
4. Define the desired configuration state.
5. Propose or apply minimal scoped changes.
6. Document CI/local impact.
7. If evidence is required, hand off to `final-evidence-gate` or `verify-ios-build` rather than running ad-hoc verification inside this Skill.
8. Report residual risk and next action.

## Inputs

Expected input contract:

```json
{
  "goal": "configure signing | archive | export | ci | build settings | xcframework",
  "workspace": "App.xcworkspace",
  "project": null,
  "scheme": "App",
  "target": "App",
  "configuration": "Debug | Release",
  "destination": "optional",
  "ci_provider": "Jenkins | GitHub Actions | local | other",
  "signing": {
    "team_id": "optional",
    "bundle_id": "optional",
    "style": "automatic | manual | unknown",
    "export_method": "app-store | ad-hoc | enterprise | development | unknown"
  },
  "changed_files": [],
  "constraints": []
}
```

## Outputs

Return compact structured output:

```json
{
  "status": "completed | proposed | blocked | partial",
  "build_entry": {
    "workspace": "App.xcworkspace",
    "project": null,
    "scheme": "App",
    "target": "App",
    "configuration": "Release"
  },
  "build_strategy": "...",
  "signing_strategy": "...",
  "archive_strategy": "...",
  "export_strategy": "...",
  "ci_changes": [],
  "changed_files": [],
  "validation_handoff": "none | final-evidence-gate | verify-ios-build",
  "known_risks": [],
  "next_action": "none | review | verify | provide_signing_assets | blocked"
}
```

## Exit Conditions

Return `completed` when:

- Build/signing/archive/CI configuration change or design is complete.
- Changed files are listed.
- Local and CI impact is described.
- Verification handoff is clear.

Return `proposed` when:

- The user requested a strategy/design only and no repository change was made.

Return `partial` when:

- Some configuration was completed but final signing credentials, CI secrets, or device/team access are missing.

Return `blocked` when:

- Required signing assets, team access, project files, CI credentials, or dependency access are unavailable.
- The repository is not an Xcode project.
- Required decision between signing/export/CI paths is missing.

## Escalation Rules

Escalate to `verify-ios-build` when:

- The user explicitly asks to run real project-environment build verification.
- Build configuration changes need actual final evidence.
- `final-evidence-gate` decides evidence is insufficient.

Escalate to `final-evidence-gate` when:

- There is a question whether current testing/review/build evidence is enough.

Escalate to `ios-automation` when:

- The task becomes install, launch, simulator lifecycle, real-device workflow, screenshot, or accessibility verification.

Escalate to `testing` when:

- The task becomes test writing or affected test selection.

Escalate to `code-review` when:

- Configuration changes need static review and risk assessment.

Escalate to `ios-build-log-digest` when:

- A raw build log needs compact failure attribution.

Escalate to `ios-feature-implementation` with `sdk-contract` mode when:

- The task is SDK distribution boundary, module design, package layout, or XCFramework product strategy.

## Reporting Format

```text
Build entry:
- Workspace/Project:
- Scheme:
- Target:
- Configuration:

Build strategy:
- ...

Signing strategy:
- ...

Archive/export strategy:
- ...

CI impact:
- ...

Validation handoff:
- none | final-evidence-gate | verify-ios-build

Known risks:
- ...

Next action:
- ...
```

## Reference Resources

- `references/build-settings.md`
- `references/ci-templates.md`

## Relationship to Other Skills

- Use this Skill for Build Settings, signing, Archive/Export, CI/CD, XCFramework, and build scripts.
- Use `verify-ios-build` for one-off project-environment build verification.
- Use `ios-automation` for simulator/device execution and app lifecycle automation.
- Use `testing` for unit/UI test writing and targeted test scope.
- Use `code-review` for static review of configuration changes.
- Use `ios-build-log-digest` for compact build failure attribution.
- Use `ios-feature-implementation` with `sdk-contract` mode for SDK distribution and module boundary strategy; keep concrete build/signing/archive mechanics in this Skill.
