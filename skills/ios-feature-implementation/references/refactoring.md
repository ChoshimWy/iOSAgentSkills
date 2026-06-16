# Refactoring Mode Reference

Use this reference when `ios-feature-implementation` selects `refactor` mode.

## Scope

- Long methods, duplicated logic, deep nesting, callback-heavy flows, and God Object decomposition.
- Behavior-preserving structure changes, extraction seams, dependency injection, and readability cleanup.
- SwiftUI-specific view decomposition still uses `swiftui` mode inside the same unified implementation Skill.

## Rules

- Preserve behavior by default; do not mix unrelated feature work into a refactor.
- Move in small steps and keep rollback scope obvious.
- Prefer seams that improve ownership, testability, and readability without over-abstracting.
- Keep public API documentation, concurrency notes, side-effect comments, and failure semantics current on touched code.
- If behavior changes become necessary, reclassify the work as feature implementation and report the contract change explicitly.

## Output Focus

Report `refactoring_patterns`, changed ownership boundaries, behavior-preservation evidence, `test_impact` or `no_test_reason`, and residual risk.
