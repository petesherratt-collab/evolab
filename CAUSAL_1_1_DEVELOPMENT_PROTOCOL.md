# Causal 1.1 development protocol

**Status:** offline-audited development design; not frozen and not authorized for evaluation

**Generator identifier:** `causal-1.1-dev`

**Created:** 2026-11-12

## Purpose

The sealed `causal-1.0` development run established genuine causal-class structure but exposed a behavioural ceiling. On the eight compute-eligible tasks, every condition was categorically correct and the single-agent mean Brier loss was only `0.012532`. A similar task distribution could not demonstrate the planned practical improvement of `0.10`.

`causal-1.1-dev` is a prospective development version. It keeps the audited additive, relational, and coordination-trap mechanics while addressing three calibration failures:

1. complete evidence previously drove the exact posterior to 1.0;
2. the fixed evidence budget of 100 allowed indiscriminate acquisition;
3. four collective revision calls left too little room for synthesis on relational-hard.

The previous signed manifests and development ledgers remain historical evidence. This version does not alter or reinterpret them.

## Explicit uncertainty layer

Every original possible world now acts as an observation regime. For each latent source fault, the faithful regime has a larger weight while four alias regimes remain possible. All original nuisance configurations are retained, so the transformation preserves:

- positive single-clue information in additive tasks;
- zero marginal information and positive XOR synergy for relational pair members;
- misleading correlated proxies and a corrective physical route in coordination traps.

The five fault priors remain exactly balanced. Full-evidence posterior confidence in the true fault is mechanically capped by difficulty:

| Difficulty | Faithful weight | Alias weight per alternative | Full-evidence ceiling | Sufficiency threshold |
|---|---:|---:|---:|---:|
| Easy | 19 | 1 | 0.826087 | 0.75 |
| Moderate | 11 | 1 | 0.733333 | 0.65 |
| Hard | 7 | 1 | 0.636364 | 0.55 |

The correct fault remains the unique posterior mode after sufficient evidence, but calibrated reports should retain meaningful probability mass on alternatives.

## Scarce evidence budgets

Each condition receives one total task budget. The budget equals the exact minimum sufficient-path cost plus a small frozen verification reserve of 2, 3, or 4 units for easy, moderate, or hard tasks.

| Task class | Easy | Moderate | Hard |
|---|---:|---:|---:|
| Additive | 5 | 12 | 29 |
| Relational | 8 | 21 | 53 |
| Coordination trap | 6 | 15 | 22 |

Easy and moderate minimum sufficient costs remain `3/9`, `6/18`, and `4/12`. Hard tasks add a one-unit router to the guaranteed acquisition path, producing routed path costs of `25`, `49`, and `18`. On some realized relational worlds, a lucky un-routed probe can still yield a hindsight minimum of `48`; the prospective resource budget correctly uses the guaranteed routed cost of `49`. The budget therefore permits one adaptive decisive route plus four units of verification, not broad catalogue purchase.

Budget conservation across conditions is prospective and mechanical:

- single agent: the complete condition budget;
- independent vote: minimum-path clue prices are greedily packed across four isolated investigators, then the verification reserve is distributed;
- independent synthesizer: one minimum-path clue price plus the verification reserve is assigned to synthesis, while the remaining path prices are packed across investigators;
- communicating collective: the same path-feasible investigator/synthesis allocation as independent synthesis.

Packing ties and reserve units rotate deterministically from the task identifier so the same investigator role is not consistently favoured. This price-aware rule prevents an equal numerical split from making every 8-unit hard clue unaffordable while still conserving the exact condition-level total.

## Adaptive hard-task routing

Every hard task contains an independent binary branch, a one-unit routing check, and two expensive branch probes. One probe is informative in branch A and the other in branch B. The remaining minimum-path evidence forms the baseline before this decision.

The exact adaptive diagnostic compares:

- a routed policy that observes the router and then buys the best branch probe; and
- the best fixed policy forced to choose one branch probe before seeing the router.

A hard task passes only when both router outcomes have positive mass, the optimal follow-up differs between outcomes, and the routed policy reduces conditional fault entropy by at least `0.01` bits. Across the full audit, every hard task produced an adaptive gain of `0.165977` bits.

## Compute plan

The target remains 25,000 provider-reported tokens per condition with a ±10% envelope (`22,500–27,500`). The communicating condition reserves 5,000 tokens for its evidence-capable synthesis episode.

Before each prospective peer revision, the harness must reserve:

- 1,800 tokens for the revision; and
- 5,000 tokens for synthesis.

At most two investigators revise. Their order rotates deterministically from the task identifier. A revision is skipped if its conservative estimate plus the synthesis reserve would exceed 27,500 tokens. Applied to the prior relational-hard trace, this rule permits two revisions and blocks the third, leaving the observed synthesis cost inside the envelope.

This is a prospective allocation rule. It does not retroactively change the compute assessment of any `causal-1.0` ledger.

## Offline audit result

The development audit covered 25 seeds in every class/difficulty cell, 225 tasks total.

- accepted: 225;
- rejected: 0;
- unique causal fingerprints: 225;
- unique public fingerprints: 225;
- each correct label: 45 occurrences;
- each correct position: 45 occurrences;
- metadata and text leakage probes: 4/4 passed;
- candidate-renaming, evidence-order, wording, posterior-order, and scarcity invariants: all passed;
- audit ledger records: 227;
- hard adaptive-choice checks: 75/75 passed;
- adaptive gain range: `0.165977–0.165977` bits;
- audit ledger head: `a04906c3a5dccdcb9156770afd75388358f1f00204d6f71d30658fe955a94e10`.

The audit artifacts are:

- `collective_runs/CAUSAL_V11_ADAPTIVE_AUDIT_20261112_DEV.json`
- `collective_runs/causal-v11-adaptive-audit-20261112-dev.jsonl`

## Remaining gates

The manifest-driven `HarnessV11` campaign wrapper is implemented. It verifies task fingerprints, public fingerprints, evidence budgets, path prices, signatures, and frozen source hashes before any model call. A prepared manifest is deliberately rejected until a separately signed authorization artifact changes its status.

The prepared seal artifacts are:

- `collective_runs/FROZEN_DEVELOPMENT_MANIFEST_CAUSAL_1_1_PREPARED.json`
- `collective_runs/FROZEN_EVALUATION_CONFIGURATION_CAUSAL_1_1_PREPARED.json`

Both have detached Ed25519 signatures. The development seal contains nine fresh development seeds but has status `sealed_development_prepared_not_execution_authorized`. The evaluation configuration contains no seed, commitment, hidden world, or task fingerprint.

`causal-1.1-dev` is not ready for the thirty-task evaluation. Before any evaluation seed is generated:

1. create a separate signed authorization artifact only after explicit model-spend approval;
2. run the prepared nine-task development split under that authorization;
3. require all nine tasks to pass compute matching and require non-ceiling single-agent loss;
4. review whether communication materially improves over both the single agent and independent synthesizer;
5. assign a frozen release identifier only after those development gates pass.

The evaluation configuration remains unauthorized. No evaluation master seed, seed commitment, hidden world, or task fingerprint may be created during this development phase.
