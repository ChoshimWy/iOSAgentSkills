---
name: ui-ux-pro-max
description: "面向 Web 与移动端 UI/UX 设计的智能参考技能，覆盖 50+ 风格、21+ 色板、50+ 字体搭配、20+ 图表类型与 9 种技术栈（React、Next.js、Vue、Svelte、SwiftUI、React Native、Flutter、Tailwind、shadcn/ui）。当任务涉及设计、构建、评审、优化或修复 UI/UX 代码时使用。"
---

# UI/UX Pro Max

## 适用场景
- 设计新页面、组件或完整设计系统。
- 评审现有 UI/UX 代码，定位布局、可访问性、交互或视觉问题。
- 为特定产品类型、行业或技术栈生成设计方向、色彩、字体和实现建议。

## 核心规则
- 先产出设计系统，再进入具体实现。
- 默认优先检查可访问性、交互触达、性能与响应式，而不是只看视觉风格。
- 在用户未指定技术栈时，默认使用 `html-tailwind`。
- 关键词越具体，检索结果越稳定；必要时分多次搜索不同 domain。

## 工作流
1. 分析需求
- 提炼产品类型、行业、风格关键词、技术栈和页面目标。
- 例如：SaaS、医疗、极简、dashboard、landing page。

2. 生成设计系统
- 默认先运行 `--design-system`：

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<product_type> <industry> <keywords>" --design-system -p "Project Name"
```

- 需要跨会话保存时使用 `--persist`：

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system --persist -p "Project Name"
```

- 需要按页面保存 override 时加入 `--page`：

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system --persist -p "Project Name" --page "dashboard"
```

3. 按需做细分检索
- 需要更细的风格、字体、图表、无障碍或 landing 结构时，使用 domain 搜索：

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<keyword>" --domain <domain> [-n <max_results>]
```

- 常用 domain：
  - `style`
  - `color`
  - `typography`
  - `landing`
  - `chart`
  - `ux`

4. 获取技术栈约束
- 用户未指定时默认：

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<keyword>" --stack html-tailwind
```

- 可选 stack 包括：`html-tailwind`、`react`、`nextjs`、`vue`、`svelte`、`swiftui`、`react-native`、`flutter`、`shadcn`、`jetpack-compose`。

## 参考资源
- `scripts/search.py`：核心检索入口。
- `scripts/design_system.py`：设计系统生成逻辑。
- `data/products.csv`：产品类型数据。
- `data/styles.csv`：风格与视觉方向。
- `data/colors.csv`：色板。
- `data/typography.csv`：字体搭配。
- `data/charts.csv`：图表建议。
- `data/ux-guidelines.csv`：交互与可访问性规则。
- `data/ui-reasoning.csv`：设计系统推理规则。

## 输出要求
- 默认先给设计系统，再给实现建议。
- `--design-system` 支持两种输出格式：

```bash
#终端友好的 ASCII 盒子输出（默认）
python3 skills/ui-ux-pro-max/scripts/search.py "fintech crypto" --design-system

#适合文档的 Markdown 输出
python3 skills/ui-ux-pro-max/scripts/search.py "fintech crypto" --design-system -f markdown
```

- 交付 UI 代码前至少检查：
  - 所有交互元素都有可见 hover / focus 反馈。
  - 正文文本在浅色模式下达到可读对比度。
  - 移动端没有横向滚动。
  - 图标来源一致，不用 emoji 充当 UI icon。
  - 固定/悬浮元素不会遮挡主要内容。
  - 尊重 `prefers-reduced-motion`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: ui-ux-pro-max`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
