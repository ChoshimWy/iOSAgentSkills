# iOS Agent Skills 通用技能包

本项目为 Apple 平台开发相关的 Agent Skills 集合，适用于 Claude（`.claude/skills`）与 Codex（`.codex/skills`）AI 助手。`skills/` 下每个子目录为一个独立 skill，覆盖 iOS/macOS 开发、调试、测试、构建、自动化、设计与发布等常见场景。

## 目录结构

### Shared Config
- `AGENTS.md` —— 团队共享规则与长期稳定偏好单一来源
- `config/codex.shared.toml` —— 可版本化、可跨设备复用的 Codex 共享默认配置
- `CLAUDE.md` —— Claude 入口薄包装，导入 `AGENTS.md`

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
- `office-docx/` —— `.docx` / Word 文档读取、模板编辑、从零生成、批注修订与 QA
- `office-pptx/` —— `.pptx` / PowerPoint 演示文稿读取、模板编辑、从零生成与 QA

### Platform / Legacy
- `macos-menubar-tuist-app/` —— Tuist + SwiftUI macOS 菜单栏应用
- `macos-spm-app-packaging/` —— 无 Xcode 工程的 macOS SwiftPM App 打包
- `swiftui-performance-audit/` —— 旧名兼容入口，新的性能任务统一使用 `ios-performance`

## 使用方法

1. **推荐：一键接入本地 Agent 配置**
   - 任意设备 clone 仓库后，优先执行：
   ```bash
   bash install-local-agent-config.sh
   ```
   - 脚本会自动使用**当前 clone 的仓库路径**生成本地入口，不依赖固定仓库位置，也不需要你手工改路径。
   - 脚本会默认同时配置 Codex 与 Claude：
     - `~/.codex/AGENTS.md`
     - `~/.codex/skills`
     - `~/.claude/CLAUDE.md`
     - `~/.claude/skills`
   - 同时会自动同步 `config/codex.shared.toml` 到 `~/.codex/config.toml`：
     - `model_instructions_file` 指向 `~/.codex/AGENTS.md`
     - 写入仓库托管的共享默认项，例如 model / reasoning / features / memories / MCP / plugins / tui
     - 保留本机未托管配置，例如项目 trust、认证、历史、缓存、memory 文件与额外本地自定义项
   - 如果本地已有冲突文件、目录或错误链接，脚本会先备份到：
     - `~/.agent-skills-backups/iOSAgentSkills/<timestamp>/`
   - 如需先查看将要发生的变更，可执行：
   ```bash
   bash install-local-agent-config.sh --dry-run
   ```
   - 正式执行后，脚本会立即做一轮安装后自检；只有输出 `Verification: OK` 才表示当前设备已经可以直接使用这套配置。

2. **手工方式（备选）**
   - 对于 Claude，请将本目录复制到 `.claude/skills` 下。
   - 对于 Codex，请将本目录复制到 `.codex/skills` 下。
   - 对应 VS Code Copilot 会自动加载 `.claude/skills` 下的技能目录。
   - 或使用软连接方式将各 AI 工具对应的 skills 目录连接到本项目的 `skills` 目录，例如：
   ```bash
   ln -s iOSAgentSkills/skills .claude/skills
   ```

3. **Agent 自动加载**
   - Agent 会自动识别并加载该目录下的所有技能，无需额外配置。

4. **技能调用**
   - 在对话中描述需求，Agent 会根据意图自动调用合适的技能。
   - 例如：
     - “帮我 review 下面这段 Swift 代码”
     - “帮我设计一个新的 SwiftUI 设置页结构”
     - “帮我在连接中的 iPad 真机上跑一次 test”
     - “帮我配置 archive/export 的 xcodebuild 流程”
     - “帮我把这份合同模板改成新的 .docx”
     - “帮我读取这个 .pptx 模板并改成新的 deck”

5. **技能扩展**
   - 新增技能：在本目录下新建子文件夹，包含 `SKILL.md` 及相关参考文档。
   - 参考现有技能目录结构与文档规范。
   - 所有新增 `SKILL.md` 末尾都必须包含 sentinel 规则。

## 规则主文件架构

