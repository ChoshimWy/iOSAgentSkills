---
name: gitnexus-impact-analysis
description: "Use when the user wants to know what will break if they change something, or needs safety analysis before editing code. Examples: \"Is it safe to change X?\", \"What depends on this?\", \"What will break?\""
---

# Impact Analysis with GitNexus

## Purpose

Use GitNexus to estimate blast radius, upstream/downstream dependencies, affected flows, and test impact for proposed or current changes.

## Agent Rules

- Start from GitNexus context/freshness when using MCP graph data; stale or missing indexes are evidence gaps, not current facts.
- Prefer bounded MCP/resource reads and targeted source-file confirmation over broad recursive scans or large raw dumps.
- If indexing is required, run or suggest the project-local `node .gitnexus/run.cjs analyze` path from the repo root; use `--pdg` only when PDG/taint data is needed.
- Treat GitNexus output as navigation and impact evidence; confirm correctness-sensitive conclusions against the current worktree before reporting.

## Inputs

```json
{
  "goal": "target symbol/file/route, current diff scope, direction, repo name, optional risk threshold.",
  "repo": "optional repository name or current repo",
  "constraints": []
}
```

## When to Use

- "Is it safe to change this function?"
- "What will break if I modify X?"
- "Show me the blast radius"
- "Who uses this code?"
- Before making non-trivial code changes
- Before committing — to understand what your changes affect

## Workflow

```
1. impact({target: "X", direction: "upstream"})  → What depends on this
2. READ gitnexus://repo/{name}/processes                   → Check affected execution flows
3. detect_changes()                               → Map current git changes to affected flows
4. Assess risk and report to user
```

> If "Index is stale" → run `node .gitnexus/run.cjs analyze` in terminal.

## Checklist

```
- [ ] impact({target, direction: "upstream"}) to find dependents
- [ ] Review d=1 items first (these WILL BREAK)
- [ ] Check high-confidence (>0.8) dependencies
- [ ] READ processes to check affected execution flows
- [ ] detect_changes() for pre-commit check
- [ ] Assess risk level and report to user
```

## Understanding Output

| Depth | Risk Level       | Meaning                  |
| ----- | ---------------- | ------------------------ |
| d=1   | **WILL BREAK**   | Direct callers/importers |
| d=2   | LIKELY AFFECTED  | Indirect dependencies    |
| d=3   | MAY NEED TESTING | Transitive effects       |

## Risk Assessment

| Affected                       | Risk     |
| ------------------------------ | -------- |
| <5 symbols, few processes      | LOW      |
| 5-15 symbols, 2-5 processes    | MEDIUM   |
| >15 symbols or many processes  | HIGH     |
| Critical path (auth, payments) | CRITICAL |

## Tools

**impact** — the primary tool for symbol blast radius:

```
impact({
  target: "validateUser",
  direction: "upstream",
  minConfidence: 0.8,
  maxDepth: 3
})

→ d=1 (WILL BREAK):
  - loginHandler (src/auth/login.ts:42) [CALLS, 100%]
  - apiMiddleware (src/api/middleware.ts:15) [CALLS, 100%]

→ d=2 (LIKELY AFFECTED):
  - authRouter (src/routes/auth.ts:22) [CALLS, 95%]
```

**detect_changes** — git-diff based impact analysis:

```
detect_changes({scope: "staged"})

→ Changed: 5 symbols in 3 files
→ Affected: LoginFlow, TokenRefresh, APIMiddlewarePipeline
→ Risk: MEDIUM
```

## Example: "What breaks if I change validateUser?"

```
1. impact({target: "validateUser", direction: "upstream"})
   → d=1: loginHandler, apiMiddleware (WILL BREAK)
   → d=2: authRouter, sessionManager (LIKELY AFFECTED)

2. READ gitnexus://repo/my-app/processes
   → LoginFlow and TokenRefresh touch validateUser

3. Risk: 2 direct callers, 2 processes = MEDIUM
```

## Outputs

```json
{
  "status": "completed | partial | blocked | skipped",
  "summary": [],
  "impact_summary": [],
  "known_risks": [],
  "next_action": "read-source | targeted-validation | code-review | blocked"
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

Use before non-trivial edits or before review/commit when graph impact can reduce manual scanning.
## Token Budget

- Do not paste large raw graph dumps, full diffs, or complete logs.
- Prefer repo context, specific tool results, and short source slices.
- Summarize findings with file paths, symbols, confidence/risk, and the next action.
