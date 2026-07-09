---
name: gitnexus-refactoring
description: "Use when the user wants to rename, extract, split, move, or restructure code safely. Examples: \"Rename this function\", \"Extract this into a module\", \"Refactor this class\", \"Move this to a separate file\""
---

# Refactoring with GitNexus

## Purpose

Use GitNexus to plan and validate safe rename, extract, split, move, or other structural refactors.

## Agent Rules

- Start from GitNexus context/freshness when using MCP graph data; stale or missing indexes are evidence gaps, not current facts.
- Prefer bounded MCP/resource reads and targeted source-file confirmation over broad recursive scans or large raw dumps.
- If indexing is required, run or suggest the project-local `node .gitnexus/run.cjs analyze` path from the repo root; use `--pdg` only when PDG/taint data is needed.
- Treat GitNexus output as navigation and impact evidence; confirm correctness-sensitive conclusions against the current worktree before reporting.

## Inputs

```json
{
  "goal": "refactor target, desired new shape/name, repo name, optional dry-run preference.",
  "repo": "optional repository name or current repo",
  "constraints": []
}
```

## When to Use

- "Rename this function safely"
- "Extract this into a module"
- "Split this service"
- "Move this to a new file"
- Any task involving renaming, extracting, splitting, or restructuring code

## Workflow

```
1. impact({target: "X", direction: "upstream"})  → Map all dependents
2. query({search_query: "X"})                            → Find execution flows involving X
3. context({name: "X"})                           → See all incoming/outgoing refs
4. Plan update order: interfaces → implementations → callers → tests
```

> If "Index is stale" → run `node .gitnexus/run.cjs analyze` in terminal.

## Checklists

### Rename Symbol

```
- [ ] rename({symbol_name: "oldName", new_name: "newName", dry_run: true}) — preview all edits
- [ ] Review graph edits (high confidence) and text_search edits (review carefully)
- [ ] If satisfied: rename({..., dry_run: false}) — apply edits
- [ ] detect_changes() — verify only expected files changed
- [ ] Run tests for affected processes
```

### Extract Module

```
- [ ] context({name: target}) — see all incoming/outgoing refs
- [ ] impact({target, direction: "upstream"}) — find all external callers
- [ ] Define new module interface
- [ ] Extract code, update imports
- [ ] detect_changes() — verify affected scope
- [ ] Run tests for affected processes
```

### Split Function/Service

```
- [ ] context({name: target}) — understand all callees
- [ ] Group callees by responsibility
- [ ] impact({target, direction: "upstream"}) — map callers to update
- [ ] Create new functions/services
- [ ] Update callers
- [ ] detect_changes() — verify affected scope
- [ ] Run tests for affected processes
```

## Tools

**rename** — automated multi-file rename:

```
rename({symbol_name: "validateUser", new_name: "authenticateUser", dry_run: true})
→ 12 edits across 8 files
→ 10 graph edits (high confidence), 2 text_search edits (review)
→ Changes: [{file_path, edits: [{line, old_text, new_text, confidence}]}]
```

**impact** — map all dependents first:

```
impact({target: "validateUser", direction: "upstream"})
→ d=1: loginHandler, apiMiddleware, testUtils
→ Affected Processes: LoginFlow, TokenRefresh
```

**detect_changes** — verify your changes after refactoring:

```
detect_changes({scope: "all"})
→ Changed: 8 files, 12 symbols
→ Affected processes: LoginFlow, TokenRefresh
→ Risk: MEDIUM
```

**cypher** — custom reference queries:

```cypher
MATCH (caller)-[:CodeRelation {type: 'CALLS'}]->(f:Function {name: "validateUser"})
RETURN caller.name, caller.filePath ORDER BY caller.filePath
```

## Risk Rules

| Risk Factor         | Mitigation                                |
| ------------------- | ----------------------------------------- |
| Many callers (>5)   | Use rename for automated updates |
| Cross-area refs     | Use detect_changes after to verify scope  |
| String/dynamic refs | query to find them               |
| External/public API | Version and deprecate properly            |

## Example: Rename `validateUser` to `authenticateUser`

```
1. rename({symbol_name: "validateUser", new_name: "authenticateUser", dry_run: true})
   → 12 edits: 10 graph (safe), 2 text_search (review)
   → Files: validator.ts, login.ts, middleware.ts, config.json...

2. Review text_search edits (config.json: dynamic reference!)

3. rename({symbol_name: "validateUser", new_name: "authenticateUser", dry_run: false})
   → Applied 12 edits across 8 files

4. detect_changes({scope: "all"})
   → Affected: LoginFlow, TokenRefresh
   → Risk: MEDIUM — run tests for these flows
```

## Outputs

```json
{
  "status": "completed | partial | blocked | skipped",
  "summary": [],
  "refactor_plan": [],
  "known_risks": [],
  "next_action": "apply-refactor | targeted-validation | ask-user | blocked"
}
```
## Exit Conditions

- `completed`: GitNexus evidence or command guidance is sufficient for the requested task.
- `partial`: useful findings are available, but freshness, ambiguity, or missing source confirmation remains.
- `blocked`: the repo is not indexed, required tools are unavailable, or the request cannot proceed safely without user input.
- `skipped`: GitNexus is not applicable after checking the task scope.
## Escalation Rules

- Escalate to `gitnexus-cli` when the index must be created, refreshed, cleaned, or checked.
- Escalate to source-code reading whenever graph output is stale, ambiguous, or correctness-critical.
- Escalate to implementation, verification, debugging, or review Skills when the task moves beyond GitNexus navigation/evidence.
## Relationship to Other Skills

Use for graph-guided refactor planning; switch to implementation skills for actual Apple/iOS code edits and tests.
## Token Budget

- Do not paste large raw graph dumps, full diffs, or complete logs.
- Prefer repo context, specific tool results, and short source slices.
- Summarize findings with file paths, symbols, confidence/risk, and the next action.
