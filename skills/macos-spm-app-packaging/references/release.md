# 发布与公证说明

## 公证前提
- 安装 Xcode Command Line Tools，以便使用 `xcrun` 和 `notarytool`。
- 准备 App Store Connect API 凭证：
  - `APP_STORE_CONNECT_API_KEY_P8`
  - `APP_STORE_CONNECT_KEY_ID`
  - `APP_STORE_CONNECT_ISSUER_ID`
- 在 `APP_IDENTITY` 中配置 `Developer ID Application` 身份。

## Sparkle appcast（可选）
- 安装 Sparkle 工具，确保 `generate_appcast` 在 PATH 中。
- 提供 `SPARKLE_PRIVATE_KEY_FILE`（`ed25519` 私钥）。
- appcast 脚本会基于打包产物生成更新后的 `appcast.xml`。
- Sparkle 通过 `sparkle:version` 比较版本，该值通常来自 `CFBundleVersion`，因此每次发布都要提升 `BUILD_NUMBER`。

## Tag 与 GitHub Release（可选）
如果通过 GitHub Releases 分发 zip 或 appcast，建议使用语义化 tag 并显式发布 release。

示例流程：

```bash
git tag v<version>
git push origin v<version>

gh release create v<version> CodexBar-<version>.zip appcast.xml \
  --title "AppName <version>" \
  --notes-file CHANGELOG.md
```

注意事项：
- 如果 appcast 通过 GitHub Releases 或 raw URL 分发，必须确保 release 已发布且资源可访问，避免出现 `404`。
- 发布说明优先使用整理过的版本文案，不要直接倾倒完整 changelog。
