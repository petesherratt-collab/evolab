# Causal 1.5 diagnostic findings

19 November 2026. Offline analysis only; no provider calls or new charges.

## Conclusion

The inconsistent collective advantage has three distinguishable explanations:
voluntary early stopping, confidence differences on already-solved cases, and
weak independent comparators created partly by budget fragmentation. A further
measurement issue is that the selected true worlds always use faithful
observations, although the oracle weights misleading observation regimes too.

Do not spend on another prompt revision yet. Repair and test the experimental
measurement and comparator contract first. The existing version remains a failed
promotion attempt; no score or threshold was changed by this audit.

## What accounts for the score differences

The seven-task mean collective improvement over the single agent was 0.111657.
Its underlying total Brier difference was 0.7816, divided by seven tasks:

| Group | Tasks | Total collective improvement |
|---|---:|---:|
| Both bought the complete planned route; confidence differed | 4 | -0.0922 |
| One side stopped before buying affordable diagnostic evidence | 3 | +0.8738 |
| Total | 7 | +0.7816 |

The four small losses occurred on additive easy, moderate and hard, and
relational hard. Both strategies acquired the full planned route and selected
the correct diagnosis. The collective assigned it 0.80 probability; the single
agent assigned 0.84–0.87. The realized score rewarded the latter's higher
confidence. These losses are not evidence of failed causal reconstruction.

The remaining three differences were much larger:

| Task | Agent that stopped early | Spent / available | Affordable route still missing | Collective improvement |
|---|---|---:|---:|---:|
| Relational easy | Collective coordinator | 2 / 8 | Four items costing 4 | -0.6625 |
| Relational moderate | Single agent | 1 / 20 | Six items costing 18 | +0.7488 |
| Coordination-trap easy | Single agent | 2 / 6 | Three items costing 3 | +0.7875 |

All three returned a report on tool-enabled round 1 without requesting another
purchase. The ledger explicitly records `model_returned_without_tool_request`.
There was no tool-round exhaustion or compute fallback in these three stopping
events. Each final report recommended the missing observations. Thus the v1.5
batching instruction made acquisition feasible but did not prevent premature
completion.

In relational easy, the collective bought one reference/trace pair and stopped.
Its 0.30/0.30/0.30 probabilities over three compatible candidates were close to
the oracle probabilities given only that pair. The main failure was leaving
useful evidence unbought, not misinterpreting the evidence it had.

**Correction to the earlier accuracy headline:** the collective's seven correct
diagnosis labels include this three-way tie. Six were unique probability leaders;
one was a correct tie-breaking label. “7/7 correct” should not be read as seven
fully resolved diagnoses. Brier loss remained the primary metric throughout.

## Why the independent comparators were so weak

Among 36 independent investigator/synthesizer episodes on the four completed
routed tasks:

- 17 budgets could not cover the registry plus even one active nonrouting item.
- 35 ended with an exact oracle posterior of 0.20 for every candidate, based on
  the evidence actually acquired.
- Some budgets that could cover an item still could not cover a relational
  reference/trace pair or a physical measurement plus calibration. Conversely,
  some participants with affordable options also stopped early.

For additive moderate, voting budgets were 3, 1, 4 and 3 units. Each investigator
bought the registry for 1; active observations cost 3 each. Only the investigator
with 4 units could afford one afterward, and it did not buy it. In independent
synthesis the investigator budgets were 1, 0, 3 and 3, with 4 reserved for the
synthesizer. All final evidence amounted to repeated registry access.

The allocation code packs individual clue costs across participants, including
one routing cost in the planned route. It does not ensure that every isolated
participant can pay its own routing overhead or buy a useful dependency bundle.
The collective shares routing results and a common pool; independent agents
must pay locally and cannot transfer their unused balances.

This is a real architectural difference, not an accounting violation. It means
the measured contrast mixes communication with shared access, repeated routing
costs, dependency affordability and voluntary stopping. It cannot establish a
pure communication benefit. The “cannot afford” count is a lower bound for the
declared active route, not proof that no alternative noncore observation could
ever be informative. The exact oracle calculation separately describes the
information in their actual purchases.