- 本仓库以根目录 `AGENTS.md` 作为**单一规则源**。
- `AGENTS.md` 同时承载团队共享规则与当前默认行为约定；以后修改规则时，只编辑这一份文件。
- 其中“默认回复语言”和“长期稳定偏好”属于适合跨 session 复用的稳定约定；按 OpenAI 官方建议，必须长期生效的要求继续放在 `AGENTS.md`，memory 只作为辅助 recall。
- Codex 的**可共享默认配置**统一维护在 `config/codex.shared.toml`；它只放适合跨设备同步的内容，不放本机状态。
- Codex 全局入口建议保持为 `~/.codex/AGENTS.md`，并通过本地软连接指向本仓库的 `AGENTS.md`，这样无需改动既有 `config.toml` 入口。
- Claude 项目入口使用仓库根目录 `CLAUDE.md`，其内容仅导入 `@AGENTS.md`，避免两份正文漂移。
- Claude 全局入口使用 `~/.claude/CLAUDE.md`，并通过绝对路径导入本仓库 `AGENTS.md`，从而让全局会话也继承同一份规则。
- 维护原则：
  - 不要分别手改 `~/.codex/AGENTS.md` 与 `~/.claude/CLAUDE.md` 的正文；
  - `CLAUDE.md` 只做薄包装导入；
  - 规则正文统一维护在仓库 `AGENTS.md`。
  - Codex 共享默认项统一改 `config/codex.shared.toml`，然后重新运行 `bash install-local-agent-config.sh` 同步到本机。
  - 任意设备 clone 后优先运行 `bash install-local-agent-config.sh`，不要手工重复拼装本地入口。
  - 脚本会把本地入口绑定到**当前 clone 的仓库路径**，因此换目录重新 clone 后，应从新的仓库目录再执行一次脚本。

## Codex 共享配置边界

- **应放 Git 的共享项**
  - `AGENTS.md`
  - `skills/`
  - `config/codex.shared.toml`
  - 安装脚本与校验脚本
- **应保留在每台机器本地的项**
  - `~/.codex/auth.json`
  - `~/.codex/history.jsonl`
  - `~/.codex/sessions/`
  - `~/.codex/log*`、`~/.codex/cache/`、`~/.codex/tmp/`
  - `~/.codex/memories/`
  - `~/.codex/config.toml` 中的本机路径、项目 trust 和其他设备特有项
- 当前安装脚本采用“**共享默认 + 保留本地**”策略：
  - 仓库托管的共享键会被同步覆盖
  - 本机未托管键会被保留
  - `mcp_servers` / `plugins` 中，仓库已声明的条目视为托管条目；仓库未声明的本地条目保持不动

## Git 提交门禁

- 本仓库使用 `.githooks/commit-msg` + `scripts/commitlint.py` 校验 commit message。
- 规则与 `git-workflow` skill 保持一致：
  - 格式必须为 `<type>(<scope>): <subject>`
  - `subject` 必须包含中文
  - `subject` 不能以句号结尾
  - 首行长度不超过 72 字符
- 首次 clone 后执行：

```bash
./scripts/install-git-hooks.sh
```

- `install-git-hooks.sh` 与 `install-local-agent-config.sh` 是两个独立步骤：
  - 前者只负责 Git hooks
  - 后者只负责本地 Codex / Claude 接入

- 安装后，类似 `fix: persist group fixture state for 3D virtual fixture sync` 这类不合规消息会被直接拒绝。

## 强制 `verify-ios-build` 收尾门禁

- 只要任务产出修改了 Apple Xcode 项目相关内容，最终必须切到 `verify-ios-build` 做收尾验证。
- “Apple Xcode 项目相关内容”包括：代码、测试、资源、`.xcodeproj` / `.xcworkspace` / `.pbxproj`、`xcconfig`、scheme、`Info.plist`、entitlements、构建脚本，以及项目内 `.codex/xcodebuild.env` 一类环境配置。
- 最终门禁必须在**目标项目根目录的项目环境**执行，不能把沙箱内构建结果当成最终验收。
- 如果同时存在 `.xcworkspace` 与 `.xcodeproj`，验证必须优先 `.xcworkspace`。
- 对 iOS 项目，验证默认优先已连接真机；找不到连接中的真机时，自动回退到 simulator。
- 在 `verify-ios-build` 成功前，任务不能宣告“已完成”。
- 可用以下脚本检查本仓库的技能规则是否仍满足该门禁策略：

```bash
python3 scripts/lint_verify_ios_build_policy.py
```

## 通用约定
- 对应项目中新建 `.swift`、`.h`、`.m`、`.mm` 等源码文件且项目要求文件头时，`Created by` 必须使用**本机用户名称**，不能写 `Codex`。
- 当前环境下默认作者名取自本机用户信息：`Choshim.Wei`。
- 日期格式遵循项目约定；若无额外约定，默认使用 `YYYY/M/D`，例如：`Created by Choshim.Wei on 2026/4/11.`

## 适用场景
- iOS / macOS / Swift / SwiftUI / UIKit / Objective-C 开发
- Apple 官方文档与 WWDC 知识检索
- Word / `.docx` 文档读取、模板编辑、批注修订与生成
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
