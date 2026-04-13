# DOCX 模板编辑与修订处理指南

## 适用时机
当你已经有一个现成 `.docx` 文档或模板，需要复用其样式、页眉页脚、编号、目录、批注或修订历史时，优先走本流程，而不是从零重建。

## 标准流程
1. **必要时先转换格式**
   ```bash
   python scripts/office/soffice.py --headless --convert-to docx input.doc
   ```
   - legacy `.doc` 先转成 `.docx` 再编辑。

2. **先取证**
   ```bash
   pandoc --track-changes=all input.docx -o output.md
   python scripts/office/unpack.py input.docx unpacked/
   ```
   - `pandoc` 先看正文、修订与注释大致情况。
   - `unpack.py` 会把 XML 解开，并对 DOCX 做 run 合并与 redline 简化，方便后续编辑。

3. **编辑 `unpacked/word/` 下的 XML**
   - 普通文本替换：优先直接编辑现有 XML，不要为了简单替换再写临时脚本。
   - tracked changes：按最小改动原则，只包裹真正变更的片段。
   - comment / reply：优先用 `python scripts/comment.py ...`，不要手工补 comments boilerplate。

4. **校验并回包**
   ```bash
   python scripts/office/validate.py unpacked/ --original input.docx
   python scripts/office/pack.py unpacked/ output.docx --original input.docx
   ```
   - `pack.py` 会做基础 auto-repair，但不能修复错误的 XML 结构或缺失关系。

5. **做 QA**
   - 内容 QA：重新导出文本，检查占位符、残留示例文案、批注和修订。
   - 视觉 QA：版式敏感时转 PDF / 图片看分页、表格、页眉页脚和图片位置。

## 编辑规则
- 默认把 tracked changes / comments 的作者名写成 `Claude`，除非用户明确要求其它名字。
- 新增引号或 apostrophe 时，优先使用智能引号实体：
  - `&#x2018;` `&#x2019;` `&#x201C;` `&#x201D;`
- 需要保留前后空格时，对 `<w:t>` 添加 `xml:space="preserve"`。
- 需要保留原格式时，复制原 `<w:rPr>`，不要只替换文本节点。
- 目录、页码、样式、编号通常依赖既有 Word 结构；不要随意删除相关字段后再猜测回填。

## 修订（Tracked Changes）
### 基本模式
```xml
<w:ins w:id="1" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:t>inserted text</w:t></w:r>
</w:ins>

<w:del w:id="2" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:delText>deleted text</w:delText></w:r>
</w:del>
```

关键规则：
- 只标记真正变化的文本，不要把整段没变内容都包进修订。
- 在 `<w:del>` 内使用 `<w:delText>`，不要继续用 `<w:t>`。
- 删除整段/整条列表项时，要同时处理段落标记；否则 accept changes 后可能留下空段落。
- 新增修订时，优先替换整个 `<w:r>` 块，不要把 `<w:ins>` / `<w:del>` 强塞进现有 run 内部。

## 批注（Comments）
先运行：
```bash
python scripts/comment.py unpacked/ 0 "Comment text with &amp; and &#x2019;"
python scripts/comment.py unpacked/ 1 "Reply text" --parent 0
python scripts/comment.py unpacked/ 2 "Custom author" --author "Reviewer Name"
```

再在 `document.xml` 中放 comment markers。关键规则：
- `<w:commentRangeStart>` 和 `<w:commentRangeEnd>` 必须是 `w:p` 的直接子节点。
- 它们**不能**放在 `<w:r>` 内部。
- reply 需要嵌套在 parent comment 的 range 内。

示例：
```xml
<w:commentRangeStart w:id="0"/>
<w:r><w:t>text</w:t></w:r>
<w:commentRangeEnd w:id="0"/>
<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="0"/></w:r>
```

## 常见坑
### 1) 直接编辑 packed `.docx`
- 不要把 `.docx` 当 zip 手工来回解压再改零散文件。
- 优先走 `unpack.py` / `pack.py`，这样能保持格式、压缩与校验链路一致。

### 2) tracked changes 包裹范围过大
- 错误：整段内容全删再整段重插。
- 正确：只对变更词、数字、子句打 redline，保留不变部分。

### 3) comments 关系缺失
- 手工加 `comments.xml` 但忘了补 `[Content_Types].xml` 或 `document.xml.rels`，文档很容易损坏。
- 有 comment 需求时，优先使用 `comment.py` 自动处理。

### 4) 智能引号和空格丢失
- 直接粘贴富文本内容时，常导致智能引号被替换、首尾空格被吞掉。
- 对排版敏感内容，优先用 XML 实体和 `xml:space="preserve"`。

### 5) 误把“清理文档”理解成 accept all changes
- “输出干净文档”才使用 `accept_changes.py`。
- 如果用户要保留审校痕迹，就不能自动 accept all changes。

## QA 建议
### 内容 QA
```bash
pandoc --track-changes=all output.docx -o output.md
rg -n "xxxx|lorem|ipsum|TODO|TBD" output.md
```

重点检查：
- 占位符是否残留
- comments / replies 是否完整
- tracked changes 是否只覆盖预期内容
- 标题层级、编号、目录项是否合理

### 视觉 QA
```bash
python scripts/office/soffice.py --headless --convert-to pdf output.docx
pdftoppm -jpeg -r 150 output.pdf page
```

重点检查：
- 分页是否异常
- 表格是否溢出或列宽错乱
- 页眉页脚和页码是否跑位
- 图片、签名、抬头或印章是否偏移
