---
name: macos-menubar-tuist-app
description: 使用 Tuist 与 SwiftUI 构建、重构或审查 macOS 菜单栏应用。仅适用于 `LSUIElement` 菜单栏工具与 Tuist manifest 驱动的工程；不要用于无 Xcode 工程的 SwiftPM 打包，后者应交给 `macos-spm-app-packaging`；若任务产出修改了 Apple Xcode 项目相关内容，收尾必须切到 `verify-ios-build` 并在项目环境完成最终验证。
---

# macOS 菜单栏 Tuist 应用

## 角色定位
- 专项型 skill。
- 负责 Tuist + SwiftUI + `LSUIElement` 菜单栏应用的工程组织、状态分层、脚本化启动与本地验证。
- 不负责无 Xcode 工程的 SwiftPM 打包链路，也不替代通用构建签名设计。

## 适用场景
- 创建或维护仅驻留在菜单栏中的 macOS 应用。
- 调整 `Project.swift`、运行脚本、依赖注入和 store/view 分层。
- 审查菜单栏应用的启动流程、状态边界和本地构建验证。

## 核心工作流
1. 确认 Tuist 归属
- 检查 `Tuist.swift`、`Project.swift` 或工作区 manifest 是否存在。
- 在修改运行流程之前，先阅读已有的 `run-menubar.sh` / `stop-menubar.sh`。

2. 明确菜单栏应用边界
- 除非用户明确要求，否则保持 `LSUIElement = true`。
- 模型、客户端、store 和视图职责分离，不在 SwiftUI `body` 中直接发起网络请求。
- 以 Tuist manifest 为唯一事实来源，不依赖手改生成产物。

3. 自下而上实现
- 先定义或调整模型。
- 再更新 client 请求与解码。
- 接着修改 store 的刷新、过滤和缓存策略。
- 最后接入菜单视图和行视图。

4. 统一本地启动体验
- `run-menubar.sh` 应在重启前关闭旧实例。
- 启动脚本不应隐式打开 Xcode。
- 需要重新生成工程时使用 `tuist generate --no-open`。

## 输出要求
- 默认文件职责分布如下：
  - `Project.swift`：target、构建设置、资源和 `Info.plist` 键。
  - `Sources/*Model*.swift`：API / domain model 与解码。
  - `Sources/*Client*.swift`：请求、响应映射和传输逻辑。
  - `Sources/*Store*.swift`：可观察状态、刷新策略、过滤与缓存。
  - `Sources/*Menu*View*.swift`：菜单结构和顶层 UI 状态。
  - `Sources/*Row*View*.swift`：行渲染与轻量交互。
  - `run-menubar.sh`：标准本地构建/重启/拉起入口。
  - `stop-menubar.sh`：显式停止辅助脚本。
- 修改后按触达范围执行校验：

```bash
TUIST_SKIP_UPDATE_CHECK=1 tuist build <TargetName> --configuration Debug
```

- 如果变更了启动流程，再运行：

```bash
./run-menubar.sh
```

## 强制收尾验证
- 只要当前任务产出修改了 Apple Xcode 项目相关内容（代码、测试、资源、工程文件、构建脚本、plist / entitlements / xcconfig / scheme 或项目内环境配置），最终必须切到 `verify-ios-build`。
- 最终门禁必须在目标项目根目录的项目环境执行；沙箱内的构建结果不能作为最终验收结论。
- 对 iOS 项目，`verify-ios-build` 必须优先 `.xcworkspace`（当 `.xcworkspace` 与 `.xcodeproj` 同时存在时），并默认优先已连接真机；找不到连接中的真机时再回退到 simulator。
- 对 macOS Xcode 工程，`verify-ios-build` 走宿主机 `xcodebuild build` 门禁；在成功前同样不得宣告任务已完成，必须明确写出“任务未完成”。

## 与其他技能的关系
- 如果目标是无 `.xcodeproj` 的 SwiftPM 打包、签名、公证和 appcast，切换到 `macos-spm-app-packaging`。
- 如果是通用 Archive、导出、签名和 CI 流程，而非 Tuist 菜单栏专项，切换到 `xcode-build`。
- 需要官方 API 依据时，可辅以 `apple-docs`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: macos-menubar-tuist-app`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
