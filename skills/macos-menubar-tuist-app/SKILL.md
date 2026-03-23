---
name: macos-menubar-tuist-app
description: 使用 Tuist 与 SwiftUI 构建、重构或审查 macOS 菜单栏应用。当任务涉及 `LSUIElement` 菜单栏工具、Tuist target/manifest、model-client-store-view 分层、脚本化启动流程，或需要在不依赖 Xcode 首选流程的前提下验证本地构建与运行时使用。
---

# macOS 菜单栏 Tuist 应用

## 适用场景
- 创建或维护仅驻留在菜单栏中的 macOS 应用。
- 为 Tuist 工程补齐或调整 `Project.swift`、运行脚本、依赖注入和状态分层。
- 需要审查菜单栏应用的架构边界、启动方式和本地验证流程。

## 核心规则
- 除非用户明确要求，否则保持菜单栏应用形态，默认使用 `LSUIElement = true`。
- 传输层、解码层和业务状态必须在视图之外；不要在 SwiftUI `body` 中直接发起网络请求。
- 状态变更集中在 store 层（`@Observable` 或等价实现），行视图只负责展示和轻量交互。
- 模型解码要能承受后端字段漂移：优先使用可选字段、默认值和防御式解析。
- 以 Tuist manifest 为唯一事实来源，不依赖手改的生成产物。
- 当 `tuist run` 对 macOS 目标不稳定时，优先使用脚本化启动流程。

## 工作流
1. 确认 Tuist 归属
- 检查 `Tuist.swift`、`Project.swift` 或工作区 manifest 是否存在。
- 在修改运行流程之前，先阅读已有的 `run-menubar.sh` / `stop-menubar.sh`。

2. 先探测后端行为，再写代码假设
- 使用 `curl` 确认接口形态、鉴权方式和分页行为。
- 如果后端忽略 `limit/page`，在 store 层处理全量拉取和本地裁剪。

3. 自下而上实现
- 先定义或调整模型。
- 再更新 client 请求与解码。
- 接着修改 store 的刷新、过滤和缓存策略。
- 最后接入菜单视图和行视图。

4. 保持应用入口最小化
- `App`、menu scene 和依赖注入只做装配，不承载业务逻辑。
- 视图只读取状态，不承担模型整理和传输细节。

5. 统一本地启动体验
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
  - `stop-menubar.sh`：显式停止辅助脚本（如果存在）。
- 修改后按触达范围执行校验：

```bash
TUIST_SKIP_UPDATE_CHECK=1 tuist build <TargetName> --configuration Debug
```

- 如果变更了启动流程，再运行：

```bash
./run-menubar.sh
```

- 如果变更了 shell 脚本，再运行：

```bash
bash -n run-menubar.sh
bash -n stop-menubar.sh
./run-menubar.sh
```

- 交付时报告实际执行过的命令和结果。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: macos-menubar-tuist-app`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
