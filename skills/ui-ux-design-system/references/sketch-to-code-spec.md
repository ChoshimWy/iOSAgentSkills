# Sketch 源文件到代码实现规范

用于把 Sketch 源文件、SketchMCP、蓝湖 / PNG 补充素材转换为可执行的 `Design-to-Code Spec`，再交给 `ios-feature-implementation` 的 SwiftUI / UIKit / mixed-ui 模式实现。

## 目标

- 先抽取设计事实，再写代码；禁止直接“看图猜 UI”。
- 将设计稿转换为 tokens、组件合同、布局规则、资源清单、状态矩阵和验收清单。
- 不确定的值必须标记 `unknown`，不要脑补。
- 代码实现阶段必须使用 Spec 中的 tokens / component contract，禁止散落 magic number。

## 输入优先级

| 优先级 | 输入 | 用途 |
| --- | --- | --- |
| 1 | Sketch 源文件 + SketchMCP | 读取画板、图层、文本、样式、资产和截图 |
| 2 | 蓝湖 / Figma inspect 链接 | 补充标注、切图和设计注释 |
| 3 | 原始 PNG 截图 | 视觉校验和截图对比 |
| 4 | 人工说明 | 交互、状态、业务语义、适配和不可见规则 |

## SketchMCP 读取顺序

1. 连接与上下文
   - 确认 Sketch 已打开目标 `.sketch` 文件。
   - `GET /mcp` 返回 405 属于正常现象；MCP 需要 POST JSON-RPC。
   - 先调用 `get_guide(topic: "mcp")`，需要更深内容操作时再读 `use` / `styling` / `assets`。
2. 文档与画板
   - 调用 `get_document_info` 获取 `documentID`、page、frame / artboard 列表、尺寸、layerCount。
   - 让用户指定目标画板；若目标不明确，先列候选，不要猜。
3. 层级与截图
   - 对目标画板调用 `get_layer_tree_summary(depth: 3~6)`。
   - 调用 `get_screenshot` 保存目标画板截图，用于视觉验收。
4. 样式与 token
   - 读取 `get_design_assets(kind: "textStyle" | "layerStyle" | "swatch" | "symbol")`。
   - 必要时用 `run_code` 只读抽取选中画板内文本样式、fills、borders、cornerRadius、shadows、blur、opacity、frame。
5. 资产
   - 记录 image / icon / symbol instance 的 layer 名称、尺寸、导出倍率和资源命名。
   - 对无法用原生控件重建的复杂视觉，要求单独导出资产，而不是从整屏截图抠图。

## 必读数据清单

### 画板与适配

- 页面 / 画板名称、ID、尺寸。
- 设计单位和倍率：`pt` / `px`、`@1x` / `@2x` / `@3x`。
- 目标设备、safe area、状态栏 / 导航栏 / tab bar 是否由系统实现。
- 滚动区域、固定区域、键盘弹出后的布局变化。
- iPhone / iPad / 横竖屏 / Dynamic Type / 深色模式规则。

### 结构与组件

- 页面组件树：screen -> region -> component -> primitive。
- 每个组件的职责、复用名、状态和约束。
- list / card / modal / sheet / toolbar / button / input / tab / toast 等组件边界。
- 可点击区域与最小 hit target。

### Tokens

- Color：HEX、alpha、语义名、light/dark 对应关系。
- Typography：字体、字号、字重、lineHeight、letterSpacing、对齐、截断规则。
- Spacing：页面边距、组件 padding、gap、列表间距、栅格单位。
- Radius：容器、按钮、输入框、图片、标签。
- Border：宽度、颜色、位置。
- Shadow / Blur：x/y/blur/spread/color/alpha、material / background blur。
- Opacity：禁用态、遮罩、分割线、浮层。
- Motion：弹窗、选择、加载、错误提示的动画时长和曲线；没有标注则写 `unknown`。

### 文案与数据

- 所有可见文案、换行、最大长度、空值策略。
- 多语言 / 中文英文长度差异。
- 示例数据：最短、正常、超长、空列表。

### 状态矩阵

至少检查：

- default
- selected / highlighted / pressed
- disabled
- loading
- empty
- error
- keyboard shown
- modal presented / dismissed
- light / dark mode（如产品要求）

## Design-to-Code Spec 输出格式

```json
{
  "source": {
    "file": "path-or-link",
    "document_id": "optional",
    "page": "optional",
    "frame": {
      "id": "optional",
      "name": "...",
      "size": "375x768",
      "scale": "unknown | @1x | @2x | @3x"
    },
    "evidence": {
      "screenshot": "path-or-tool-output",
      "layer_tree": "summary-or-path",
      "assets": []
    }
  },
  "platform": {
    "target": "SwiftUI | UIKit | mixed-ui | web",
    "device": "iPhone/iPad/unknown",
    "min_os": "optional",
    "safe_area": "system | custom | unknown"
  },
  "component_tree": [],
  "tokens": {
    "color": [],
    "typography": [],
    "spacing": [],
    "radius": [],
    "border": [],
    "shadow": [],
    "opacity": [],
    "motion": []
  },
  "components": [
    {
      "name": "...",
      "role": "...",
      "layout": {},
      "states": [],
      "assets": [],
      "implementation_hint": "native | custom | image-asset | unknown"
    }
  ],
  "content_rules": [],
  "responsive_rules": [],
  "accessibility_rules": [],
  "implementation_plan": [],
  "visual_acceptance": [],
  "unknowns": []
}
```

## 实现前门禁

进入代码实现前必须具备：

- 目标画板明确。
- 至少有一份画板截图和层级摘要。
- tokens 已提取或明确 `unknown`。
- 组件边界和状态矩阵已列出。
- 资源清单和需要导出的资产已列出。
- 视觉验收项可执行，例如“弹窗宽度 312pt、圆角 16pt、遮罩 40% black”。

## 高保真验收闭环

1. 按 Spec 分层实现：tokens -> primitive -> component -> screen。
2. 运行后截图。
3. 对比 Sketch 截图与实现截图。
4. 只修正差异项，不重新设计。
5. 每轮差异记录为：
   - 设计稿表现
   - 当前实现表现
   - 偏差类型：size / spacing / color / typography / asset / state / interaction
   - 应调整的 token / 组件 / 文件

## 常见禁止项

- 只看整屏 PNG 就直接写代码。
- 将图层视觉整体切成一张大图当 UI。
- 未确认倍率时把 px 直接写进 pt。
- 不读文本样式 / 图层样式，只靠肉眼估值。
- 不区分系统导航栏、safe area 和自绘区域。
- 把单一状态误认为完整组件规范。
- 把 unknown 值悄悄补成猜测值。
