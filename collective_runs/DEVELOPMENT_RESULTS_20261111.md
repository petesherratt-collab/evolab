# Sealed causal development run — results and calibration decision

**Date:** 2026-11-11

**Scope:** nine-task sealed development split; protocol calibration only

**Evaluation status:** not authorized and not run

## Decision

Do **not** begin the thirty-task evaluation yet.

The causal generator passed its offline structural audit and the development harness produced clean, fully traceable records. However, the live tasks were too easy for the conditions at the available evidence budget. On the eight compute-eligible tasks, every condition made the correct categorical diagnosis and the single-agent mean Brier loss was only `0.012532`. The communicating collective therefore had only `0.012532` mean loss available to improve even if it were perfect, far below the protocol's planned practical-improvement threshold of `0.10`.

This is a useful development result: the generator currently establishes distinct causal structure and mechanically different evidence costs, but those properties have not yet produced adequate model-facing discrimination.

## Run accounting

- All nine sealed task identities have one successful completed ledger.
- The original relational-easy attempt stopped after three conditions when a provider response exceeded the original 180-second read timeout. Its ledger and cost were retained.
- The relational-easy retry used a distinct attempt identity under the signed V2 continuation manifest and completed successfully.
- Eight of nine completed tasks passed the `25,000 ±10%` provider-reported token envelope for every condition.
- Relational-hard was compute-ineligible because the communicating collective used `29,232` tokens, above the `27,500` ceiling. Its other conditions used `22,553`, `22,885`, and `23,368` tokens.
- No completed condition produced a malformed report, unsupported citation, recorded agent error, or failed constituent.
- Successful task cost was `$2.2526`. The retained timeout attempt cost `$0.2215`, for total provider-reported campaign cost of `$2.4741`.

## Primary descriptive results

The main calibration summary excludes relational-hard because it failed the predeclared compute gate. These are development descriptions, not scientific estimates or hypothesis tests.

| Condition | Tasks | Accuracy | Mean Brier loss | Median Brier loss | Mean tokens | Mean evidence spend | Reported cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| Single agent | 8 | 100% | 0.012532 | 0.004155 | 23,863 | 33.000 | $0.6498 |
| Independent vote | 8 | 100% | 0.001716 | 0.001157 | 23,060 | 65.125 | $0.4801 |
| Independent synthesizer | 8 | 100% | 0.003594 | 0.000320 | 23,442 | 50.500 | $0.4905 |
| Communicating collective | 8 | 100% | 0.000715 | 0.000403 | 24,301 | 54.375 | $0.4095 |

Paired task-level descriptive contrasts on the eight eligible tasks:

- Single minus communicating-collective Brier loss: mean `+0.011817`; collective lower on 6 tasks and tied on 2.
- Independent-synthesizer minus communicating-collective Brier loss: mean `+0.002879`; collective lower on 3, tied on 3, and higher on 2.
- Independent-vote minus communicating-collective Brier loss: mean `+0.001001`; collective lower on 4, tied on 2, and higher on 2.

The collective was descriptively best overall, but the absolute differences were small and communication did not consistently beat centralized independent synthesis. No significance test is reported for this development set. The planned evaluation statistic is a paired permutation test on Brier-loss differences, not a chi-square test.

## Per-task outcomes

Values are Brier losses; lower is better. `Ineligible` refers only to the compute-comparability gate.

| Task | Compute | Single | Vote | Synthesizer | Communicating |
|---|---|---:|---:|---:|---:|
| Additive / easy | Eligible | 0.003414 | 0.001821 | 0.001198 | 0.000294 |
| Additive / moderate | Eligible | 0.004896 | 0.008228 | 0.014118 | 0.000818 |
| Additive / hard | Eligible | 0.029400 | 0.000000 | 0.000000 | 0.000000 |
| Relational / easy | Eligible | 0.000000 | 0.000021 | 0.000000 | 0.000000 |
| Relational / moderate | Eligible | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| Relational / hard | **Ineligible** | 0.000000 | 0.611306 | 0.000000 | 0.000000 |
| Coordination trap / easy | Eligible | 0.000542 | 0.001152 | 0.000128 | 0.000512 |
| Coordination trap / moderate | Eligible | 0.028800 | 0.001162 | 0.012800 | 0.002048 |
| Coordination trap / hard | Eligible | 0.033200 | 0.001341 | 0.000512 | 0.002048 |

