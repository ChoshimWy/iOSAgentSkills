# devicectl Quick Reference

## 常用命令
- 列出设备：`xcrun devicectl list devices`
- 查看设备详情：`xcrun devicectl device info details --device <device-id>`
- 查看已装 app：`xcrun devicectl device info apps --device <device-id>`
- 查看运行中进程：`xcrun devicectl device info processes --device <device-id>`
- 安装 app：`xcrun devicectl device install app --device <device-id> <App.app>`
- 启动 app：`xcrun devicectl device process launch --device <device-id> <bundle-id>`
- 终止进程：`xcrun devicectl device process terminate --device <device-id> --pid <pid>`
- 重启设备：`xcrun devicectl device reboot --device <device-id>`
- 收集 sysdiagnose：`xcrun devicectl device sysdiagnose --device <device-id>`
- 手动配对：`xcrun devicectl manage pair --device <device-id>`
- 解除配对：`xcrun devicectl manage unpair --device <device-id>`

## 真机构建
- Build：`xcodebuild -workspace <workspace> -scheme <scheme> -destination 'id=<device-id>' build`
- Test：`xcodebuild -workspace <workspace> -scheme <scheme> -destination 'id=<device-id>' test`

## 约定
- 优先使用 `connected` 设备；只有用户明确指定时才使用非默认候选。
- `devicectl` 的结构化输出优先使用 `--json-output <path>`；若 JSON 不可用，再回退文本解析。
- 真机构建依赖项目已有签名与开发者配置；签名错误不在本 skill 内修复。
