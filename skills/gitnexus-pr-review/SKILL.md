---
name: gitnexus-pr-review
description: "Use when the user wants to review a pull request, understand what a PR changes, assess risk of merging, or check for missing test coverage. Examples: \"Review this PR\", \"What does PR #42 change?\", \"Is this PR safe to merge?\""
---

# PR Review with GitNexus

## Purpose

Review PRs or compare diffs with GitNexus impact data, affected flows, and missing-test risk.

## Agent Rules

- Start from GitNexus context/freshness when using MCP graph data; stale or missing indexes are evidence gaps, not current facts.
- Prefer bounded MCP/resource reads and targeted source-file confirmation over broad recursive scans or large raw dumps.
- If indexing is required, run or suggest the project-local `node .gitnexus/run.cjs analyze` path from the repo root; use `--pdg` only when PDG/taint data is needed.
- Treat GitNexus output as navigation and impact evidence; confirm correctness-sensitive conclusions against the current worktree before reporting.

## Inputs

```json
{
  "goal": "PR number/diff/base ref, repo name, optional review focus.",
  "repo": "optional repository name or current repo",
  "constraints": []
}
```

## When to Use

- "Review this PR"
- "What does PR #42 change?"
- "Is this safe to merge?"
- "What's the blast radius of this PR?"
- "Are there missing tests for this PR?"
- Reviewing someone else's code changes before merge

## Workflow

```
1. gh pr diff <number>                                    → Get the raw diff
2. detect_changes({scope: "compare", base_ref: "main"})  → Map diff to affected flows
3. For each changed symbol:
   impact({target: "<symbol>", direction: "upstream"})    → Blast radius per change
4. context({name: "<key symbol>"})               → Understand callers/callees
5. READ gitnexus://repo/{name}/processes                   → Check affected execution flows
6. Summarize findings with risk assessment
```

> If "Index is stale" → run `node .gitnexus/run.cjs analyze` in terminal before reviewing.

## Checklist

```
- [ ] Fetch PR diff (gh pr diff or git diff base...head)
- [ ] detect_changes to map changes to affected execution flows
- [ ] impact on each non-trivial changed symbol
- [ ] Review d=1 items (WILL BREAK) — are callers updated?
- [ ] context on key changed symbols to understand full picture
- [ ] Check if affected processes have test coverage
- [ ] Assess overall risk level
- [ ] Write review summary with findings
```

## Review Dimensions

| Dimension | How GitNexus Helps |
| --- | --- |
| **Correctness** | `context` shows callers — are they all compatible with the change? |
| **Blast radius** | `impact` shows d=1/d=2/d=3 dependents — anything missed? |
| **Completeness** | `detect_changes` shows all affected flows — are they all handled? |
| **Test coverage** | `impact({includeTests: true})` shows which tests touch changed code |
| **Breaking changes** | d=1 upstream items that aren't updated in the PR = potential breakage |

## Risk Assessment

| Signal | Risk |
| --- | --- |
| Changes touch <3 symbols, 0-1 processes | LOW |
| Changes touch 3-10 symbols, 2-5 processes | MEDIUM |
| Changes touch >10 symbols or many processes | HIGH |
| Changes touch auth, payments, or data integrity code | CRITICAL |
| d=1 callers exist outside the PR diff | Potential breakage — flag it |

## Tools

**detect_changes** — map PR diff to affected execution flows:

```
detect_changes({scope: "compare", base_ref: "main"})

→ Changed: 8 symbols in 4 files
→ Affected processes: CheckoutFlow, RefundFlow, WebhookHandler
→ Risk: MEDIUM
```

**impact** — blast radius per changed symbol:

```
impact({target: "validatePayment", direction: "upstream"})

→ d=1 (WILL BREAK):
  - processCheckout (src/checkout.ts:42) [CALLS, 100%]
  - webhookHandler (src/webhooks.ts:15) [CALLS, 100%]

→ d=2 (LIKELY AFFECTED):
  - checkoutRouter (src/routes/checkout.ts:22) [CALLS, 95%]
```

**impact with tests** — check test coverage:

```
impact({target: "validatePayment", direction: "upstream", includeTests: true})

→ Tests that cover this symbol:
  - validatePayment.test.ts [direct]
  - checkout.integration.test.ts [via processCheckout]
```

**context** — understand a changed symbol's role:

```
context({name: "validatePayment"})

→ Incoming calls: processCheckout, webhookHandler
→ Outgoing calls: verifyCard, fetchRates
→ Processes: CheckoutFlow (step 3/7), RefundFlow (step 1/5)
```

## Example: "Review PR #42"

```
1. gh pr diff 42 > /tmp/pr42.diff
   → 4 files changed: payments.ts, checkout.ts, types.ts, utils.ts

2. detect_changes({scope: "compare", base_ref: "main"})
   → Changed symbols: validatePayment, PaymentInput, formatAmount
   → Affected processes: CheckoutFlow, RefundFlow
   → Risk: MEDIUM

3. impact({target: "validatePayment", direction: "upstream"})
   → d=1: processCheckout, webhookHandler (WILL BREAK)
   → webhookHandler is NOT in the PR diff — potential breakage!

4. impact({target: "PaymentInput", direction: "upstream"})
   → d=1: validatePayment (in PR), createPayment (NOT in PR)
   → createPayment uses the old PaymentInput shape — breaking change!

5. context({name: "formatAmount"})
   → Called by 12 functions — but change is backwards-compatible (added optional param)

6. Review summary:
   - MEDIUM risk — 3 changed symbols affect 2 execution flows
   - BUG: webhookHandler calls validatePayment but isn't updated for new signature
   - BUG: createPayment depends on PaymentInput type which changed
   - OK: formatAmount change is backwards-compatible
   - Tests: checkout.test.ts covers processCheckout path, but no webhook test
```

## Review Output Format

Structure your review as:

```markdown
## PR Review: <title>

**Risk: LOW / MEDIUM / HIGH / CRITICAL**

### Changes Summary
- <N> symbols changed across <M> files
- <P> execution flows affected

### Findings
1. **[severity]** Description of finding
   - Evidence from GitNexus tools
   - Affected callers/flows

### Missing Coverage
- Callers not updated in PR: ...
- Untested flows: ...

### Recommendation
APPROVE / REQUEST CHANGES / NEEDS DISCUSSION
```

## Outputs

```json
{
  "status": "completed | partial | blocked | skipped",
  "summary": [],
  "blocking_findings": [],
  "known_risks": [],
  "next_action": "address-comments | request-tests | complete | blocked"
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

Use for GitNexus-assisted PR review; use `code-review` for Apple/iOS static review output contracts when no GitNexus-specific graph work is needed.
## Token Budget

- Do not paste large raw graph dumps, full diffs, or complete logs.
- Prefer repo context, specific tool results, and short source slices.
- Summarize findings with file paths, symbols, confidence/risk, and the next action.
