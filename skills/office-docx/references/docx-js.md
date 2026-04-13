# docx-js / `docx` 生成 DOCX 速查

## 适用时机
当没有现成 `.docx` 模板，或现有模板不值得继续复用时，直接用 Node `docx`（常被口头称为 docx-js）从零生成一份 Word 文档。

## 基础结构
```javascript
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel,
} = require("docx");

const doc = new Document({
  sections: [{
    children: [
      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("Title")],
      }),
    ],
  }],
});

Packer.toBuffer(doc).then(buffer => fs.writeFileSync("output.docx", buffer));
```

下文其余片段默认也已从 `docx` 引入对应 symbol，例如 `TableOfContents`、`LevelFormat`、`AlignmentType`、`Table`、`ImageRun`、`Header`、`Footer`、`PageBreak` 等。

生成后立即校验：
```bash
python scripts/office/validate.py output.docx
```

## 页面尺寸
- **必须显式设置 page size**，不要吃默认值。
- `docx` 默认是 A4；如果目标是美式文档，通常要改成 US Letter。

```javascript
sections: [{
  properties: {
    page: {
      size: {
        width: 12240,
        height: 15840,
      },
      margin: {
        top: 1440,
        right: 1440,
        bottom: 1440,
        left: 1440,
      },
    },
  },
  children: [/* ... */],
}]
```

常见尺寸（DXA，1440 = 1 英寸）：

| 纸张 | 宽 | 高 |
| --- | ---: | ---: |
| US Letter | 12240 | 15840 |
| A4 | 11906 | 16838 |

横向页面要显式设置 `orientation`，并注意库会交换宽高。

## 标题与目录
### 覆盖内建标题样式
```javascript
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 24 } } },
    paragraphStyles: [
      {
        id: "Heading1",
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 32, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 },
      },
    ],
  },
});
```

### 目录（TOC）
```javascript
new TableOfContents("Table of Contents", {
  hyperlink: true,
  headingStyleRange: "1-3",
})
```

关键规则：
- TOC 依赖 `HeadingLevel` 与对应 `outlineLevel`。
- 不要自己发明一套与标题脱节的样式名，再指望 TOC 自动识别。

## 列表
**不要手打 Unicode bullet。**

```javascript
const doc = new Document({
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{
        level: 0,
        format: LevelFormat.BULLET,
        text: "•",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } },
      }],
    }],
  },
});
```

关键规则：
- 同一个 `reference` 会连续编号。
- 不同 `reference` 会重新开始编号。
- 需要编号列表时用 `LevelFormat.DECIMAL`，不要手写 `1.`、`2.`。

## 表格
DOCX 表格最容易出问题，默认按以下规则：

```javascript
new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [4680, 4680],
  rows: [
    new TableRow({
      children: [
        new TableCell({
          width: { size: 4680, type: WidthType.DXA },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          shading: { fill: "D5E8F0", type: ShadingType.CLEAR },
          children: [new Paragraph("Cell")],
        }),
      ],
    }),
  ],
})
```

关键规则：
- 总是用 `WidthType.DXA`，不要用百分比。
- 表格 `width`、`columnWidths`、cell `width` 三者必须一致。
- `columnWidths` 之和必须等于 table width。
- `ShadingType.CLEAR` 比 `SOLID` 更安全。
- 不要把 table 当分隔线或布局容器乱用。

## 图片
```javascript
new Paragraph({
  children: [new ImageRun({
    type: "png",
    data: fs.readFileSync("image.png"),
    transformation: { width: 200, height: 150 },
    altText: { title: "Title", description: "Desc", name: "Name" },
  })],
})
```

关键规则：
- `ImageRun` 必须传 `type`。
- 图片尺寸要显式给出，不要完全依赖原图。
- 正式交付文档应提供可读 `altText`。

## 常用结构
### 分页
```javascript
new Paragraph({ children: [new PageBreak()] })
```

### 超链接
```javascript
new ExternalHyperlink({
  children: [new TextRun({ text: "Click here", style: "Hyperlink" })],
  link: "https://example.com",
})
```

### 页眉页脚与页码
```javascript
sections: [{
  headers: {
    default: new Header({ children: [new Paragraph("Header")] }),
  },
  footers: {
    default: new Footer({
      children: [new Paragraph({
        children: [new TextRun("Page "), new TextRun({ children: [PageNumber.CURRENT] })],
      })],
    }),
  },
}]
```

## 从零生成时的默认建议
- 标题层级、目录、页眉页脚和页码先确定，再填正文。
- 页面尺寸、页边距、默认字体先定死，避免后续全局返工。
- 表格、图片、页码、双栏或复杂页脚都应在生成后做 PDF 视觉 QA。
- 生成成功不等于排版正确；交付前仍要跑 `validate.py` 和视觉检查。
