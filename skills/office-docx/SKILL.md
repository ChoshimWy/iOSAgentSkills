---
name: office-docx
description: 处理 Word / .docx 文档的读取、提取、分析、模板编辑、从零创建、批注与修订处理、批量替换、解包回包与基础校验。只要用户提到 .docx、Word、Word 文档，或要求把内容产出为带标题、目录、页码、信头、表格等格式化 Word 文件时使用；不要把它用于 .pptx/.xlsx、PDF、Google Docs 或普通文案写作。
---

# DOCX 文档处理

## 角色定位
- 专项型 skill。
- 负责 `.docx` 文件的读取、分析、模板驱动编辑、从零生成、批注/修订处理与交付前 QA。
- 不负责 `.pptx` / `.xlsx` / PDF，也不替代普通文案写作、Google Docs 协作或与 Word 文件无关的内容整理。

## 触发判定（硬边界）
- 用户明确提到 `.docx`、Word、Word 文档，或给出一个 Word 文件路径。
- 需要读取、提取、总结、修改、更新、转换、导出或校验 `.docx` 文件。
- 需要把报告、memo、信函、模板、合同、说明文档等实际产出为格式化的 Word 文件。
- 需要处理 tracked changes、comments、查找替换、插图替换、目录、页码、页眉页脚或版式规则。
- 如果任务只是写提纲、文案、报告正文或结构建议，但**不需要实际打开、创建、修改 `.docx` 文件**，不要把本 skill 作为主 skill。

## 适用场景
- 读取现有 Word 文档并提取正文、修订、注释或结构。
- 基于现有 `.docx` 模板改报告、信函、备忘录、合同或制度文档。
- 解包 XML 后做精确替换、样式修正、评论插入或 tracked changes 处理。
- 从零创建带标题层级、目录、页码、表格、图片和页眉页脚的新 `.docx`。
- 将 legacy `.doc` 转为 `.docx`，或把 `.docx` 转 PDF / 图片做视觉 QA。

## 核心工作流
1. **先判断任务类型**
   - 读取/摘要：优先用 `pandoc --track-changes=all`
   - 模板编辑、修订、批注：先读 `references/editing.md`
   - 从零创建：先读 `references/docx-js.md`
   - 需要最终可视化检查：走 `scripts/office/soffice.py` 转 PDF
2. **先取证，再修改**
   - 对已有文档，优先运行：
     - `pandoc --track-changes=all input.docx -o output.md`
     - `python scripts/office/unpack.py input.docx unpacked/`
   - 先看正文、修订、注释和 XML 结构，再决定编辑策略。
3. **已有文档编辑要走标准链路**
   - `unpack -> XML 编辑 -> validate -> pack`
   - legacy `.doc` 先转 `.docx` 再编辑。
   - comments 优先使用 `python scripts/comment.py`，不要手工补全所有 comments 关系和内容类型。
4. **修订处理要先分清目标**
   - 如果要**保留** tracked changes，就按 redline 规则编辑 XML。
   - 如果要输出干净文档，使用 `python scripts/accept_changes.py input.docx output.docx`。
   - 未经确认，不要一边新增修订一边自动 accept all changes。
5. **QA 至少做一轮复查**
   - 内容 QA：重新提取文本，检查占位符、残留示例文本、修订/批注是否符合预期。
   - 结构 QA：跑 `python scripts/office/validate.py`
   - 视觉 QA：版式敏感文档转 PDF / 图片逐页检查分页、溢出、错位和页眉页脚。

## 快速命令
| 任务 | 命令 |
|---|---|
| `.doc` 转 `.docx` | `python scripts/office/soffice.py --headless --convert-to docx input.doc` |
| 提取文本与修订 | `pandoc --track-changes=all input.docx -o output.md` |
| 解包 XML | `python scripts/office/unpack.py input.docx unpacked/` |
| 校验文档或解包目录 | `python scripts/office/validate.py input.docx` |
| 接受全部修订 | `python scripts/accept_changes.py input.docx clean.docx` |
| 添加 comment / reply | `python scripts/comment.py unpacked/ 0 "Comment text"` |
| 回包 DOCX | `python scripts/office/pack.py unpacked/ output.docx --original input.docx` |
| 转 PDF 做视觉 QA | `python scripts/office/soffice.py --headless --convert-to pdf output.docx` |
| PDF 转图片 | `pdftoppm -jpeg -r 150 output.pdf page` |

## 依赖与环境前提
- 文本提取：`pandoc`
- 从零创建：Node `docx` 包（常见安装方式：`npm install -g docx`）
- XML 处理：`defusedxml`
- 文档转换：LibreOffice / `soffice`
- 图片化 QA：`pdftoppm`（Poppler）
- 在受限环境里优先使用 `scripts/office/soffice.py`，不要假设直接调用 `soffice` 一定稳定可用。

## 参考资源
- `references/editing.md`：现有 `.docx` 的解包编辑、tracked changes、comments、QA 与常见坑。
- `references/docx-js.md`：从零生成 `.docx` 时的 `docx` / docx-js 常用 API、页面尺寸、样式、目录、表格和图片规则。
- `scripts/accept_changes.py`：通过 LibreOffice 接受全部修订，输出干净文档。
- `scripts/comment.py`：在解包目录中补 comments 相关 XML、关系和模板。
- `scripts/office/unpack.py` / `pack.py` / `validate.py`：Office 文档解包、回包和校验基础能力。

## 与其他技能的关系
- 涉及 `.pptx` / PowerPoint 演示文稿时，切换到 `office-pptx`。
- 涉及 `.xlsx`、电子表格或一般数据分析时，不要套用本 skill。
- 只是整理文案、写报告内容、润色措辞，但不触碰实际 Word 文件时，不要主用本 skill。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定当前任务已经加载并正在使用本 Skill 时：

- 在回复末尾追加一行：`// skill-used: office-docx`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范
