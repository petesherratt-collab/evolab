# Causal 1.2 development protocol

**Status:** offline-audited development design; live execution not authorized

**Protocol identifier:** `causal-1.2-dev`

**Generator lineage:** `causal-1.1-dev` mechanics retained unchanged

**Created:** 2026-11-13

## Purpose

The sealed causal-1.1 development run demonstrated real behavioural difficulty
but failed the evaluation gates. On the eight compute-eligible tasks, the
single agent achieved mean Brier loss `0.072844` and 100% categorical accuracy;
the communicating collective achieved `0.341287` and 62.5% accuracy.
Communication improved over independent synthesis on average but was much worse
than a sequential single agent.

The failure mechanism was resource timing. The single agent controlled the
whole evidence budget and could condition later purchases on earlier results.
The collective divided much of its budget before communication, then exchanged
reports after decisive purchases were already fixed. Causal 1.2 changes the
collective protocol, not the audited task mechanics.

## Frozen comparison conditions

The four conditions remain:

1. single agent;
2. independent vote;
3. independent investigators with centralized synthesis; and
4. communicating collective.

The first three retain the causal-1.1 evidence allocations. Only the timing and
control of evidence acquisition changes for the communicating condition. Every
condition still receives exactly one task-level evidence budget and the same
provider-token envelope.

## Staged communicating collective

The communicating condition uses one shared evidence pool. Evidence is never
duplicated or charged twice across stages.

### Stage 1: scout

One scout can spend only the verification reserve: 2 units on easy tasks, 3 on
moderate tasks, and 4 on hard tasks. Its instruction prioritizes cheap routing,
provenance, and observations that should control later purchases. Even if the
scout spends its full ceiling unhelpfully, the entire minimum decisive path
remains affordable.

### Stage 2: acquisition deliberation

Four role-diverse deliberators see the public task, the scout's acquired
results, its provisional report, and the remaining common budget. They cannot
buy evidence. Each returns a structured proposal containing:

- prioritized evidence IDs;
- contingent follow-up purchases;
- evidence to avoid; and
- a resource-aware rationale.

This stage makes diverse reasoning available before expensive purchases are
committed.

### Stage 3: shared coordinator

A coordinator receives all proposals and continues from the scout's exact
shared evidence state. It may condition purchases on observed results and spend
up to the original total evidence budget. Duplicate requests return the
existing result without a second charge.

This creates the intended treatment contrast: independent synthesis pools
reports only after isolated acquisition, while communication can redirect the
same remaining resources before acquisition ends.

## Evidence conservation

For each task:

`scout ceiling = total budget - planned minimum-path cost`

After a maximally wasteful scout, the coordinator's guaranteed remaining budget
equals the planned minimum-path cost exactly. On hard tasks the one-unit router
fits within the scout ceiling, and the baseline plus the active expensive
branch remains affordable afterward.

No condition receives extra evidence because it has more agents. Deliberation
uses model compute, not evidence units.

## Prospective compute gate

The target remains 25,000 provider-reported tokens per condition with a ±10%
envelope (`22,500–27,500`). Causal 1.2 replaces the revision-only estimate with
a condition-level gate applied before every request.

The gate:

- tracks provider-reported tokens cumulatively;
- estimates the next prompt from the complete messages, tools, and response
  schema;
- reserves 2,200 tokens for every mandatory future episode;
- dynamically reduces the next completion cap to the remaining allowance;
- rejects a request when fewer than 96 completion tokens can fit;
- limits a condition to 18 requests and 12 optional private reviews; and
- aborts the condition if reported usage nevertheless crosses 27,500.

Tool-capable episodes also reserve one mandatory final-report call before each
prospective tool round. Optional compute filling stops when the next review
cannot fit. A ceiling violation is therefore a recorded run failure, never a
silently accepted compute-ineligible result.

## Offline audit

The causal-1.2 policy audit is anchored to the valid 225-task causal-1.1
adaptive audit rather than regenerating or changing its hidden worlds.

- source candidates: 225;
- staged allocation accepted: 225;
- rejected: 0;
- hard adaptive source gates retained: 75/75;
- exact representative class/difficulty contracts: 9/9;
- compute-gate properties: 7/7;
- policy-audit ledger records: 227;
- policy-audit ledger head:
  `b7483e5b17cb7dbe16a8639b18e0a4ef7516e96dddc702274aec61813673e31b`.

The audit artifacts are:

- `collective_runs/CAUSAL_V12_POLICY_AUDIT_20261113_DEV.json`
- `collective_runs/causal-v12-policy-audit-20261113-dev.jsonl`

## Development gates

Before any evaluation seed exists, a fresh sealed nine-task development split
must satisfy all of the following:

1. all nine tasks complete and pass the compute envelope;
2. no malformed report, unsupported citation, failed constituent, or evidence
   budget violation;
3. eligible single-agent mean Brier loss is at least `0.12`;
4. communicating mean Brier improvement is at least `0.10` over the single
   agent;
5. communicating mean Brier improvement is at least `0.05` over independent
   synthesis; and
6. the communicating collective has lower Brier loss on at least six of nine
   tasks against both primary comparators.

These are calibration gates, not significance tests. The nine development
tasks can never enter evaluation.

## Authorization boundary

Prepared manifests may contain fresh development seeds, but live execution
requires a separate signed authorization artifact after explicit spend
approval. The evaluation configuration must remain seedless and unauthorized.
No evaluation seed, commitment, hidden world, or task fingerprint may be
generated during this phase.
