# iOS Agent Skills 通用技能包

本项目为 iOS 开发相关的 Agent Skills 通用技能集合，适用于 Claude（.claude/skills）与 Codex（.codex/skills）AI 助手。Skill 目录下的每个子文件夹为一个独立技能，覆盖 iOS 开发、调试、测试、架构、代码审查等常见场景。

## 目录结构

- `code-review/`      —— 代码审查与 API 设计评审
- `debugging/`        —— iOS 调试与问题排查
- `git-workflow/`     —— Git 工作流与协作
- `ios-base/`         —— iOS/Swift/SwiftUI/UIKit 基础开发
- `apple-docs/`       —— Apple 官方文档、API 与 WWDC 资料检索
- `refactoring/`      —— 代码重构与异味识别
- `sdk-architecture/` —— SDK/Framework 架构设计
- `swift-expert/`     —— Swift 进阶能力（并发、协议导向、性能优化）
- `testing/`          —— iOS 测试编写与自动化
- `xcode-build/`      —— Xcode 构建、配置与 CI/CD

## 使用方法

1. **复制技能目录**
   - 对于 Claude，请将本目录复制到 `.claude/skills` 下。
   - 对于 Codex，请将本目录复制到 `.codex/skills` 下。
   - 对应 VC Code Copilot 会自动加载`.claude/skills`下的技能目录。
   - 或者使用软连接方式，将各个 AI 工具对应的 skills 目录连接到该项目 `skills` 目录。示例：
   ```bash
   ln -s iOSAgentSkills/skills .claude/skills
   ```

2. **Agent 自动加载**
   - Agent 会自动识别并加载该目录下的所有技能，无需额外配置。

3. **技能调用**
   - 在对话中描述你的需求，Agent 会根据意图自动调用合适的技能。
   - 例如：
     - “帮我 review 下面这段 Swift 代码”
     - “排查一下这个 iOS crash 日志”
     - “如何为 SwiftUI 组件写单元测试？”
     - “请帮我设计一个可扩展的 iOS SDK 架构”

4. **技能扩展**
   - 新增技能：在本目录下新建子文件夹，包含 `SKILL.md` 及相关参考文档。
   - 参考现有技能目录结构与文档规范。

## 适用场景

- iOS/Swift/SwiftUI 应用开发
- Apple 官方文档与 WWDC 知识检索
- Swift 并发与协议导向进阶开发
- SDK/组件开发与架构设计
- 代码审查、重构与协作
- 自动化测试与 CI/CD
- 性能优化与问题排查

## 贡献

欢迎补充更多 iOS 相关技能，完善文档与案例。

---

如需详细用法与示例，请查阅各技能子目录下的 `SKILL.md` 文件。