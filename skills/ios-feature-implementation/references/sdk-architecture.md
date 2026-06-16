# SDK / Framework Architecture Reference

Use this reference only for `ios-feature-implementation` with `sdk-contract` mode when SDK / Framework architecture, public API, distribution, or version evolution is central to the task.

## Scope

Covers:
- SDK / Framework layer boundaries and dependency direction.
- Public/open API design.
- Entry types, initialization, shutdown, and lifecycle ownership.
- Configuration / Options / Environment design.
- Error, logging, metrics, callbacks, delegates, closures, and async streams.
- Mock / Stub / Fake seams.
- SPM / XCFramework / CocoaPods distribution strategy.
- SemVer, deprecation, and breaking-change strategy.

Does not cover:
- Xcode signing, archive/export, build-script, or CI mechanics; route those to `xcode-build`.
- Runtime crash/leak/hang diagnosis; route those to `debugging`.
- Pure test implementation; use `test-implementation` mode in `ios-feature-implementation`.

## Architecture Rules

- Expose the minimum necessary public API.
- Keep implementation details internal.
- Default dependency direction: `Public API Layer -> Feature Layer -> Core Layer -> Platform Layer`.
- Public API layer should not depend on concrete platform implementation details.
- Entry types own initialization, lifecycle, configuration validation, and high-level coordination only.
- Do not put business implementation detail into the entry type.
- Keep side effects explicit and observable.
- Prefer dependency injection over hidden singletons.

## API Design Rules

- Public/open APIs must include `///` documentation.
- Public APIs must define input, output, error, concurrency, side-effect, and availability semantics.
- Breaking changes must be explicit and paired with a version strategy.
- Avoid leaking implementation types through public signatures.
- Prefer stable value types for configuration.
- Keep callbacks, async streams, delegates, and closures lifecycle-safe.

## Distribution Rules

- Prefer SPM source distribution unless binary distribution is required.
- Use XCFramework for binary distribution.
- Document platform and architecture support.
- Document resource bundling strategy.
- Document sample app or integration test strategy.
- Versioning should follow SemVer.
- Keep signing/archive/export/CI details in `xcode-build`; this reference only sets architecture strategy.

## Testability Rules

- Define seams for network, persistence, BLE, device, clock, queue, logger, metrics, and transport dependencies.
- Provide mock/stub/fake protocols where they improve deterministic tests.
- Do not over-abstract single-use internal implementation.
- SDK APIs should be testable without requiring real devices unless the capability inherently requires hardware.

## Output Focus

When this reference is active, include only applicable fields in the Skill output:

- `public_api_surface`
- `module_boundaries`
- `dependency_direction`
- `entry_points`
- `configuration_model`
- `testability_plan`
- `distribution_plan`
- `versioning_plan`
- `known_risks`
- `test_impact` or `no_test_reason`

## Escalation Notes

- Use `advanced-swift` as a secondary mode when complex generics, actor isolation, `Sendable`, type erasure, or availability strategy drives implementation details.
- Use `test-implementation` mode when test seams, mocks, integration tests, or coverage strategy need implementation.
- Escalate to `xcode-build` when SPM/XCFramework/build/signing/archive/export/CI mechanics become the main task.
- Escalate to `apple-docs` when official availability or API behavior must be verified.
