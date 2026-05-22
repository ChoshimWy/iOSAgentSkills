# PptxGenJS 速查

## 适用时机
当没有现成模板，或现有模板不值得继续复用时，直接用 PptxGenJS 从零生成一份 `.pptx`。

## 基础结构
```javascript
const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "Your Name";
pres.title = "Presentation Title";

const slide = pres.addSlide();
slide.addText("Hello World!", {
  x: 0.5, y: 0.5, w: 9, h: 0.8,
  fontSize: 36,
  color: "363636",
  bold: true,
});

await pres.writeFile({ fileName: "Presentation.pptx" });
```

## 常用画布尺寸
- `LAYOUT_16x9`：10" × 5.625"
- `LAYOUT_16x10`：10" × 6.25"
- `LAYOUT_4x3`：10" × 7.5"
- `LAYOUT_WIDE`：13.3" × 7.5"

## 文本
### 普通文本
```javascript
slide.addText("Simple Text", {
  x: 1, y: 1, w: 8, h: 1.2,
  fontSize: 24,
  fontFace: "Arial",
  color: "363636",
  bold: true,
  align: "center",
  valign: "middle",
});
```

### 多行与富文本
```javascript
slide.addText([
  { text: "Bold ", options: { bold: true } },
  { text: "Italic ", options: { italic: true } },
], { x: 1, y: 2, w: 8, h: 1 });

slide.addText([
  { text: "Line 1", options: { breakLine: true } },
  { text: "Line 2", options: { breakLine: true } },
  { text: "Line 3" },
], { x: 0.5, y: 3, w: 8, h: 2 });
```

### 易错点
- 调整字距要用 `charSpacing`，不要写 `letterSpacing`。
- 需要和图形、分隔线精确对齐时，给文本框设 `margin: 0`。
- 多行内容依赖 `breakLine: true`，不要自己在纯字符串里随意塞换行期望自动排好。

## 列表与项目符号
```javascript
slide.addText([
  { text: "First item", options: { bullet: true, breakLine: true } },
  { text: "Second item", options: { bullet: true, breakLine: true } },
  { text: "Third item", options: { bullet: true } },
], { x: 0.5, y: 0.5, w: 8, h: 3 });
```

- **不要手打 Unicode bullet**（例如 `• First item`），否则常会出现双 bullet。
- 子项可用 `indentLevel`，编号可用 `bullet: { type: "number" }`。

## 形状
```javascript
slide.addShape(pres.shapes.RECTANGLE, {
  x: 0.5, y: 0.8, w: 1.5, h: 3,
  fill: { color: "FF0000" },
  line: { color: "000000", width: 2 },
});

slide.addShape(pres.shapes.LINE, {
  x: 1, y: 3, w: 5, h: 0,
  line: { color: "FF0000", width: 3, dashType: "dash" },
});
```

### Shadow 注意事项
- `color` 只写 6 位 hex，不要带 `#`，也不要写 8 位透明通道。
- 透明度用 `opacity` 控制，不要编码进颜色值。
- `offset` 必须是非负数；负值可能直接损坏文件。
- 需要向上投影时，使用正 `offset` + `angle: 270`，不要传负 offset。

### 圆角矩形注意事项
- `rectRadius` 只对 `ROUNDED_RECTANGLE` 生效。
- 如果你要在卡片边缘上叠一个矩形色条或遮罩，普通 `RECTANGLE` 往往比圆角矩形更安全，因为后者容易露出圆角。

## 图片
```javascript
slide.addImage({ path: "images/chart.png", x: 1, y: 1, w: 5, h: 3 });
slide.addImage({ path: "https://example.com/image.jpg", x: 1, y: 1, w: 5, h: 3 });
slide.addImage({ data: "image/png;base64,...", x: 1, y: 1, w: 5, h: 3 });
```

### 常用选项
```javascript
slide.addImage({
  path: "image.png",
  x: 1, y: 1, w: 5, h: 3,
  rotate: 45,
  rounding: true,
  transparency: 50,
  altText: "Description",
  hyperlink: { url: "https://example.com" },
});
```

### 尺寸策略
```javascript
{ sizing: { type: "contain", w: 4, h: 3 } }
{ sizing: { type: "cover", w: 4, h: 3 } }
{ sizing: { type: "crop", x: 0.5, y: 0.5, w: 2, h: 2 } }
```

- `contain`：完整显示，保持比例
- `cover`：填满区域，可能裁切
- `crop`：精确裁图

## 图标
常见做法是使用 `react-icons` 生成 SVG，再用 `sharp` 转 PNG，以获得较好的兼容性。

```javascript
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const { FaCheckCircle } = require("react-icons/fa");

function renderIconSvg(IconComponent, color = "#000000", size = 256) {
  return ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
}

async function iconToBase64Png(IconComponent, color, size = 256) {
  const svg = renderIconSvg(IconComponent, color, size);
  const pngBuffer = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + pngBuffer.toString("base64");
}
```

## 从零生成时的默认建议
- 每页都给一个明确视觉元素：图片、图标、数字卡片、时间线、流程图，而不是只有标题和 bullets。
- 一页内保留足够留白，不要塞满。
- 标题与正文必须拉开尺度差。
- 深色/浅色背景上的文字与图标都要做对比度检查。
- 生成后仍要走一次 PDF/JPG 视觉 QA；PptxGenJS 能生成文件，不代表版面一定正确。
