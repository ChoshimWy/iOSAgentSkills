# Searchable

## 用途
用于原生搜索 UI、scope 切换和异步搜索结果展示。

## 核心规则
- 搜索文本绑定本地状态。
- 多搜索模式优先用 `.searchScopes`。
- 高频查询应配合 `.task(id:)` 或防抖，避免过度请求。
