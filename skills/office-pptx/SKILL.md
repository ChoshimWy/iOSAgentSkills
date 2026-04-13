---
name: office-pptx
description: 处理 PowerPoint / .pptx 演示文稿的读取、提取、分析、模板编辑、从零创建、拆分合并、缩略图预览、解包回包与基础校验。只要用户提到 .pptx、PowerPoint、slides、deck、presentation，或需要打开、创建、修改、导出、检查幻灯片文件时使用；不要把它用于 docx/xlsx、普通文案写作或纯视觉方向讨论。
---

# PPTX 演示文稿处理

## 角色定位
- 专项型 skill。
- 负责 `.pptx` 文件的读取、分析、模板驱动编辑、从零生成和交付前 QA。
- 不负责 `docx` / `xlsx`；不替代一般文案撰写、纯视觉设计讨论或与幻灯片文件无关的内容整理。

## 触发判定（硬边界）
- 用户明确提到 `.pptx`、PowerPoint、slides、deck、presentation，或给出一个演示文稿文件路径。
- 需要读取、提取、总结、修改、更新、合并、拆分、导出或校验演示文稿文件。
- 需要基于现有模板改 deck，或从零生成一份可交付的 PowerPoint。
- 如果当前任务只是写提纲、演讲稿、文案或视觉方向，但**不需要实际打开、创建、修改 `.pptx` 文件**，不要把本 skill 作为主 skill。

## 适用场景
- 读取 deck 文本内容并做摘要、比对、占位符扫描。
- 通过缩略图快速理解模板布局、隐藏页与页面风格。
- 解包 `.pptx` 后直接编辑 slide XML，再重新清理与打包。
- 使用 PptxGenJS 从零生成一份新演示文稿。
- 将 deck 转成 PDF / JPG 做视觉 QA，检查重叠、溢出、边距、对齐和残留占位符。

## 核心工作流
1. **先判断任务类型**
   - 读取/摘要：优先用 `python -m markitdown input.pptx`
   - 模板编辑：先读 `references/editing.md`
   - 从零创建：先读 `references/pptxgenjs.md`
   - 视觉 QA：优先走 `scripts/office/soffice.py` + `pdftoppm`
2. **先取证，再修改**
   - 对已有 deck 或模板，先运行：
     - `python scripts/thumbnail.py input.pptx`
     - `python -m markitdown input.pptx`
   - 先看布局、隐藏页、占位符和文本长度，再决定改哪些 slide。
3. **模板编辑要走标准链路**
   - `unpack -> 结构调整 -> 文本/元素编辑 -> clean -> pack`
   - 需要新增 slide 时，使用 `python scripts/add_slide.py`，不要手工复制 slide 文件。
   - 结构变化（删除、复制、重排）应在正式改文案前完成。
4. **QA 必须拆成两类**
   - 内容 QA：重新跑 `markitdown`，并检查占位符或残留文本
   - 视觉 QA：转成图片逐页检查重叠、截断、过密、对齐和低对比度问题
   - 至少完成一轮“修复后重新验证”，不要第一版就宣布完成。

## 快速命令
| 任务 | 命令 |
|---|---|
| 提取文本 | `python -m markitdown input.pptx` |
| 生成缩略图网格 | `python scripts/thumbnail.py input.pptx` |
| 解包 XML | `python scripts/office/unpack.py input.pptx unpacked/` |
| 新增/复制 slide | `python scripts/add_slide.py unpacked/ slide2.xml` |
| 清理孤儿资源 | `python scripts/clean.py unpacked/` |
| 回包 PPTX | `python scripts/office/pack.py unpacked/ output.pptx --original input.pptx` |
| 转 PDF | `python scripts/office/soffice.py --headless --convert-to pdf output.pptx` |
| PDF 转图片 | `pdftoppm -jpeg -r 150 output.pdf slide` |

## 依赖与环境前提
- 文本提取：`markitdown[pptx]`
- 缩略图：`Pillow`
- XML 处理：`defusedxml`
- PDF 转换：LibreOffice / `soffice`
- PDF 转图片：`pdftoppm`（Poppler）
- 从零创建：`pptxgenjs`（通常通过 Node 环境安装）
- 在受限环境里优先使用 `scripts/office/soffice.py`，不要假设直接调用 `soffice` 一定稳定可用。

## 参考资源
- `references/editing.md`：模板驱动编辑、slide 操作、XML 修改规范、QA 与常见坑。
- `references/pptxgenjs.md`：从零生成 deck 时的 PptxGenJS 常用 API、布局、图片、图标和排版要点。
- `scripts/thumbnail.py`：快速看模板结构与隐藏页。
- `scripts/add_slide.py`：复制 slide 或从 layout 新建 slide。
- `scripts/office/unpack.py` / `pack.py` / `validate.py`：Office 文档解包、回包和校验基础能力。

## 与其他技能的关系
- 只是整理演讲内容、写文案、写提纲，但不触碰 `.pptx` 文件时，不要主用本 skill。
- 涉及 `docx` / Word 文档时，切换到 `office-docx`。
- 涉及 `xlsx` 或一般表格类 Office 文档问题时，不要套用本 skill。
- 需要纯视觉方向、配色或设计系统决策时，应由对应设计类 skill 主导；本 skill 只处理演示文稿文件本身。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定当前任务已经加载并正在使用本 Skill 时：

- 在回复末尾追加一行：`// skill-used: office-pptx`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
