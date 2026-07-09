---
name: gitnexus-debugging
description: "Use when the user is debugging a bug, tracing an error, or asking why something fails. Examples: \"Why is X failing?\", \"Where does this error come from?\", \"Trace this bug\""
---

# Debugging with GitNexus

## Purpose

Use GitNexus code intelligence to trace bugs, failures, suspicious call paths, and runtime symptoms before confirming root cause in source files.

## Agent Rules

- Start from GitNexus context/freshness when using MCP graph data; stale or missing indexes are evidence gaps, not current facts.
- Prefer bounded MCP/resource reads and targeted source-file confirmation over broad recursive scans or large raw dumps.
- If indexing is required, run or suggest the project-local `node .gitnexus/run.cjs analyze` path from the repo root; use `--pdg` only when PDG/taint data is needed.
- Treat GitNexus output as navigation and impact evidence; confirm correctness-sensitive conclusions against the current worktree before reporting.

## Inputs

```json
{
  "goal": "symptom/error text, suspect symbol/file, repo name, optional logs or reproduction notes.",
  "repo": "optional repository name or current repo",
  "constraints": []
}
```

## When to Use

- "Why is this function failing?"
- "Trace where this error comes from"
- "Who calls this method?"
- "This endpoint returns 500"
- Investigating bugs, errors, or unexpected behavior

## Workflow

```
1. query({search_query: "<error or symptom>"})            → Find related execution flows
2. context({name: "<suspect>"})                    → See callers/callees/processes
3. READ gitnexus://repo/{name}/process/{name}                → Trace execution flow
4. cypher({statement: "MATCH path..."})                 → Custom traces if needed
```

> If "Index is stale" → run `node .gitnexus/run.cjs analyze` in terminal.

## Checklist

```
- [ ] Understand the symptom (error message, unexpected behavior)
- [ ] query for error text or related code
- [ ] Identify the suspect function from returned processes
- [ ] context to see callers and callees
- [ ] Trace execution flow via process resource if applicable
- [ ] cypher for custom call chain traces if needed
- [ ] Read source files to confirm root cause
```

## Debugging Patterns

| Symptom              | GitNexus Approach                                          |
| -------------------- | ---------------------------------------------------------- |
| Error message        | `query` for error text → `context` on throw sites |
| Wrong return value   | `context` on the function → trace callees for data flow    |
| Intermittent failure | `context` → look for external calls, async deps            |
| Performance issue    | `context` → find symbols with many callers (hot paths)     |
| Recent regression    | `detect_changes` to see what your changes affect           |
| "How does A reach B?" | `trace` between the two symbols — shortest call chain in one call |

## Tools

**query** — find code related to error:

```
query({search_query: "payment validation error"})
→ Processes: CheckoutFlow, ErrorHandling
→ Symbols: validatePayment, handlePaymentError, PaymentException
```

**context** — full context for a suspect:

```
context({name: "validatePayment"})
→ Incoming calls: processCheckout, webhookHandler
→ Outgoing calls: verifyCard, fetchRates (external API!)
→ Processes: CheckoutFlow (step 3/7)
```

**cypher** — custom call chain traces:

```cypher
MATCH path = (a)-[:CodeRelation {type: 'CALLS'}*1..2]->(b:Function {name: "validatePayment"})
RETURN [n IN nodes(path) | n.name] AS chain
```

**trace** — shortest call chain between two symbols ("how does A reach B?"), one call instead of chaining `context` hops:

```
trace({ from: "processCheckout", to: "fetchRates" })
→ status: ok, hopCount: 3
→ hops: processCheckout → validatePayment → verifyCard → fetchRates
→ edges: CALLS (1.0), CALLS (0.95), CALLS (1.0)
```

When no path exists, `trace` reports the furthest reachable node — exactly where the chain breaks (dynamic dispatch, reflection, or an external boundary).

## Example: "Payment endpoint returns 500 intermittently"

```
1. query({search_query: "payment error handling"})
   → Processes: CheckoutFlow, ErrorHandling
   → Symbols: validatePayment, handlePaymentError

2. context({name: "validatePayment"})
   → Outgoing calls: verifyCard, fetchRates (external API!)

3. READ gitnexus://repo/my-app/process/CheckoutFlow
   → Step 3: validatePayment → calls fetchRates (external)

4. Root cause: fetchRates calls external API without proper timeout
```

## Outputs

```json
{
  "status": "completed | partial | blocked | skipped",
  "summary": [],
  "suspects": [],
  "known_risks": [],
  "next_action": "read-source | fix-with-implementation-skill | ask-user | blocked"
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

Use before `debugging` or implementation when a GitNexus index can cheaply narrow the search space; switch to source/log inspection for final proof.
## Token Budget

- Do not paste large raw graph dumps, full diffs, or complete logs.
- Prefer repo context, specific tool results, and short source slices.
- Summarize findings with file paths, symbols, confidence/risk, and the next action.
