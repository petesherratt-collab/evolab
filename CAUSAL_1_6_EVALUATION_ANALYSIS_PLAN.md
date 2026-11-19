# Prospective evaluation analysis and precision plan

Prepared 19 November 2026, before any v1.6 model result or evaluation seed.
This is an analysis specification, not authorization to generate evaluation
seeds, spend money, or automatically promote the pilot. The final sample size
and execution budget must be frozen in a separate signed release after pilot
precision review. Historical protocols and verdicts are unchanged.

## Primary population and estimand

The population is an equal mixture of the nine class/band cells in v1.6.
Layouts and complete true worlds are sampled independently under the declared
generator. The experimental unit is a task, not a constituent agent, call,
clue or model token. All four reasoning conditions see the same task packet.
Independent tasks use independent layout/world seeds. Model/provider/settings
must be identical across conditions and fixed before evaluation.

For task i, define D_i = Brier(independent_synthesizer) minus
Brier(communicating_collective). Positive values favor communication. The
primary estimate is the average of the nine within-cell mean differences,
with each cell weighted 1/9. This remains the target if a 30-task design uses
four tasks in each diagonal cell and three in the other six cells. An unweighted
average of those 30 tasks would target a different cell mixture.

Realized Brier loss is primary. Expected Brier under the oracle, single-agent
and voting contrasts, acquisition comparisons, unique-leader accuracy, ties,
calibration, costs and token usage are secondary/descriptive. No alternative
metric replaces the primary one after results are observed. Only one primary
contrast is tested; exploratory contrasts get no unadjusted confirmatory claims.

## Interval, effect size and decision language

Use a two-sided **95%** interval, not a post-hoc choice between 90% and 95%.
The proposed smallest practically worthwhile improvement is **0.05 Brier**.
These choices are fixed now and may be amended only before evaluation seeds
and with a separately recorded rationale, never from evaluation results.

For cell h, let n_h be its task count and s_h² the sample variance of paired
differences. Calculate v_h = s_h²/(81 n_h), SE = sqrt(sum(v_h)), and
df = sum(v_h)² / sum(v_h²/(n_h-1)). The primary approximate interval is
estimate ± t_(0.975,df) SE, clipped to the possible [-2,2] effect range.
This combines independent variance components with a Welch–Satterthwaite
degrees-of-freedom approximation. [NIST method](https://www.itl.nist.gov/div898/handbook/mpc/section5/mpc571.htm),
[SciPy Student-t quantiles](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html).

Report the estimate and interval, not just a significance label. An interval
entirely above zero supports a positive average effect under the approximation;
an interval entirely above 0.05 supports an effect exceeding the practical
threshold. Otherwise distinguish inconclusive precision from evidence of no
effect. Zero observed within-cell variance does not produce a significance
claim or a zero-width t interval.

With three or four observations per cell, normal/t approximations can be poor.
Also report a distribution-free independent-task bounded interval: each task
has weight 1/(9 n_h), D is in [-2,2], and the Hoeffding half-width is
4 sqrt(log(40) sum_i(weight_i²)/2). This interval will usually be very wide at
30 tasks. It is a sensitivity check, not a substitute selected after seeing
which interval is favorable. Neither method automatically promotes anything.

## Precision review before seed release

Thirty tasks are a proposal, not a sufficient sample size by assertion. Target
a 95% interval half-width of at most 0.05 and approximately 80% power to detect
a true improvement of 0.05 against zero. For an initial homogeneous-variance
planning approximation, n_precision = ceil((1.96 SD/0.05)²) and
n_power = ceil(((1.96+0.842) SD/0.05)²). These are planning approximations,
not guarantees for the stratified, bounded, possibly skewed score distribution.

| Paired SD assumption | Approximate half-width at 30 | Balanced task count to review for both targets |
|---|---:|---:|
| 0.10 | 0.036 | 36 |
| 0.20 | 0.072 | 126 |
| 0.30 | 0.107 | 288 |
| 0.50 | 0.179 | 792 |

The calculator in `collective_lab/precision_v16.py` reproduces this table.
The nine-task pilot has only one task per cell: it cannot estimate within-cell
variances or validate confidence-interval coverage. Use the SD grid and the
pilot's overall paired dispersion (also a 1.5× dispersion stress scenario),
without using the observed sign of the pilot effect to loosen the target.
An overall pilot SD is a rough stress input, not an unbiased within-cell estimate.

Before seed release, record the complete pilot, failure counts, variance
sensitivity, approximate power and half-width for the proposed allocation,
and a synthetic-distribution coverage/power simulation covering skewness and
rare failures. Simulation seeds must be separate from experimental task seeds.
Select and sign the allocation, fixed sample size, analysis code/environment,
model/provider settings and dollar ceiling. If 30 tasks cannot meet the target,
either increase the fixed sample size or explicitly designate a 30-task study
as exploratory before generating its seeds. Do not claim it is adequately
powered merely because the budget fits.

## Failure, stopping and missing-data policy

- Score a completed condition with a missing/malformed final report as loss 2.
  Unsupported final citations also receive integrity-adjusted loss 2; retain
  raw Brier alongside the penalty. Report all failed constituents and eligibility.
- A constituent failure with a valid final report retains its actual final loss
  in the primary all-task analysis and is separately flagged. Failed voting
  constituents follow the frozen uniform-contribution rule.
- Infrastructure interruption, unknown charges or budget exhaustion stop the
  campaign. Unstarted tasks are not invented as losses and incomplete tasks are
  not silently dropped. No confirmatory interval or success verdict is released
  for an incomplete planned sample. Any resumption/retry requires a prospectively
  recorded operational decision; original failures remain in the record.
- No outcome-dependent early stopping, peeking-driven sample-size increases,
  replacement of misleading worlds, or rerunning tasks until they pass.
- No complete-case subset becomes primary. Display incomplete results only as
  explicitly partial descriptive results. Confidence intervals use paired task
  differences with fixed cell weights, not independent-agent observations.

## Reproducibility and release status

`stratified_interval` requires every cell and at least two finite paired
differences per cell; it is an interval primitive, not a completeness validator
for a signed evaluation manifest. The future evaluation analyzer must verify
all declared task IDs/conditions and failures before invoking it.
Its analysis environment is pinned in `requirements-evaluation-v16.txt`.

Evaluation seeds remain **unset**. The signed pilot plan binds this document's
hash but cannot authorize evaluation. A fresh signed evaluation release is
required after the precision review; no code in the pilot launcher generates
evaluation seeds or performs automatic promotion.
