# 真机常见问题排查

## 设备显示 `unavailable`
- 检查 USB / Wi‑Fi 连接是否稳定。
- 重新插拔或重新配对设备。
- 确认设备已解锁并信任当前 Mac。

## 设备显示 `available (paired)` 但不是 `connected`
- 设备可能仅完成配对，但当前未物理连接或无线调试不可用。
- 优先改用 `connected` 设备；如果必须使用该设备，先确认无线调试状态与网络连通性。

## `devicectl` 报 CoreDevice / provider 错误
- 先直接重试 `xcrun devicectl list devices`，不要先套 Python 子进程封装。
- 确认 Xcode 已安装完成并启动过一次。
- 如果 `devicectl` 只在某个脚本包装层里失败，优先回到直接 shell 命令，或改用显式 `--device-id` / 设备名称。
- 若仍失败，记录错误文本并明确说明是 CoreDevice / provider 初始化失败，而不是伪造设备结论。

## `xcodebuild` 真机构建失败
- Build / test 的 destination id 来自 `xcodebuild -showdestinations`，不要混用 `devicectl` device identifier。
- 优先检查签名、Bundle ID、Provisioning Profile、Development Team。
- 这类问题交给 `xcode-build` 处理，不在 `ios-device-automation` 内重构签名配置。

## 安装或启动失败
- 确认传给 `devicectl` 的是 device identifier，而不是 `xcodebuild` destination id。
- 确认 `.app` 路径正确，且与真机平台兼容。
- 确认设备已开启开发者模式。
- 重新收集设备详情、已装 app 与运行中进程，确认是否存在旧进程或冲突安装。
