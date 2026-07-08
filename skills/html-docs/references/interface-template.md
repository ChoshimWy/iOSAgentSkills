# 接口说明 HTML 模板

## 默认风格
- Notion 风格优先：轻表格、轻 callout、正文和示例分离；最终 HTML 必须按 `dark-mode-style.md` 支持系统暗黑模式。

## 结构
- Hero：接口主题、版本、适用范围
- 总览：改造目的 / 兼容策略
- 接口矩阵：接口、方法、请求、响应、说明
- 单接口详情：
  - URL
  - 请求参数表
  - 示例 Query / Body
  - 响应字段表
  - 示例 Response JSON
  - 幂等 / 错误 / 约束说明
- 与旧版本兼容说明
- 数据一致性与回退策略

## 强制要求
- 请求与响应都要给字段表
- 至少给一个完整示例
- 明确哪些字段是新增、当前、保留、废弃
- 明确空数组 / 空对象 / 缺省值是否代表删除
- 若涉及同步，必须写 latestTime / ack / schemaVersion / baselineStatus
