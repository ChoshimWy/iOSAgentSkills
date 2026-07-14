# AUCreateProjectAlertView Real Benchmark Case

This is a prepared, real-source reuse/conformance benchmark case for the SidusLinkPro **New Project** alert. The frozen baseline already contains the target component, so this case measures discovery, required reuse, semantic understanding, and necessary visual correction—not greenfield class generation.

- Design source: `SLP_014.sketch`, node `C9A8ED98-5762-4416-B165-ECE0335FE955`.
- Code anchor: `AUCreateProjectAlertView`.
- Fixed state: Fixture View selected, dark appearance, `en_US`, 728 × 471 reference export.
- Variants: screenshot-only, UI IR, UI IR + binding.
- Result status: **not measured**. This bundle proves input readiness only and must not be cited as model-quality or ROI evidence.

From the iOSAgentSkills repository root, materialize and verify the case with:

```bash
python3 skills/design-context-compiler/scripts/prepare_benchmark_case.py \
  skills/design-context-compiler/references/benchmark-cases/au-create-project-alert/benchmark-case.json \
  --output-dir /tmp/iosagent-design-context/benchmarks/au-create-project-alert
```

The command exports the Sketch layer, verifies all immutable hashes, recompiles the Agent Packet, creates a hash-frozen UI-IR-only projection with every code binding removed, and writes three isolated variant input directories.

The generic isolated runner, real Codex executor, independent semantic/visual validator, and machine-specific Run Plan freezer are implemented. The evaluator retains a pinned full checkout, while the provider runs in a separately generated minimal Git worktree containing only the frozen source allowlist. All source/plan repositories, the full checkout, prepared inputs, prior runs, and evaluator-only artifacts are unreadable during provider execution. The provider patch is frozen with external diff, textconv, and rename detection disabled plus full Git object IDs, applied to the full checkout, and accepted only when patch bytes, hash, and changed paths match exactly; this prevents repository-specific attributes, rename heuristics, or abbreviation lengths from changing otherwise identical evidence. The executor exposes only agent-audience inputs and derives usage from one canonical provider JSONL turn; the run plan freezes absolute launcher/native paths, their hashes, and the `@openai/codex/package.json` hash, then invokes the frozen native binary directly rather than resolving Node through the launcher shebang.

The case now freezes a `provider_source_scope` allowlist for the Project domain plus four required image sets. At commit `4cf733453b8ad4a90d9e88f4b633e4c3f1c32a43`, it resolves to 95 files and 1,442,225 bytes with canonical manifest identity `11e0f25f75e8861a84121b9ba4cdb78ae17191699a25d7a7ee2ae162f01ad818`. The 13 `source.code.files` entries remain integrity anchors and do not define visibility. Explicit approval for this exact readable source set, per-variant agent-visible inputs, frozen provider identity, and capture runtime was obtained on 2026-07-14. Regenerate and review the scope identity and obtain new approval if any of those boundaries change. `validation-config.json`, the complete evaluator checkout, capture overlay/runtime/dependency setup, and semantic/visual expected evidence remain evaluator-only and are not model prompt inputs.

The evaluator-only `capture-overlay.patch`, typed iOS Simulator runtime freezer and `capture_adapter.py` are now implemented. The pinned `UnityFramework.xcframework` contains a device arm64 slice and an Intel Simulator slice, but no arm64 Simulator slice. A separate hash-frozen `unityframework-arm64-simulator-stub-v1` evaluator dependency setup now supplies a fail-closed ABI stub only while capture runs, then restores the two touched Pod files and removes the generated slice. The exact UI capture test passed through `codex_verify` on 2026-07-13 and produced a fresh 728 × 471 PNG plus four-region/one-binding Probe. The case remains **not measured** until the three provider variants are executed and independently scored.

Two authorized attempts on 2026-07-14 remain invalid and are not benchmark evidence. The first exposed repository-dependent abbreviated Git object IDs during provider-to-evaluator patch replay; canonical full-index patching now fixes that failure and is covered for tracked and untracked binary output. The second passed replay but capture could not start the shared build-queue daemon because legacy incomplete job directories were interpreted as queued. Dependency setup restored the pinned files before exit. Shared queue recovery requires separate explicit authorization; do not bypass it with an isolated queue or direct `xcodebuild`.

### Project capture prerequisite audit (2026-07-13)

The pinned SidusLinkPro source has one permanent deterministic UI-test launch context, `-AcruxUICueSmoke`, but no provider-visible design-capture route for `AUCreateProjectAlertView`. The evaluator overlay temporarily adds `-AcruxUIDesignCapture`, renders the real view without login/database/network/keyboard/transition dependencies, writes a one-pixel-per-point PNG and raw UIKit hierarchy observations, and adds one exact UI test selector. Existing authenticated project E2E remains excluded.

The smallest trustworthy prerequisite is a DEBUG/test-only fixture delivered as a hash-frozen evaluator `capture-overlay.patch`, not as a permanent change to the provider-visible baseline. The runner freezes its bytes in the evaluator parent process but does not materialize the archived patch in the run directory until after the provider has exited and the implementation patch is frozen; it then applies the overlay only for capture and removes it before semantic/visual validation. The overlay must:

