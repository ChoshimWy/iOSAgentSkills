# Overlay 与 Toast

## 用途
用于 toast、banner、加载浮层等不应改变底层布局的临时界面。

## 核心规则
- 用 `.overlay(alignment:)` 放置，不要把临时浮层塞进主布局。
- 浮层状态轻量、可自动消失。
- 如果多个功能都可能触发 toast，考虑集中管理。
