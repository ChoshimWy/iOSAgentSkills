# Low-Token iOS Verification Workflow

本文档说明如何把现有 `build-queue daemon` 升级为低 token、低重复编译的 iOS 验证闭环。

## 目标

- 减少不必要的 `xcodebuild` 请求。
- 避免多 Agent 重复验证同一 diff。
- 避免 Codex / Claude Code 读取完整构建日志。
- 让 Agent 优先消费结构化 `diagnostics.json`。
- 默认只跑最窄验证面，按需升级 full verification。

## 推荐链路

```text
Agent
  ↓
ios-verification-router
  ↓
ios-affected-tests
  ↓
codex_verify.sh / ~/.codex/bin/codex_verify
  ↓
build-queue daemon
  ↓
xcodebuild
  ↓
digest-xcodebuild-log.sh
  ↓
diagnostics.json / build-summary.txt
  ↓
ios-build-log-digest
  ↓
Agent fixes first blocking error only
```

## 新增 Skills

### `ios-verification-router`

验证请求前置路由：根据 diff 类型选择 `none` / `lint` / `typecheck` / `build` / `unit` / `ui` / `full`。

核心规则：

- 不直接运行 `xcodebuild`。
- 默认不请求 full verification。
- 优先使用目标项目 `./codex_verify.sh`。
- 无项目 wrapper 时回退 `~/.codex/bin/codex_verify`。
- 同一 fingerprint 已失败时优先读取缓存诊断。

### `ios-affected-tests`

根据变更文件推导最小 `-only-testing` 集合。

核心规则：

- ViewModel 改动优先找 `*ViewModelTests`。
- Service 改动优先找 `*ServiceTests`。
- StoreKit / Subscription 改动优先找购买、订阅、receipt 相关测试。
- 无低成本测试时输出 `no_test_reason`，不要自动升级到 full test。

### `ios-build-log-digest`

构建失败后只读取摘要，不读取原始日志。

核心规则：

- 优先读取 `diagnostics.json`。
- 其次读取 `build-summary.txt`。
- 默认禁止读取完整 `build.log`。
- 默认禁止读取完整 `.xcresult` dump。
- 只修第一个真实 blocking error。

## Daemon 输出规范

建议 build-queue daemon 每次验证后输出：

```text
build-results/latest/
  diagnostics.json
  build-summary.txt
  test-summary.json
```

`diagnostics.json` 应遵守：

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
tools/digest-xcodebuild-log.sh build.log diagnostics.json build-summary.txt
```

典型集成：

```bash
set -o pipefail
xcodebuild ... 2>&1 | tee build.log
status=$?
tools/digest-xcodebuild-log.sh build.log diagnostics.json build-summary.txt
exit $status
```

## Agent 交付格式

建议 Agent 汇报验证时使用紧凑格式：

```text
Verification route: affected unit tests + build
Reason: SubscriptionService and PurchaseViewModel changed.
Full build: skipped; no project/dependency config changed.
Log policy: diagnostics.json only.
```

失败时：

```text
Verification failed.
First blocking error: PurchaseViewModel.swift:82 cannot find `productID` in scope.
Next action: fix this error only, then request verification again.
Raw log: skipped by policy.
```