1. is entered by a dedicated launch argument such as `-AcruxUIDesignCapture` plus a frozen scene value `create-project-alert`;
2. constructs `AUCreateProjectAlertView` directly in the `fixture-selected`, dark, `en_US` state without login, database, network, keyboard or transition dependencies;
3. renders the alert content at the frozen 728 × 471 one-pixel-per-point viewport;
4. derives the root, name input, entry-card union and footer-button union frames from the live UIKit hierarchy, including actual class names and accessibility identifiers;
5. writes a project-owned raw capture payload and PNG to its test container, without structure/semantic/visual pass/fail or reference geometry;
6. fails closed when the viewport, region count, runtime identity or output paths differ.

The reviewed capture adapter invokes this temporary fixture only through the hash-frozen `codex_verify` wrapper, verifies the exact Simulator runtime/UDID/name and `simctl` identity, removes stale app data, runs one test selector, retrieves only the two project-owned files, and emits `DCC_ACTUAL_SCREENSHOT` / `DCC_VALIDATOR_PROBE`. It never navigates the authenticated app, synthesizes frames from `validation-config.json`, or calls `xcodebuild` directly. Capture failure, overlay mutation, reverse conflict, restored patch mismatch, runtime drift or cross-run overlay hash drift invalidates the run.

For this pinned baseline, the runtime also freezes an evaluator dependency generator, clang binary, Simulator SDK version/build/settings hash, original XCFramework/CocoaPods copy-script hashes, and deterministic stub product hashes. The stub exports only the compile-time Unity ABI and traps on every Unity entrypoint; therefore the passing capture test is also evidence that the alert fixture did not execute Unity. The generator verifies `LC_BUILD_VERSION=IOSSIMULATOR`, `LC_UUID`, product hashes and deterministic rebuilds. Apply/restore occurs inside the capture adapter's `try/finally`; capture-time mutation or incomplete restoration blocks the run, and the runner's existing post-capture checkout gate provides a second recovery boundary.

Freeze the machine runtime outside the repository:

```bash
python3 skills/design-context-compiler/scripts/create_ios_capture_runtime.py \
  --udid <simulator-udid> \
  --workspace Acrux/Acrux.xcworkspace \
  --scheme Acrux_DEV \
  --test-selector AcruxUITests/AUCreateProjectAlertDesignCaptureUITests/test_fixtureSelected_writesCanonicalCaptureArtifacts \
  --app-bundle-id com.siduslink.cn.Acrux.hd \
  --evaluator-dependency-generator skills/design-context-compiler/scripts/unityframework_simulator_stub.py \
  --source-checkout <clean-pinned-SidusLinkPro-checkout> \
  --unity-xcframework Acrux/Pods/SL3DViewModeKit/SL3DViewModeKit/UnityFramework/UnityFramework.xcframework \
  --unity-pod-copy-script 'Acrux/Pods/Target Support Files/SL3DViewModeKit/SL3DViewModeKit-xcframeworks.sh' \
  --output /tmp/au-create-project-alert-capture-runtime.json
```

```bash
python3 skills/design-context-compiler/scripts/create_benchmark_run_plan.py \
  skills/design-context-compiler/references/benchmark-cases/au-create-project-alert/benchmark-case.json \
  --capture-adapter skills/design-context-compiler/references/benchmark-cases/au-create-project-alert/capture_adapter.py \
  --capture-overlay skills/design-context-compiler/references/benchmark-cases/au-create-project-alert/capture-overlay.patch \
  --capture-runtime /tmp/au-create-project-alert-capture-runtime.json \
  --codex-launcher <absolute-@openai/codex-bin/codex.js> \
  --model <frozen-model-id> \
  --reasoning high \
  --output skills/design-context-compiler/references/benchmark-cases/au-create-project-alert/measured-run-plan.local.json
```

Then execute from the repository root with the generated `evidence_status: measured` plan:

```bash
python3 skills/design-context-compiler/scripts/run_benchmark.py \
  skills/design-context-compiler/references/benchmark-cases/au-create-project-alert/measured-run-plan.local.json \
  --workspace-root . \
  --output-dir /tmp/iosagent-design-context/runs/au-create-project-alert
```

The runner re-prepares measured inputs, creates three full evaluator checkouts and three minimal provider worktrees from the pinned commit, archives the plan/case/executor/capture/validator/input context and all phase logs, rechecks both Git boundaries and frozen inputs after every phase, freezes and replays implementation patches, freezes capture evidence before validation, and invokes the scorer. The standalone scorer independently recomputes the source manifest canonical identity, baseline tree entries, detached HEAD, exact object closure, Git metadata fingerprint, actual filesystem scope, provider patch, evaluator patch, binding identity, source declarations, anchors, PNG pixel ratios, provider usage, repair events and manual time. It does not rely on `git status` for scope enforcement. All three runs must share one explicit source-scope identity, one plan, and all adapter identities. Do not add `--allow-synthetic` to a real run. Actual model runs and `benchmark-v1` measured results remain a later step.

The source repository may advance after the case is frozen: preparation verifies that the declared commit still exists and that every referenced worktree file matches that commit. The eventual three-run benchmark must create each isolated run from the declared `code_baseline_commit`, never from whichever `HEAD` happens to be current.