As a sensitivity description only, including all nine completed tasks changes the mean Brier losses to `0.011139` (single), `0.069448` (vote), `0.003195` (synthesizer), and `0.000636` (communicating). The vote mean is dominated by its wrong relational-hard diagnosis, and that task is compute-ineligible, so these nine-task means must not be used as the primary comparison.

## What the development run teaches us

1. **Structural difficulty is not yet behavioural difficulty.** The exact oracle distinguishes the three causal classes and the easy/moderate/hard evidence paths, but the conditions often recovered the answer with near-certainty. The three relational tasks gave zero Brier loss to the single agent, synthesizer, and communicating collective.
2. **The fixed evidence budget is too generous relative to minimum sufficient cost.** Every condition received 100 evidence units, while the highest minimum sufficient costs range from 17 to 48. Conditions could acquire enough decisive and verification evidence to remove most uncertainty.
3. **There is a floor effect.** With eligible single-agent mean loss at `0.012532`, the planned `0.10` practical improvement cannot be observed on a similar distribution, regardless of collective quality.
4. **Communication-specific value is not yet isolated.** The communicating collective improved over independent synthesis by only `0.002879` on average and lost on two of eight eligible tasks.
5. **Compute matching is close but not finished.** Eight tasks passed. The relational-hard collective exceeded the ceiling by 1,732 tokens, so its revision/synthesis allocation needs a deterministic cap before evaluation.

## Recommended next development version

Preserve the causal graph/oracle approach, but create and audit a new generator version before any evaluation seed exists.

1. Scale evidence prices or condition-specific budgets so a condition can afford roughly one decisive route plus limited verification, rather than most available decisive evidence. The budget rule should be derived mechanically from each task's minimum sufficient cost and frozen before the next live run.
2. Add causal near-miss worlds and calibrated observation uncertainty so the correct answer remains identifiable without routinely supporting probability 1.0. Difficulty should control posterior separation as well as acquisition cost.
3. Make hard tasks require adaptive evidence choice: early observations should determine which later purchase is useful, and buying the wrong branch should consume meaningful scarce resources.
4. Strengthen coordination traps with correlated but persuasive evidence whose dependence is only detectable by combining provenance or audit evidence. Preserve an affordable independent route to the truth.
5. Cap the communicating condition's relational-hard revision/synthesis allowance so every condition remains within the frozen token envelope without post-hoc truncation.
6. Run a fresh, sealed nine-task development split under the new version. Proceed to evaluation only if all tasks are compute-eligible, the single-agent condition has meaningful non-ceiling loss, and communication shows material development headroom over both the single agent and independent synthesizer.

Any generator change must receive a new version identifier, full offline audit, signed development manifest, and fresh development seeds. The present nine tasks remain permanently excluded from evaluation.

## Integrity record

- Signed development manifest payload: `4a613bbcd4f7df3e21ae762f6b31df2d10d912dfdd2691eee49afef9041645ca`
- Signing-key fingerprint: `4fb6947ba7bbc76dac9b2b0687878e8b3be971b24586007562c2cfef002eaa4b`
- Campaign ledger: 26 records; head `f6170146df57513b9011da9b35ebd94045bfbf8bcfa2125ce4819d512c95907f`
- Ten task-ledger chains verified successfully: nine completed ledgers plus the retained timeout ledger.
- Evaluation configuration remains `frozen_but_not_authorized_seed_not_generated`; no evaluation seed was generated.
