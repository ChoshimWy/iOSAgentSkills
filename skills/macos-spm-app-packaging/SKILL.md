---
name: macos-spm-app-packaging
description: 在不依赖 Xcode 工程的前提下，为基于 SwiftPM 的 macOS 应用搭建脚手架、构建并打包。仅适用于无 `.xcodeproj` 的 SwiftPM 应用与脚本化签名、公证、appcast；不要用于 Tuist 菜单栏应用，后者应交给 `macos-menubar-tuist-app`。
---

# macOS SwiftPM 应用打包（无 Xcode 工程）

## 角色定位
- 专项型 skill。
- 负责无 Xcode 工程的 SwiftPM macOS 应用脚手架、`.app` 组装、签名、公证和发布辅助脚本。
- 不负责 Tuist 菜单栏工程维护，也不替代一般 iOS/macOS 业务开发。

## 适用场景
- 从零搭建不依赖 `.xcodeproj` 的 macOS 应用。
- 需要使用 SwiftPM、脚本和模板完成 `.app` 打包。
- 需要补齐签名、公证、Sparkle appcast 或 GitHub Release 发布流程。

## 核心工作流
1. 初始化项目骨架
- 复制 `assets/templates/bootstrap/` 到新仓库。
- 在 `Package.swift`、`Sources/MyApp/` 和 `version.env` 中把 `MyApp` 改成真实应用名。
- 显式填写 `APP_NAME`、`BUNDLE_ID`、`MARKETING_VERSION`、`BUILD_NUMBER`。

2. 复制并使用脚本
- 复用 `assets/templates/` 中的现成脚本，不要重新发明脚手架。
- 至少准备 `package_app.sh` 与 `compile_and_run.sh`。
- 运行 `chmod +x Scripts/*.sh`。

3. 构建、打包、发布
- 使用 `swift build` / `swift test` 做基础验证。
- 使用 `Scripts/package_app.sh` 生成 `.app`。
- 需要签名、公证、Sparkle 或 GitHub Release 时，再按需启用对应脚本。

## 参考资源
- `references/scaffold.md`：从零搭建 SwiftPM macOS app 的最小结构。
- `references/packaging.md`：打包输出路径与关键环境变量。
- `references/release.md`：签名、公证、Sparkle 和 GitHub Release 说明。
- `assets/templates/bootstrap/`：最小骨架模板。
- `assets/templates/package_app.sh`：打包 `.app`。
- `assets/templates/compile_and_run.sh`：本地构建并运行。
- `assets/templates/launch.sh`：直接启动已打包应用。
- `assets/templates/sign-and-notarize.sh`：签名、公证与 zip。
- `assets/templates/make_appcast.sh`：生成 Sparkle appcast。

## 输出要求
- 最短可运行路径如下：

```bash
cp -R assets/templates/bootstrap/ ~/Projects/MyApp
cd ~/Projects/MyApp
sed -i '' 's/MyApp/HelloApp/g' Package.swift version.env
cp assets/templates/package_app.sh Scripts/
cp assets/templates/compile_and_run.sh Scripts/
chmod +x Scripts/*.sh
swift build
Scripts/compile_and_run.sh
```

- 打包后至少检查：

```bash
ls -R build/HelloApp.app/Contents
file build/HelloApp.app/Contents/MacOS/HelloApp
```

- 如果涉及签名、公证或 `Sparkle`，必须显式说明哪些脚本和环境变量被启用。

## 与其他技能的关系
- 如果项目使用 Tuist，且目标是 `LSUIElement` 菜单栏应用，切换到 `macos-menubar-tuist-app`。
- 如果任务重点是通用签名、Archive、导出或 CI，而非无 Xcode 的 SwiftPM 打包，切换到 `xcode-build`。
- 如果需要官方平台约束或 API 依据，可辅以 `apple-docs`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: macos-spm-app-packaging`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
