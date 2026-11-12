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
| Additive | 5 | 12 | 28 |
| Relational | 8 | 21 | 52 |
| Coordination trap | 6 | 15 | 21 |

The original minimum sufficient costs remain `3/9/24`, `6/18/48`, and `4/12/17` respectively. The budget therefore permits one decisive route plus limited verification, not broad catalogue purchase.

Budget conservation across conditions is prospective and mechanical:

- single agent: the complete condition budget;
- independent vote: the complete budget split across four isolated investigators;
- independent synthesizer: 80% split across investigators and up to 20% reserved for synthesis;
- communicating collective: the same investigator/synthesis split as independent synthesis.

Integer remainders rotate deterministically from the task identifier so the same investigator role is not consistently favoured.

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
- audit ledger head: `91e3b0afbcfb43dcd719e8450dcefb551e1c7288531d1dac22dd92692c21aa6d`.

The audit artifacts are:

- `collective_runs/CAUSAL_V11_AUDIT_20261111_DEV.json`
- `collective_runs/causal-v11-audit-20261111-dev.jsonl`

## Remaining gates

`causal-1.1-dev` is not ready for the thirty-task evaluation. Before any evaluation seed is generated:

1. integrate the prospective evidence allocation and revision limit into a separate development runner;
2. add explicit adaptive branch-choice diagnostics for hard tasks, beyond minimum-cost and path-count checks;
3. seal a fresh nine-task development split under a signed manifest;
4. run that split only after separate model-spend authorization;
5. require all nine tasks to pass compute matching and require non-ceiling single-agent loss;
6. review whether communication materially improves over both the single agent and independent synthesizer;
7. assign a frozen release identifier only after those development gates pass.

The evaluation configuration remains unauthorized. No evaluation master seed, seed commitment, hidden world, or task fingerprint may be created during this development phase.
