# Sealed causal-1.2 development run — results and gate decision

**Date:** 2026-11-14

**Scope:** nine-task sealed development split; protocol calibration only

**Evaluation status:** not authorized; no evaluation seed or tasks generated

## Decision

Do **not** begin the thirty-task evaluation.

All nine final tasks completed inside the `25,000 ±10%` provider-token
envelope. Staged communication materially improved on independent synthesis,
but did not improve on the single agent. The communicating collective had mean
Brier loss `0.244233`, compared with `0.061128` for the single agent and
`0.419556` for independent synthesis. Lower is better.

Two of the six preregistered development gates passed:

1. **Pass:** all nine tasks completed and were compute-eligible.
2. **Fail:** the hard coordination-trap synthesis path recorded a malformed
   intermediate report and `FINISH_REASON_LENGTH`, although a later private
   review produced a valid final report. No final score was malformed and no
   constituent failed.
3. **Fail:** single-agent mean Brier was `0.061128`, below the required `0.12`.
4. **Fail:** communicating improvement over the single agent was `-0.183106`,
   below the required `+0.10`.
5. **Pass:** communicating improvement over independent synthesis was
   `+0.175322`, above the required `+0.05`.
6. **Fail:** communication had strictly lower loss than both primary
   comparators on only one of nine tasks, below the required six.

These are development calibration gates, not statistical significance tests.

## Run accounting and integrity

- Nine final task ledgers verify as valid SHA-256 chains.
- All eleven task-attempt ledgers, including the two retained infrastructure
  failures, verify as valid chains.
- The nine final ledgers contain `963` records.
- The campaign ledger contains `28` records and verifies with head
  `329647ff9999ac46c14d77bf6adb9cae4cd03144aba87eff2666983c0fd77095`.
- Completed-task provider cost was `$2.5534376`.
- Retained incomplete-attempt cost was `$0.4367419`.
- Total provider-reported spend was `$2.9901795`.
- No unsupported citation, final malformed score, failed constituent, or
  evidence-budget violation occurred.

The first attempt stopped when the provider rejected the standard JSON Schema
`uniqueItems` keyword. The second stopped on task 8 because a conservative
preflight estimator reserved more than twice the provider's actual prompt
usage. Both attempts were preserved. The schema compatibility change and the
estimator calibration were separately signed, retained the exact task seeds
and fingerprints, and did not raise the actual `27,500`-token ceiling.

## Primary results

| Condition | Tasks | Accuracy | Mean Brier | Median Brier | Mean tokens | Mean evidence spend | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| Single agent | 9 | 100.0% | 0.061128 | 0.054150 | 23,782 | 18.000 | $0.7573 |
| Independent vote | 9 | 44.4% | 0.620731 | 0.635000 | 23,300 | 18.556 | $0.5940 |
| Independent synthesizer | 9 | 55.6% | 0.419556 | 0.534400 | 23,641 | 16.222 | $0.5645 |
| Communicating collective | 9 | 77.8% | 0.244233 | 0.074700 | 23,441 | 14.556 | $0.6376 |

Paired task-level descriptive contrasts:

- Single minus communicating Brier: mean `-0.183106`; communication was lower
  on 2 tasks and higher on 7.
- Independent-synthesis minus communicating Brier: mean `+0.175322`;
  communication was lower on 4 tasks, tied on 3, and higher on 2.
- Independent-vote minus communicating Brier: mean `+0.376497`;
  communication was lower on 8 tasks and higher on 1.

## Per-task outcomes

Values are Brier losses; lower is better. A dagger marks an incorrect
categorical diagnosis.

| Task | Single | Vote | Synthesizer | Communicating |
|---|---:|---:|---:|---:|
| Additive / easy | 0.054150 | 0.115200 | 0.051200 | 0.063200 |
| Additive / moderate | 0.074700 | 0.534400 | 0.132800 | 0.073200 |
| Additive / hard | 0.063200 | 0.635000 | 0.569600 | 0.117300 |
| Relational / easy | 0.115200 | 0.577400 | 0.051200 | 0.051200 |
| Relational / moderate | 0.051200 | 0.533750† | 0.073200 | 0.534400† |
| Relational / hard | 0.051200 | 0.718750† | 0.534400† | 0.534400† |
| Coordination trap / easy | 0.051200 | 0.800000† | 0.675000† | 0.074700 |
| Coordination trap / moderate | 0.057000 | 0.800000† | 0.675000† | 0.675000 |
| Coordination trap / hard | 0.032300 | 0.872075† | 1.013600† | 0.074700 |

## What the run establishes

### Staged communication repaired part of the fragmentation penalty

Relative to causal-1.1, the communicating condition improved categorical
accuracy from `62.5%` on the eligible tasks to `77.8%` and reduced mean loss
from `0.341287` to `0.244233`. It strongly outperformed independent synthesis
on the easy and hard coordination traps. Communication during resource
allocation therefore matters; it is not merely report polishing.

### Sequential single-agent control still dominates

The single agent was correct on every task and achieved the lowest mean loss.
The shared scout-deliberate-coordinate process sometimes imported poor
proposals or anchored the coordinator, especially on relational/moderate and
relational/hard. Shared ownership removed fixed budget fragmentation, but did
not reproduce the single agent's clean sequential belief updates.

### The development distribution remains too easy for the primary comparator

The single-agent mean loss of `0.061128` is roughly half the `0.12` difficulty
gate. A collective improvement of `0.10` is therefore mathematically
impossible on average even if the collective were perfect. The next iteration
must increase genuine single-agent uncertainty rather than add more agents or
compute.

## Recommended next development version

Do not reinterpret or overwrite this run. For causal-1.3:

1. retain the three causal task classes and the staged shared evidence pool;
2. make hard and moderate worlds less individually recoverable by adding
   evidence interactions that require independent partial perspectives, while
   preserving exact offline solvability;
3. make deliberators critique distinct causal hypotheses rather than emit four
   unconstrained acquisition lists, reducing proposal anchoring;
4. let the coordinator request one targeted clarification from a deliberator
   within the same evidence and compute ceilings;
5. audit single-agent difficulty mechanically before spending on another live
   split; and
6. keep evaluation seedless until every development gate passes.

## Integrity record

- Final authorized retry-manifest payload:
  `72311ed37d26153ac6a838d0453dce99d3c57801f6bec470675bca24f892f108`
- Signing-key fingerprint:
  `4fb6947ba7bbc76dac9b2b0687878e8b3be971b24586007562c2cfef002eaa4b`
- Machine-readable summary:
  `collective_runs/CAUSAL_V12_DEVELOPMENT_RESULTS_20261114.json`
- Evaluation configuration status: `not_authorized_seed_not_generated`;
  `execution_authorization=false`; seed, commitment, and task list are null.
