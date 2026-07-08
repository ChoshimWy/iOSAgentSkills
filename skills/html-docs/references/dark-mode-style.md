# HTML 暗黑模式样式基线

## 使用时机

生成最终 HTML 文档时读取本文件；如果调用方已经提供等价暗黑模式样式，也必须检查是否覆盖正文、表格、代码块、callout、链接、chips 与 checklist 状态。

## 必备规则

- `<head>` 必须包含：`<meta name="color-scheme" content="light dark">`。
- 颜色必须通过 CSS custom properties 管理，禁止在正文结构里散落 light-only 颜色。
- 默认 `:root` 写 light token；用 `@media (prefers-color-scheme: dark)` 覆盖 dark token。
- 表格、代码块、callout、chips、状态标识、链接和边框都要使用语义 token。
- 暗黑模式下正文、弱化文字、链接、代码块与 warning / success / info callout 均需保持可读对比度。

## 最小 CSS 骨架

```html
<meta name="color-scheme" content="light dark">
<style>
  :root {
    color-scheme: light;
    --bg: #f7f8fb;
    --panel: #ffffff;
    --panel-muted: #f1f5f9;
    --text: #172033;
    --muted: #64748b;
    --border: #e2e8f0;
    --accent: #2563eb;
    --accent-soft: #dbeafe;
    --code-bg: #0f172a;
    --code-text: #e5e7eb;
    --callout-info-bg: #eff6ff;
    --callout-info-border: #93c5fd;
    --callout-warn-bg: #fff7ed;
    --callout-warn-border: #fdba74;
    --callout-success-bg: #ecfdf5;
    --callout-success-border: #86efac;
  }

  @media (prefers-color-scheme: dark) {
    :root {
      color-scheme: dark;
      --bg: #0b1020;
      --panel: #111827;
      --panel-muted: #1f2937;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --border: #374151;
      --accent: #60a5fa;
      --accent-soft: rgba(96, 165, 250, 0.18);
      --code-bg: #020617;
      --code-text: #e2e8f0;
      --callout-info-bg: rgba(37, 99, 235, 0.18);
      --callout-info-border: rgba(147, 197, 253, 0.55);
      --callout-warn-bg: rgba(245, 158, 11, 0.16);
      --callout-warn-border: rgba(251, 191, 36, 0.55);
      --callout-success-bg: rgba(16, 185, 129, 0.15);
      --callout-success-border: rgba(110, 231, 183, 0.5);
    }
  }

  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
  }

  main,
  .card,
  .hero {
    background: var(--panel);
    border: 1px solid var(--border);
  }

  a { color: var(--accent); }
  .muted { color: var(--muted); }

  code,
  pre {
    background: var(--code-bg);
    color: var(--code-text);
  }

  th {
    background: var(--panel-muted);
  }

  td,
  th {
    border-color: var(--border);
  }

  .chip {
    background: var(--accent-soft);
    color: var(--accent);
  }

  .callout.info {
    background: var(--callout-info-bg);
    border-color: var(--callout-info-border);
  }

  .callout.warn {
    background: var(--callout-warn-bg);
    border-color: var(--callout-warn-border);
  }

  .callout.success {
    background: var(--callout-success-bg);
    border-color: var(--callout-success-border);
  }
</style>
```
