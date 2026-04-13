# PPTX 模板编辑指南

## 适用时机
当你已经有一个现成 `.pptx` 模板，目标是复用其布局、字体、母版、配色或组件时，优先走本流程，而不是从零重建。

## 标准流程
1. **先分析模板**
   ```bash
   python scripts/thumbnail.py template.pptx
   python -m markitdown template.pptx
   ```
   - 看 `thumbnails.jpg` 理解页面布局、隐藏页、重复样式。
   - 看文本抽取结果识别占位符、残留文案、注释或页内结构。

2. **做内容到模板的映射**
   - 为每个内容区块挑选最适合的 slide。
   - 避免全篇重复同一种“标题 + bullet”布局；优先利用模板里已有的多栏、数字卡片、图片区、引用页、分节页等变体。

3. **解包**
   ```bash
   python scripts/office/unpack.py template.pptx unpacked/
   ```

4. **先做结构变化，再做文案变化**
   - 删除不要的 slide：从 `ppt/presentation.xml` 的 `<p:sldIdLst>` 中移除。
   - 重排 slide：调整 `<p:sldIdLst>` 顺序。
   - 新增 slide：
     ```bash
     python scripts/add_slide.py unpacked/ slide2.xml
     python scripts/add_slide.py unpacked/ slideLayout2.xml
     ```
   - **不要手工复制 slide 文件**。`add_slide.py` 会同时处理 notes、Content_Types、relationship IDs 等易错点。

5. **编辑内容**
   - 逐个打开 `ppt/slides/slideN.xml` 修改文本与元素。
   - 先识别这个 slide 上所有占位符：标题、正文、图片、图标、图表、脚注、页脚。
   - 有多个条目时，为每个条目创建独立段落，不要把整串内容塞进一个 `<a:t>`。

6. **清理孤儿资源**
   ```bash
   python scripts/clean.py unpacked/
   ```

7. **回包并校验**
   ```bash
   python scripts/office/pack.py unpacked/ output.pptx --original template.pptx
   ```

## 编辑规则
- 标题、分节标题、行内标签优先加粗。
- 不要手打 Unicode bullet（如 `•`）；应沿用模板已有的列表格式。
- 多个步骤/条目要拆成多个 `<a:p>` 段落。
- 新增带引号的文本时，优先使用 XML 实体而不是直接粘贴智能引号。
- 如果文本长度明显比模板原文更长，默认会带来换行、溢出或卡片高度不够，必须做视觉复查。

## 常见坑
### 1) 模板槽位数和实际内容数不一致
- 模板有 4 个成员位，但源内容只有 3 个时，应删除第 4 组完整元素，而不是只清空其中的文字。
- 图片、图标、背景形状、装饰线也都算槽位的一部分。

### 2) 直接复制 slide 文件
- 不要手工 `cp slide2.xml slide5.xml`。
- 这通常会漏掉 rels、notes、Content_Types 与 presentation relationships，最终产生损坏文件。

### 3) 把多个项目写进同一段
- 错误：一个 `<a:p>` 里串联多个步骤或多条 bullet。
- 正确：每条内容单独一个段落，需要标题时另起段落并加粗。

### 4) 长文本替换
- 原模板是短标题，替换成一整句长文案时，极易发生：
  - 标题换成两行导致下方装饰线穿过文字
  - 卡片内正文溢出
  - 页脚或引用上移后与正文碰撞
- 任何长文本替换后都要跑视觉 QA。

## 视觉 QA
将 deck 转成 PDF，再转成单页图片检查：

```bash
python scripts/office/soffice.py --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
```

重点检查：
- 文本/图形重叠
- 文本溢出、截断、过度换行
- 页边距是否过小
- 同类卡片或列是否对齐
- 间距是否过密或明显不均匀
- 深浅背景上的文字和图标是否有足够对比度
- 是否还残留模板占位符、示例文案、默认页脚

## 内容 QA
```bash
python -m markitdown output.pptx
python -m markitdown output.pptx | grep -iE "xxxx|lorem|ipsum|this.*(page|slide).*layout"
```

如果还能搜到占位符或示例文字，就不要视为完成。

## XML 与字符注意事项
- 需要保留前后空格时，对 `<a:t>` 使用 `xml:space="preserve"`。
- 避免用会破坏 namespace 的简陋 XML 写法；优先沿用现有脚本链路。
- 智能引号常见实体：
  - `&#x201C;`：左双引号
  - `&#x201D;`：右双引号
  - `&#x2018;`：左单引号
  - `&#x2019;`：右单引号
