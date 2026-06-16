# Low-Token iOS Verification Workflow

本文档说明如何把现有 `build-queue daemon` 升级为低 token、低重复编译的 iOS 验证闭环。

## 目标

- 减少不必要的 `xcodebuild` 请求。
- 避免多 Agent 重复验证同一 diff。
- 避免 Codex / Claude Code 读取完整构建日志。
- 让 Agent 优先消费脚本生成的结构化 `verification-report.json`，再按需读取 `diagnostics.json`。
- 默认只跑最窄验证面，按需升级 full verification。

## 推荐链路

```text
Agent
  ↓
ios-verification(route / affected-tests)
  ↓
codex_verify.sh / ~/.codex/bin/codex_verify
  ↓
build-queue daemon
  ↓
xcodebuild
  ↓
verification-report.json / diagnostics.json / build-summary.txt
  ↓
ios-verification(digest / final-gate)
  ↓
Agent fixes first blocking error only or accepts evidence
```

## 统一 Skill

### `ios-verification`

`ios-verification` 统一承接原先分散的验证前路由、受影响测试选择、项目环境执行、失败摘要和最终证据裁决。内部模式：

- `route`：根据 diff 类型选择 `none` / `lint` / `typecheck` / `build` / `unit` / `ui` / `full`。
- `affected-tests`：根据变更文件推导最小 `-only-testing` 集合。
- `execute`：通过 `codex_verify.sh` / `~/.codex/bin/codex_verify` 接入 build-queue daemon 执行验证。
- `digest`：优先读取 `verification-report.json`，其次读取 `diagnostics.json`、`build-summary.txt`，只定位第一个真实 blocking error。
- `final-gate`：在定向验证 / `no_test_reason` 与独立 `code-review` 后判断证据是否足够。

核心规则：

- 不直接运行裸 `xcodebuild`。
- 默认不请求 full verification。
- 优先使用目标项目 `./codex_verify.sh`。
- 无项目 wrapper 时回退 `~/.codex/bin/codex_verify`。
- 同一 fingerprint 已失败时优先读取缓存诊断。
- 无低成本测试时输出 `no_test_reason`，不要自动升级到 full test。
- 默认禁止读取完整 `build.log` 和完整 `.xcresult` dump。

## Daemon 输出规范

建议 build-queue daemon 每次验证后输出：

```text
build-results/latest/
  verification-report.json
  diagnostics.json
  build-summary.txt
  test-summary.json
```

`verification-report.json` 是 Agent 默认入口，最小字段：

```json
{
  "status": "failed",
  "mode": "unit",
  "fingerprint": "abc123",
  "cached": false,
  "summary": "swift_compile_error: App/File.swift:82 cannot find 'productID' in scope",
  "first_blocking_error": {
    "kind": "swift_compile_error",
    "file": "App/File.swift",
    "line": 82,
    "message": "Cannot find 'productID' in scope"
  },
  "failed_tests": [],
  "warnings_count": 0,
  "artifact_paths": {
    "diagnostics_json": "build-results/latest/diagnostics.json",
    "build_summary": "build-results/latest/build-summary.txt",
    "raw_log": "build-results/latest/build.log"
  },
  "suggested_next_action": "Fix the first real blocking error only, then request verification again.",
  "raw_log_policy": "forbidden_by_default",
  "needs_raw_log": false
}
```

`diagnostics.json` 是二级结构化明细，应遵守：

```text
daemon/diagnostics.schema.json
```

最小字段：

```json
{
  "status": "failed",
  "mode": "build",
  "fingerprint": "abc123",
  "cached": false,
  "summary": "Swift compiler error in PurchaseViewModel.swift:82",
  "diagnostics": [
    {
      "kind": "swift_compile_error",
      "severity": "error",
      "file": "App/Subscription/PurchaseViewModel.swift",
      "line": 82,
      "column": 17,
      "message": "Cannot find 'productID' in scope"
    }
  ],
  "next_action": "Fix the first real compiler error only, then request verification again.",
  "raw_log_policy": "forbidden_by_default"
}
```

## 日志摘要脚本

脚本位置：

```bash
tools/digest-xcodebuild-log.sh
```

用法：

```bash
tools/digest-xcodebuild-log.sh build.log diagnostics.json build-summary.txt verification-report.json
```

典型集成：

```bash
set -o pipefail
xcodebuild ... 2>&1 | tee build.log
status=$?
tools/digest-xcodebuild-log.sh build.log diagnostics.json build-summary.txt verification-report.json
exit $status
```

安装脚本会同步：

```bash
~/.codex/bin/codex_verify
~/.codex/bin/digest-xcodebuild-log
```

`codex_verify` 默认只把 `verification-report.json` 打印回 Agent。若必须观察实时 raw log，显式设置：

```bash
CODEX_VERIFY_STREAM_LOG=1
```

## Agent 交付格式

建议 Agent 汇报验证时使用紧凑格式：

```text
Verification route: affected unit tests + build
Reason: SubscriptionService and PurchaseViewModel changed.
Full build: skipped; no project/dependency config changed.
Log policy: verification-report.json only.
```

失败时：

```text
Verification failed.
First blocking error: PurchaseViewModel.swift:82 cannot find `productID` in scope.
Next action: fix this error only, then request verification again.
Raw log: skipped by policy.
```
