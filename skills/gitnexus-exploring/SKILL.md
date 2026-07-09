---
name: gitnexus-exploring
description: "Use when the user asks how code works, wants to understand architecture, trace execution flows, or explore unfamiliar parts of the codebase. Examples: \"How does X work?\", \"What calls this function?\", \"Show me the auth flow\""
---

# Exploring Codebases with GitNexus

## Purpose

Use GitNexus to understand unfamiliar code structure, execution flows, clusters, and symbol relationships with low token cost.

## Agent Rules

- Start from GitNexus context/freshness when using MCP graph data; stale or missing indexes are evidence gaps, not current facts.
- Prefer bounded MCP/resource reads and targeted source-file confirmation over broad recursive scans or large raw dumps.
- If indexing is required, run or suggest the project-local `node .gitnexus/run.cjs analyze` path from the repo root; use `--pdg` only when PDG/taint data is needed.
- Treat GitNexus output as navigation and impact evidence; confirm correctness-sensitive conclusions against the current worktree before reporting.

## Inputs

```json
{
  "goal": "concept/question, repo name, optional symbol/file/process name.",
  "repo": "optional repository name or current repo",
  "constraints": []
}
```

## When to Use

- "How does authentication work?"
- "What's the project structure?"
- "Show me the main components"
- "Where is the database logic?"
- Understanding code you haven't seen before

## Workflow

```
1. READ gitnexus://repos                          → Discover indexed repos
2. READ gitnexus://repo/{name}/context             → Codebase overview, check staleness
3. query({search_query: "<what you want to understand>"})  → Find related execution flows
4. context({name: "<symbol>"})            → Deep dive on specific symbol
5. READ gitnexus://repo/{name}/process/{name}      → Trace full execution flow
```

> If step 2 says "Index is stale" → run `node .gitnexus/run.cjs analyze` in terminal.

## Checklist

```
- [ ] READ gitnexus://repo/{name}/context
- [ ] query for the concept you want to understand
- [ ] Review returned processes (execution flows)
- [ ] context on key symbols for callers/callees
- [ ] READ process resource for full execution traces
- [ ] Read source files for implementation details
```

## Resources

| Resource                                | What you get                                            |
| --------------------------------------- | ------------------------------------------------------- |
| `gitnexus://repo/{name}/context`        | Stats, staleness warning (~150 tokens)                  |
| `gitnexus://repo/{name}/clusters`       | All functional areas with cohesion scores (~300 tokens) |
| `gitnexus://repo/{name}/cluster/{name}` | Area members with file paths (~500 tokens)              |
| `gitnexus://repo/{name}/process/{name}` | Step-by-step execution trace (~200 tokens)              |

## Tools

**query** — find execution flows related to a concept:

```
query({search_query: "payment processing"})
→ Processes: CheckoutFlow, RefundFlow, WebhookHandler
→ Symbols grouped by flow with file locations
```

**context** — 360-degree view of a symbol:

```
context({name: "validateUser"})
→ Incoming calls: loginHandler, apiMiddleware
→ Outgoing calls: checkToken, getUserById
→ Processes: LoginFlow (step 2/5), TokenRefresh (step 1/3)
```

## Example: "How does payment processing work?"

```
1. READ gitnexus://repo/my-app/context       → 918 symbols, 45 processes
2. query({search_query: "payment processing"})
   → CheckoutFlow: processPayment → validateCard → chargeStripe
   → RefundFlow: initiateRefund → calculateRefund → processRefund
3. context({name: "processPayment"})
   → Incoming: checkoutHandler, webhookHandler
   → Outgoing: validateCard, chargeStripe, saveTransaction
4. Read src/payments/processor.ts for implementation details
```

## Outputs

```json
{
  "status": "completed | partial | blocked | skipped",
  "summary": [],
  "repo_context": [],
  "known_risks": [],
  "next_action": "read-source | impact-analysis | debugging | blocked"
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

Use as a lightweight discovery step before implementation, debugging, impact analysis, or refactoring.
## Token Budget

- Do not paste large raw graph dumps, full diffs, or complete logs.
- Prefer repo context, specific tool results, and short source slices.
- Summarize findings with file paths, symbols, confidence/risk, and the next action.
