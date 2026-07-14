# Benchmark Capture Adapter Protocol v1

## Purpose

A measured capture adapter is the case-specific trust boundary between the implemented iOS checkout and the independent semantic/visual validator. It must observe a real rendered state; it must not derive acceptance results.

## Frozen invocation

The Run Plan must reference the adapter by path and SHA-256, and `validator.capture_command[0]` must be `{capture}`. The runner supplies the Python runtime and these authoritative environment values:

- `DCC_EVIDENCE_STATUS=measured`
- `DCC_CASE_ID`, `DCC_VARIANT`
- `DCC_WORKTREE`, `DCC_RUN_DIR`
- `DCC_INPUT_CONTEXT`
- `DCC_ACTUAL_SCREENSHOT`
- `DCC_VALIDATOR_PROBE`
- `DCC_VALIDATOR_ID`
- `DCC_CAPTURE_ADAPTER_SHA256`

The adapter may read the checkout and validator-audience `validation-config.json`. It must not mutate provider implementation files, frozen inputs, `run-observation.json`, plan, case, or any prior run. A Run Plan may explicitly freeze one evaluator-only dependency setup needed solely to make the pinned baseline buildable; this exception follows the temporary setup contract below and is not provider output.

## Exact outputs

The adapter must create exactly two capture-owned artifacts:

1. `actual.png`: canonical one-pixel-per-point PNG matching the frozen viewport.
2. `validator-probe.json`: valid `benchmark-validator-probe-v1` containing:
   - screenshot path/hash;
   - viewport, scale, appearance and locale;
   - every required region in frozen order with runtime frame, runtime type, accessibility identifier, visibility, parent id and ordered child ids;
   - only bindings actually observed at runtime, with frozen binding id, region id and runtime type.

It must not create structure/semantic pass/fail, Semantic Evidence, Visual Diff, Run Result, scores, thresholds, or other acceptance summaries. Those belong to the independent validator and scorer.

## iOS implementation requirements

- Open a deterministic PreviewScene, snapshot test host, or project-owned debug route for the exact benchmark state.
- Freeze OS/SDK/device/destination, locale, appearance, Dynamic Type, animations and time-dependent data.
- Produce region frames and runtime binding identity from app/test instrumentation or accessibility/runtime inspection, not from the reference geometry copied into the adapter.
- A source declaration or registry entry is not runtime observation.
- Follow the target project's Xcode verification policy. Do not hide an ad hoc direct `xcodebuild` call inside the adapter; use the project-owned verification/capture entrypoint and shared queue where required.
- Fail closed if the app cannot reach the state, a region is missing, the viewport differs, or runtime identity is ambiguous.

## Temporary evaluator dependency setup

Use this only when a frozen baseline dependency cannot support the frozen capture destination and the target UI does not exercise that dependency.

- Declare the setup inside the typed capture runtime; freeze generator, compiler, SDK version/build/settings, baseline inputs and generated product hashes.
- Keep the generator in the reviewed evaluator repository and hidden from the provider with the rest of evaluator evidence.
- Apply only after the provider implementation patch is frozen and only inside the capture adapter.
- Touch only the declared dependency integration files; never patch target UI or business implementation.
- Make unsupported runtime entrypoints fail closed so a passing capture proves the fixture did not consume the shimmed subsystem.
- Verify platform load commands, deterministic output and exact hashes before invoking the project test.
- Restore in `finally`, reject capture-time mutation, verify original hashes and remove every generated file before returning to the runner.
- Treat setup, capture or restore failure as a blocked run. The runner must still recheck the entire pinned checkout and recover only inside the isolated checkout.

## Ownership gate

After capture, the runner freezes hashes for `actual.png` and `validator-probe.json`, rechecks the pinned checkout and inputs, and rejects any validator that modifies either file. The scorer independently verifies adapter identity, Probe linkage, runtime binding contracts, geometry anchors and pixel difference ratios.
