# Causal generator development audit

**Generator:** `causal-1.0` (frozen; supersedes `causal-1.0-dev`)
**Date:** 2026-11-11
**Status:** expanded offline engineering pass; not evaluation-authorized

## Architecture

Each task contains an explicit directed causal graph, twenty purchasable observations, a balanced prior over five candidate faults, nuisance-state variables, and a finite weighted possible-world table. The exact oracle conditions the possible worlds on evidence outcomes and computes posterior probabilities without a language model or model-based grader.

## Class invariants

- Additive: each core clue has positive marginal information and three signature dimensions are required.
- Relational: individual pair members have zero marginal information; their joint XOR has positive synergy and three pairs are required.
- Coordination trap: correlated cheap evidence favours a designated distractor; provenance and calibrated physical evidence reverse it within the verification allowance.

## Difficulty invariants

| Class | Easy minimum | Moderate minimum | Hard minimum |
|---|---:|---:|---:|
| Additive | 3 units / 8 cheapest paths | 9 / 1 | 24 / 1 |
| Relational | 6 units / 8 cheapest paths | 18 / 1 | 48 / 1 |
| Coordination trap | 4 units / 8 cheapest paths | 12 / 1 | 17 / 1 |

The initial audit covered seeds 500, 501, and 502 in every class/difficulty cell: 27 tasks and 27 unique causal fingerprints. All tasks required at least three observations and achieved a true-candidate posterior of at least 0.90 through an admissible evidence set.

## Expanded offline audit

The expanded audit covered seeds 500 through 524 in every class/difficulty cell: 225 attempted tasks and 225 accepted tasks. It produced 225 unique causal fingerprints and 225 unique public fingerprints, with no rejection or invariant failure. Each of the nine class/difficulty cells contributed exactly 25 tasks. Every correct label and every displayed correct-answer position occurred exactly 45 times.

All attempts are retained in a 227-record append-only SHA-256 hash chain (start, 225 candidate records, completion). The final chain head is `e6aef4d1d49857ad5df11d55bbb3942aee80106f722e890a29860b5942357063`.

Public-view leakage probes used a seed-disjoint split with 135 training tasks and 90 held-out tasks. Chance accuracy is 0.20.

| Probe | Target | Held-out accuracy | Gate |
|---|---|---:|---:|
| Metadata only | Correct label | 0.0889 | 0.40 |
| Metadata only | Correct position | 0.1111 | 0.40 |
| Text only | Correct label | 0.2000 | 0.40 |
| Text only | Correct position | 0.2000 | 0.40 |

Candidate-renaming, candidate-renaming renderer, evidence-order oracle, evidence-order renderer, and wording/oracle invariance checks all passed across every class/difficulty cell.

Audit artifacts:

- `collective_runs/causal-audit-20261109-v2.jsonl`
- `collective_runs/CAUSAL_GENERATOR_AUDIT_20261109_V2.json`

## Frozen-version audit

The version identifier was changed to `causal-1.0` on 2026-11-11. Because the version participates in deterministic layout seeding, the complete 225-task audit was repeated rather than carrying the development result forward. The frozen-version audit again accepted 225 of 225 tasks with no failure, rejection, causal-fingerprint collision, or public-fingerprint collision. Label and displayed-position counts remained exactly 45 each.

The frozen metadata probe accuracies were 0.0889 for correct label and 0.1556 for correct position. Both text probes remained at the 0.20 chance baseline. All five invariance checks passed. The independently verified 227-record audit chain head is `c2ee0d394b9646f40c2b698a22c739fec79e20113d73102a90a62e5c84ec85f2`.

Frozen audit artifacts:

- `collective_runs/causal-audit-20261111-frozen.jsonl`
- `collective_runs/CAUSAL_GENERATOR_AUDIT_20261111_FROZEN.json`

## Leakage finding

An early development renderer placed the complete candidate-signature codebook in the public briefing while the true candidate always occupied the structurally central signature. That would have enabled distribution-aware shortcutting. The codebook was removed before any model-backed causal-task run. Mapping information is now partitioned across purchased observations.

## Remaining gates

Completed gates:

1. A substantially larger seed audit retains every accepted or rejected attempt and rejection reason.
2. Metadata-only and text-only probes test truth labels and displayed answer positions.
3. Candidate-renaming and renderer-invariance property tests are automated.

Remaining gates:

1. Produce and verify the signed development and evaluation-configuration manifests.
2. Run the sealed nine-task development set and make any final protocol changes there.
3. Authorize the thirty-task evaluation only after the frozen development gate passes.
