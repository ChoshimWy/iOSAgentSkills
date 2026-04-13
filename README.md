# iOS Agent Skills 通用技能包

本项目为 Apple 平台开发相关的 Agent Skills 集合，适用于 Claude（`.claude/skills`）与 Codex（`.codex/skills`）AI 助手。`skills/` 下每个子目录为一个独立 skill，覆盖 iOS/macOS 开发、调试、测试、构建、自动化、设计与发布等常见场景。

## 目录结构

### Core Implementation
- `ios-feature-implementation/` —— 通用 iOS feature 业务实现、service / view model / 导航接线
- `swiftui-feature-implementation/` —— 在既定模式下落地普通 SwiftUI 页面与组件
- `uikit-feature-implementation/` —— 在既定架构下落地 UIKit 页面与组件
- `git-workflow/` —— Git 工作流与协作规范

### Specialized Implementation
- `swift-expert/` —— Swift 进阶能力（并发、协议导向、类型擦除、跨平台策略）
- `swiftui-ui-patterns/` —— 新建 SwiftUI 页面与模式选型
- `swiftui-view-refactor/` —— 既有 SwiftUI 大 view 结构化重构
- `swiftui-liquid-glass/` —— iOS 26+ Liquid Glass 专项实现
- `sdk-architecture/` —— SDK/Framework 架构设计
- `refactoring/` —— 通用代码重构与异味治理

### Automation / Build / Validation
- `ios-simulator-automation/` —— iOS Simulator 自动化、生命周期与语义交互
- `ios-device-automation/` —— 连接中的 iOS 真机构建、安装、启动、测试与诊断
- `testing/` —— 单元测试、UI 测试、Mock/Stub/Spy 与 async 测试
- `xcode-build/` —— Xcode 构建配置、签名、Archive/Export 与 CI/CD
- `verify-ios-build/` —— 收尾代码审查门禁 + 一次性 `xcodebuild` 验收

### Diagnostics
- `code-review/` —— 代码审查与 API 设计评审
- `debugging/` —— iOS 运行时调试与问题排查
- `ios-performance/` —— 性能分析、benchmark 与 `xctrace` / Instruments

### Research / Design / Release
- `apple-docs/` —— Apple 官方文档、API 与 WWDC 资料检索
- `ui-ux-design-system/` —— 视觉方向、设计系统与跨技术栈 UI/UX 设计
- `app-store-changelog/` —— App Store 更新文案生成
- `app-store-opportunity-research/` —— App Store 赛道与商业机会研究
- `gh-pr-flow/` —— GitHub CLI 一条龙提交流程

### Document / Productivity
- `office-pptx/` —— `.pptx` / PowerPoint 演示文稿读取、模板编辑、从零生成与 QA

### Platform / Legacy
- `macos-menubar-tuist-app/` —— Tuist + SwiftUI macOS 菜单栏应用
- `macos-spm-app-packaging/` —— 无 Xcode 工程的 macOS SwiftPM App 打包
- `swiftui-performance-audit/` —— 旧名兼容入口，新的性能任务统一使用 `ios-performance`

## 使用方法

1. **复制技能目录**
   - 对于 Claude，请将本目录复制到 `.claude/skills` 下。
   - 对于 Codex，请将本目录复制到 `.codex/skills` 下。
   - 对应 VS Code Copilot 会自动加载 `.claude/skills` 下的技能目录。
   - 或使用软连接方式将各 AI 工具对应的 skills 目录连接到本项目的 `skills` 目录，例如：
   ```bash
   ln -s iOSAgentSkills/skills .claude/skills
   ```

2. **Agent 自动加载**
   - Agent 会自动识别并加载该目录下的所有技能，无需额外配置。

3. **技能调用**
   - 在对话中描述需求，Agent 会根据意图自动调用合适的技能。
   - 例如：
     - “帮我 review 下面这段 Swift 代码”
     - “帮我设计一个新的 SwiftUI 设置页结构”
     - “帮我在连接中的 iPad 真机上跑一次 test”
     - “帮我配置 archive/export 的 xcodebuild 流程”
     - “帮我读取这个 .pptx 模板并改成新的 deck”

4. **技能扩展**
   - 新增技能：在本目录下新建子文件夹，包含 `SKILL.md` 及相关参考文档。
   - 参考现有技能目录结构与文档规范。
   - 所有新增 `SKILL.md` 末尾都必须包含 sentinel 规则。

## 通用约定
- 对应项目中新建 `.swift`、`.h`、`.m`、`.mm` 等源码文件且项目要求文件头时，`Created by` 必须使用**本机用户名称**，不能写 `Codex`。
- 当前环境下默认作者名取自本机用户信息：`Choshim.Wei`。
- 日期格式遵循项目约定；若无额外约定，默认使用 `YYYY/M/D`，例如：`Created by Choshim.Wei on 2026/4/11.`

## 适用场景
- iOS / macOS / Swift / SwiftUI / UIKit / Objective-C 开发
- Apple 官方文档与 WWDC 知识检索
- PowerPoint / `.pptx` 演示文稿读取、模板编辑与生成
- Swift 并发与协议导向进阶设计
- SDK / 组件开发与架构设计
- 代码审查、重构、调试与性能分析
- 模拟器 / 真机自动化、构建验收与 CI/CD
- 设计系统、发布文案与 App Store 机会研究

## 贡献
欢迎补充更多 Apple 平台相关技能，完善文档与案例。

---

如需详细用法与示例，请查阅各技能子目录下的 `SKILL.md` 文件。
