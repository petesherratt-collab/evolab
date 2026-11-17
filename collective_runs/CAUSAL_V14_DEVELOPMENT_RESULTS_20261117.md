# Causal 1.4 development results

Analyzed 17 November 2026. **Decision: evaluation remains locked.**

All nine tasks completed on their first attempt. Total reported provider cost
was **$2.7361679**, leaving **$2.2638321** of the authorized $5 allocation.
No further paid run is started by this result. Combined recorded spend for the
causal-1.3 and causal-1.4 campaigns is $6.1123993.

## Findings

The communicating collective narrowly outperformed the single agent on mean
Brier loss, but the advantage was too small to meet the frozen promotion
criterion. It beat independent synthesis by more than the required margin.
All conditions used the same 25,000–30,000-token envelope across all nine tasks.

| Condition | Mean Brier loss (lower is better) | Correct diagnosis | Mean tokens | Cost |
|---|---:|---:|---:|---:|
| Single agent | 0.505274 | 6/9 | 26,328 | $0.7872414 |
| Independent vote | 0.667071 | 3/9 | 26,046 | $0.6626218 |
| Independent synthesis | 0.622602 | 4/9 | 26,701 | $0.5954200 |
| Communicating collective | 0.492833 | 5/9 | 26,407 | $0.6908847 |

Accuracy can differ from probability-based performance: diagnosis labels can
break ties in uncertain reports. Brier loss remains the primary metric.

## Frozen promotion criteria

| Gate | Requirement | Observed | Outcome |
|---|---|---|---|
| 1 | All nine tasks compute-eligible | 9/9, common envelope | Pass |
| 2 | No malformed final report, failed constituent, unsupported citation or evidence-budget violation | Zero of each | Pass |
| 3 | Single-agent mean Brier at least 0.12 | 0.505274 | Pass |
| 4 | Collective mean improvement over single at least 0.10 | 0.012441 | **Fail** |
| 5 | Collective mean improvement over synthesis at least 0.05 | 0.129769 | Pass |
| 6 | Collective strictly better than both primary comparators on at least six tasks | 2/9 | **Fail** |

Four of six gates passed. All six are required. No significance test was
performed on these development tasks. Evaluation has no seed or task list and
remains unauthorized.

## Per-task Brier losses

| Class | Band | Single | Vote | Synthesis | Collective |
|---|---|---:|---:|---:|---:|
| Additive | Easy | 0.117600 | 0.204800 | 0.204800 | 0.051350 |
| Additive | Moderate | 0.460800 | 0.666667 | 0.666667 | 0.635000 |
| Additive | Hard | 0.800000 | 0.800000 | 0.800000 | 0.578750 |
| Relational | Easy | 0.051200 | 0.534400 | 0.051200 | 0.051200 |
| Relational | Moderate | 0.800000 | 0.800000 | 0.800000 | 0.800000 |
| Relational | Hard | 0.666667 | 0.800000 | 0.800000 | 0.668000 |
| Coordination trap | Easy | 0.051200 | 0.679172 | 0.680750 | 0.051200 |
| Coordination trap | Moderate | 0.800000 | 0.718600 | 0.800000 | 0.800000 |
| Coordination trap | Hard | 0.800000 | 0.800000 | 0.800000 | 0.800000 |

Against the single agent, the collective won two tasks, lost two and tied five.
Against synthesis, it won five and tied four. The two wins against both were
additive easy and additive hard.

## Reliability and accounting

- Nine valid task ledger chains contain 939 records and 441 model completions.
- The campaign chain contains 22 records. Its two successful checkpoints cover
  the initial single-task run and the remaining eight tasks, respectively.
  Completion records cover exactly the nine final task ledgers.
- All task fingerprints and compute configurations match the authorized manifest.
- Both the authorized development manifest and prepared evaluation configuration
  have valid signatures, and their frozen source hashes match current files.
- Reported per-call costs reconcile with final condition costs.
- All 36 final condition reports are valid; there are no failed constituents or
  unsupported citations. Every condition's evidence spend is within its budget.
- Two report recoveries succeeded: a truncated voting investigator report on
  relational moderate, and a missing single-agent report on relational hard.
- The three original error entries (JSON parse error, length finish reason and
  missing report) remain in the ledgers. Successful recovery does not erase them.
- Five terminal-report fallback events occurred. No task required a paid retry.

The JSON aggregate uses the established analyzer, whose single-checkpoint
campaign parser predates this protocol. Campaign coverage and signature checks
are therefore recorded separately in `CAUSAL_V14_DEVELOPMENT_AUDIT_20261117.json`.
Its checks also record the six gate outcomes and exact decimal cost accounting.

The code was tested before execution: 69 tests and 80 subtests passed. No code
was changed during the live campaign or this results analysis, so that suite
was not redundantly rerun.

## Interpretation and next diagnostic step

The reliability outcome is better than the preceding campaign, which had
malformed final reports, failed constituents and multiple incomplete attempts.
This run used different tasks and several simultaneous protocol changes, so it
does not isolate the effect of recovery, completion caps or scout handoff.

The remaining limitation is insufficient discrimination on harder cases.
Exactly uniform five-candidate probability reports occurred on four tasks for
the single agent, four for voting, five for synthesis and three for the
collective. Those reports receive a Brier loss of 0.8 regardless of the answer.
All four strategies were uniform on relational moderate and coordination hard.

Several conditions also left substantial evidence budget unused. For example,
on relational moderate the single agent spent 2 of 20 units and the collective
5 of 20; on relational hard they each spent 18 of 52. This supports an offline
investigation of acquisition choices, routing dependencies and stopping rules.
It does not prove whether the cause was inadequate planning, insufficient
tool rounds, compute reservation or justified uncertainty.

Recommended next step: trace those stalled acquisitions against the generator's
known evidence paths, using existing ledgers only. Any new acquisition policy
should then receive offline tests and a prospectively frozen development run.
Do not relax the promotion thresholds to accommodate this result.

## Artifacts

- Aggregate: `CAUSAL_V14_DEVELOPMENT_RESULTS_20261117.json`
- Integrity, gates and cost audit: `CAUSAL_V14_DEVELOPMENT_AUDIT_20261117.json`
- Task ledgers: `development-v14-20261116/`
- Campaign ledger: `development-v14-20261116-campaign.jsonl`
- Authorized payload: `67a4fcb1444320b001738692151de634f2a49c553426155e8e002cd0a3a0da91`
- Prepared evaluation payload: `15cf04d71af1d30ded5ca2a339e308127d3dc5efbfd9184ee8f4f82b2a0940a9`