## The calibration and world-selection problem

The observation-regime transform constructs weighted possibilities for faithful
and misleading observations, but chooses the true world by matching the original
fault and original true-world index. Consequently the selected observation
regime equals the true fault. This holds for all seven regenerated completed
tasks and follows from the selection code, rather than being a chance pattern
in a weighted sample.

After complete evidence, the oracle's true-candidate probabilities are about
0.8261 on easy, 0.6364 on moderate and 0.5556 on hard tasks. But the selected
labels always agree with the faithful signature. This selection rewards greater
confidence in that signature, even when it exceeds the oracle posterior.

For example, on additive hard the collective assigns 0.80 to the true candidate,
whereas the oracle assigns 0.5556. Its realized Brier loss is 0.0512. Under the
oracle's full conditional distribution, the same reported probabilities have
expected loss 0.717867; the oracle posterior itself has expected loss 0.641975.
The single agent's still higher confidence scores better on the selected true
label, but this is not evidence that it is better calibrated to that distribution.

Brier scoring is not the problem. The issue is interpreting a deliberately
selected faithful-world sample as though it measured performance under the
weighted noise model. These tasks can be deterministic diagnostic challenges,
or tests of probabilistic calibration under sampled noisy worlds, but the
current setup does not make those objectives interchangeable. The private
oracle weights are also not numerically disclosed to agents, which further
limits claims about their ability to reproduce exact posterior probabilities.

## Recommended next work, before another paid campaign

1. Specify the target population and scoring objective. If calibration under
   the weighted world model is intended, sample or prospectively stratify true
   worlds to represent its faithful and misleading regimes. Validate that
   selection offline. Do not selectively sample only faithful cases and call
   the oracle ceiling an empirical difficulty guarantee.
2. Add comparator feasibility checks. Account for repeated routing and complete
   diagnostic dependencies in individual budgets. If isolating communication
   is the objective, give comparisons matched access to routing and comparable
   evidence, and separate acquisition coordination from reasoning aggregation.
   A deliberately fragmented-budget baseline can remain, but label its scope.
3. Make early stopping explicit and auditable. Require a finish decision to
   identify remaining uncertainty, affordable relevant bundles and why further
   acquisition is not worthwhile. Test a scheduler that permits the remaining
   tool opportunity when such a bundle is selected, within the frozen budget.
   Do not force every agent to spend all resources regardless of information.
4. Run offline sampler, affordability and stopping-policy checks, then specify
   a fresh experiment and any ablations before new model calls. Preserve the
   current failed result; any revised measurement contract must be prospective.

## Verification and limitations

Seven task worlds were regenerated and matched their recorded and manifest
fingerprints. The seven completed ledger chains verify; the incomplete eighth
ledger also verifies and was explicitly excluded. The unstarted ninth task was
not generated by this audit. All historical frozen source hashes and manifest
signatures still match; evaluation remains seedless and unauthorized.

Two focused diagnostic tests passed, covering explicit partial/unstarted task
exclusion and early-return versus tool-limit/fallback classification. The live
harness was not changed, so its full regression suite was not rerun.

Oracle calculations use privileged world information and are offline diagnostics
only, never future agent inputs. These are trace-based explanations, not causal
ablations of each proposed change. The completed subset is seven tasks, and the
selection bias and comparator limitations preclude broad efficacy claims.

The raw analysis is in `CAUSAL_V15_DIAGNOSTIC_AUDIT_20261119.json`; compact score,
budget and verification findings are in `CAUSAL_V15_DIAGNOSTIC_FINDINGS_20261119.json`.
`collective_lab/acquisition_audit_v15.py` reproduces the trace/oracle analysis from
the saved manifest and ledger directory. Current account balance was not queried;
the user's stated $14.21 remains a reported balance, not a spending authorization.
