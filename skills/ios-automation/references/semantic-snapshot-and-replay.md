# Semantic Snapshot and Replay

## Purpose

Use semantic snapshots and replay artifacts to give agents a low-token, repeatable UI feedback loop before falling back to screenshots or raw logs.

## Core Rules

| # | Rule | Why |
| --- | --- | --- |
| 1 | Start with `screen_mapper.py --refs` for UI navigation. | Accessibility text and refs are cheaper and less fragile than pixels. |
| 2 | Treat refs such as `@e1` as snapshot-local. | Element order and availability can change after navigation, scroll, keyboard, alert, or animation. |
| 3 | Refresh the snapshot after every state-changing action. | Prevent stale refs from tapping the wrong element. |
| 4 | Prefer durable selectors for replay specs. | Text and accessibility identifiers survive across sessions better than transient refs. |
| 5 | Capture screenshots/logs only when they add evidence. | Successful smoke flows usually only need concise assertions and artifact paths. |

## Recommended Loop

```bash
# 1. Inspect current screen with low-token refs.
python3 scripts/simulator/screen_mapper.py --refs --max-refs 8 --udid <udid>

# 2. Act on the current snapshot.
python3 scripts/simulator/navigator.py --ref @e1 --tap --udid <udid>

# 3. Refresh before the next action.
python3 scripts/simulator/screen_mapper.py --refs --max-refs 8 --udid <udid>

# 4. Persist a rerunnable flow when the path matters.
python3 scripts/simulator/ui_smoke_runner.py --spec .codex/ui-smoke.yml --udid <udid>
```

## Ref Semantics

```text
@e1 [Button] "Login" center=(320,450)
@e2 [TextField] "Email" center=(320,220)
@e3 [SecureTextField] "Password" center=(320,278)
```

- `@eN` is generated from the latest accessibility tree order.
- `@eN` is useful for immediate same-screen actions.
- Do not store `@eN` as a long-lived selector unless the artifact is explicitly marked exploratory.
- If a ref is stale or missing, refresh with `screen_mapper.py --refs` before retrying.

## UI Smoke Spec Pattern

Prefer `id` or `text` for durable replay:

```yaml
app_bundle_id: com.example.app
flows:
  - name: login-smoke
    steps:
      - action: tap
        target:
          text: Login
        expect:
          text: Email
      - action: set_value
        target:
          id: email-field
        value_env: TEST_EMAIL
        expect:
          value_env: TEST_EMAIL
```

Use `ref` only for short-lived exploratory replay:

```yaml
flows:
  - name: exploratory-current-screen
    steps:
      - action: tap
        target:
          ref: "@e1"
```

## Evidence Bundle

For failures, return only the minimum useful bundle:

```json
{
  "first_failure": "step 2 tap Login timed out waiting for Email",
  "semantic_snapshot": ".codex/ui-smoke-artifacts/current-screen.json",
  "accessibility_excerpt": "Button Login disabled; alert Permission Required visible",
  "screenshot": ".codex/ui-smoke-artifacts/failure.png",
  "app_state": ".codex/ui-smoke-artifacts/app-state.json",
  "logs": ".codex/ui-smoke-artifacts/log-tail.txt"
}
```

## Escalation

- If UI smoke fails because the app cannot build or install, route to `ios-verification` or `xcode-build`.
- If UI smoke reveals crash, hang, leak, or runtime symptoms, route to `debugging`.
- If UI smoke reveals frame drops, memory pressure, or slow launch, route to `ios-performance`.
