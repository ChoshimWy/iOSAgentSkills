---
name: macos-spm-app-packaging
description: 在不依赖 Xcode 工程的前提下，为基于 SwiftPM 的 macOS 应用搭建脚手架、构建并打包。当任务涉及从零创建 macOS app 目录、SwiftPM target/resources、自定义 `.app` 组装脚本，或在 Xcode 之外处理签名、公证、appcast 时使用。
---

# macOS SwiftPM 应用打包（无 Xcode 工程）

## 适用场景
- 需要从零搭建不依赖 `.xcodeproj` 的 macOS 应用。
- 需要使用 SwiftPM、脚本和模板完成 `.app` 打包。
- 需要补齐签名、公证、Sparkle appcast 或 GitHub Release 发布流程。

## 核心规则
- 先复用 `assets/templates/` 和 `assets/templates/bootstrap/`，不要重新发明脚手架。
- 保持签名、公证、版本号和环境变量显式配置。
- 脚本负责打包与发布流程，`Package.swift` 负责编译目标与资源声明。
- 只有在确实使用 Sparkle 时才保留 appcast 相关步骤。

## 工作流
1. 初始化项目骨架
- 复制 `assets/templates/bootstrap/` 到新仓库。
- 在 `Package.swift`、`Sources/MyApp/` 和 `version.env` 中把 `MyApp` 改成真实应用名。
- 填写 `APP_NAME`、`BUNDLE_ID`、`MARKETING_VERSION`、`BUILD_NUMBER`。

2. 复制脚本并赋权
- 把 `assets/templates/` 中需要的脚本拷贝到项目，例如 `Scripts/`。
- 至少准备 `package_app.sh` 与 `compile_and_run.sh`。
- 运行 `chmod +x Scripts/*.sh`。

3. 构建、打包、运行
- 使用 `swift build` / `swift test` 做基础验证。
- 使用 `Scripts/package_app.sh` 生成 `.app`。
- 本地调试优先使用 `Scripts/compile_and_run.sh`，必要时使用 `Scripts/launch.sh`。

4. 发布（按需）
- 签名与公证使用 `Scripts/sign-and-notarize.sh`。
- 需要 Sparkle 时使用 `Scripts/make_appcast.sh`。
- 需要 GitHub Release 时创建 tag 并上传 zip / `appcast.xml`。

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
- `assets/templates/setup_dev_signing.sh`：配置开发签名。
- `assets/templates/build_icon.sh`：从 Icon Composer 生成 `.icns`。

## 输出要求
- 最短可运行路径如下：

```bash
#1. 复制并重命名骨架
cp -R assets/templates/bootstrap/ ~/Projects/MyApp
cd ~/Projects/MyApp
sed -i '' 's/MyApp/HelloApp/g' Package.swift version.env

#2. 复制脚本
cp assets/templates/package_app.sh Scripts/
cp assets/templates/compile_and_run.sh Scripts/
chmod +x Scripts/*.sh

#3. 构建并启动
swift build
Scripts/compile_and_run.sh
```

- 打包后至少检查：

```bash
ls -R build/HelloApp.app/Contents
file build/HelloApp.app/Contents/MacOS/HelloApp
```

- 签名后至少检查：

```bash
codesign -dv --verbose=4 build/HelloApp.app
spctl --assess --type execute --verbose build/HelloApp.app
```

- 公证并 stapling 后至少检查：

```bash
stapler validate build/HelloApp.app
spctl --assess --type execute --verbose build/HelloApp.app
```

- 常见公证故障处理：

| 现象 | 常见原因 | 处理方式 |
| --- | --- | --- |
| `The software asset has already been uploaded` | 同版本重复提交 | 提升 `version.env` 中的 `BUILD_NUMBER` 后重新打包。 |
| `Package Invalid: Invalid Code Signing Entitlements` | `.entitlements` 与签名配置不匹配 | 对照 Apple 允许项审查 entitlement，移除不支持的键。 |
| `The executable does not have the hardened runtime enabled` | `codesign` 缺少 `--options runtime` | 在 `sign-and-notarize.sh` 的所有 `codesign` 调用中补齐该参数。 |
| 公证卡住或没有状态邮件 | `xcrun notarytool` 网络或凭证异常 | 运行 `xcrun notarytool history` 检查状态，并重新导出失效的 App Store Connect 凭证。 |
| `stapler validate` 失败 | ticket 尚未传播完成 | 等待约 60 秒后重试 `xcrun stapler staple`。 |

- 额外规则：
  - `Sparkle` 依赖 `CFBundleVersion`，每次发布都必须递增 `BUILD_NUMBER`。
  - 菜单栏应用打包时设置 `MENU_BAR_APP=1`，让 `Info.plist` 输出 `LSUIElement`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: macos-spm-app-packaging`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
