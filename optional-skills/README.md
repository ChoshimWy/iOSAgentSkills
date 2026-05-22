# Optional Skill Packs

这里存放默认不常驻的低频 skills，不在 Codex 默认发现路径里。

## Packs

- `research/`
  - `ui-ux-design-system`
  - `app-store-changelog`
  - `app-store-opportunity-research`
  - `open-design`
- `docs/`
  - `html-docs`
  - `office-docx`
  - `office-pptx`
- `workflow/`
  - `git-workflow`
  - `gh-pr-flow`
- `macos/`
  - `macos-menubar-tuist-app`
  - `macos-spm-app-packaging`

## 使用说明

- 默认 Codex 只读取 `skills/` 里的 iOS core skills。
- iOS 专项模块（如 `apple-docs`、`swiftui-ui-patterns`、`sdk-architecture` 等）保留在 core 中，供主 Skill `codex-subagent-orchestration` 内部路由使用。
- 需要某个 optional pack 时，按任务临时把对应 skill 引入当前工作流即可。
- 本仓库保留这些 skill 作为可复用模板源，但它们不会参与默认上下文预算。
