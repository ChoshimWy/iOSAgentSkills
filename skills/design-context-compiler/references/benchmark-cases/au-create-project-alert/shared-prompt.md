# Shared implementation prompt

Bring the supplied **New Project** alert slice into visual and semantic conformance as production UIKit code in the provided SidusLinkPro baseline. This is a reuse/conformance task, not a greenfield class-generation task.

Constraints:

1. Match the supplied visual reference and fixed benchmark state.
2. Preserve existing project architecture, localization, subscription behavior, accessibility identifiers, and minimum OS.
3. Inspect the existing code before editing. Reuse an existing component when it already owns this UI, and never create a duplicate replacement for a required mapping.
4. Avoid unrelated refactors and do not change the benchmark input files.
5. If the baseline already satisfies a requirement, preserve it instead of manufacturing a diff. Report changed files, component reuse, remaining unknowns, and validation performed.

The evaluator will use the same viewport, state, locale, code baseline, validation configuration, and repair policy for every variant. Do not infer additional requirements from the variant name.
