# Causal 1.5: interrupted development run

Analyzed 17 November 2026. **Seven of nine tasks completed. Evaluation remains
locked. Promotion cannot be achieved by completing the remaining tasks.**

The campaign stopped automatically at its first task failure: a 300-second
read timeout during coordination-trap moderate (task index 7). Seven preceding
tasks completed under the same frozen protocol. Coordination-trap hard (index
8) was not started. No retry was launched and no experimental code was changed.

## Confirmed spending

| Category | Reported provider charges |
|---|---:|
| Seven completed tasks | $2.3167474 |
| Incomplete task's returned calls | $0.1748535 |
| **Confirmed total** | **$2.4916009** |
| Remaining $5 allocation before any unreturned charge | $2.5083991 |

The timed-out call returned neither a response identifier nor usage information.
Its billing is unknown, so the confirmed total is not a reconciled account
statement. No evidence of a credit-limit error was returned. The user-reported
$7.58 balance was sufficient for the planned allocation; no further funding is
requested for this run.

## Seven-task results — provisional, not a completed evaluation

| Condition | Mean Brier loss (lower is better) | Correct diagnosis | Mean tokens |
|---|---:|---:|---:|
| Single agent | 0.246443 | 5/7 | 26,133 |
| Independent vote | 0.735696 | 3/7 | 25,987 |
| Independent synthesis | 0.606650 | 3/7 | 26,532 |
| Communicating collective | 0.134786 | 7/7 | 26,187 |

All seven completed tasks are compute-eligible. Their 28 final condition reports
contain no malformed reports, failed constituents, unsupported citations or
recorded errors. The collective's mean Brier advantage over the single agent is
0.111657 on this completed subset, and over synthesis it is 0.471864. These are
descriptive results from an incomplete development set, not significance tests
or claims of successful promotion.

## Why another paid attempt cannot secure promotion

The frozen sixth gate requires the collective to have strictly lower Brier loss
than both the single agent and independent synthesis on at least six of nine
tasks. It achieved that on only two of the seven completed tasks: relational
moderate and coordination-trap easy.

Even two additional wins would bring the count only to **four of nine**, below
the required six. This gate is therefore mathematically unreachable while
preserving the seven completed results. No existing result may be rerun merely
to improve this count.

The collective is lower-loss than the single agent on two completed tasks and
higher-loss on five. Its better mean comes from avoiding two large single-agent
errors, not from a consistent advantage across tasks. Correct diagnosis and
probability calibration are different: a correct label can still have high
Brier loss when its probability distribution is uncertain.

| Task | Single Brier | Synthesis Brier | Collective Brier | Collective beats both |
|---|---:|---:|---:|---|
| Additive easy | 0.028800 | 0.024800 | 0.051200 | No |
| Additive moderate | 0.033200 | 0.800000 | 0.051200 | No |
| Additive hard | 0.028800 | 0.800000 | 0.051200 | No |
| Relational easy | 0.012500 | 0.503000 | 0.675000 | No |
| Relational moderate | 0.800000 | 0.800000 | 0.051200 | Yes |
| Relational hard | 0.021800 | 0.800000 | 0.051200 | No |
| Coordination-trap easy | 0.800000 | 0.518750 | 0.012500 | Yes |

The agreed stop-on-first-failure rule was followed. The unreachable promotion
gate provides an additional reason to leave this campaign stopped instead of
paying for a retry and the final task.

## Interruption diagnosis and integrity

The last successful response belonged to investigator 2, round 0 of independent
synthesis on coordination-trap moderate. It requested routing registry E02.
That purchase succeeded. The ledger records its tool result being supplied for
round 1, followed by `TimeoutError: The read operation timed out`.

This identifies the interruption point but not the external root cause. The
available record cannot distinguish provider processing delay from a network
read problem, nor determine whether the provider charged the unreturned call.

- All eight task ledger chains verify, including the retained incomplete task.
- The seven completed ledgers contain 1,093 records.
- The campaign's 20-record chain verifies and covers exactly the seven completed
  task ledgers plus the recorded failed task.
- Recorded manifest references, task fingerprints and compute
  configurations match the authorized task specifications.
- Authorized development and prepared evaluation signatures verify; all frozen
  source hashes match. The evaluation seed and task list are absent and its
  authorization is false.
- The pre-run suite passed 76 tests and 80 subtests. No code changed during the
  campaign or this analysis, so that suite was not redundantly rerun.

## Next useful work

Use the existing ledgers to inspect why relational easy produced a correct but
very uncertain collective report, and why the single agent remained uniform on
relational moderate and coordination-trap easy. Inspect the independent-agent
budget partitions as well: repeated registry purchases may leave individual
agents unable to afford the necessary diagnostic bundles. These are offline
diagnostic questions, not conclusions about their causes.

The restored routing/batching interface was exercised successfully on additive
moderate: both single and collective spent 10 units on the full planned route.
That operational improvement is useful, but it does not establish a general
collective advantage or isolate which version change caused a score difference.

## Artifacts

- Aggregate of seven completed tasks: `CAUSAL_V15_PARTIAL_RESULTS_20261117.json`
- Cost, integrity and gate-reachability audit: `CAUSAL_V15_PARTIAL_AUDIT_20261117.json`
- All completed and partial ledgers: `development-v15-20261117/`
- Campaign record: `development-v15-20261117-campaign.jsonl`
- Authorized payload: `bbf9adaae6291cd8c961de6a73444c33a3d6b58a1b80fe2cf5f2b17f8f009140`
- Evaluation payload: `948b8b2bfbd142314c535720e846015244630faa05358a865208c153e30e991e`
