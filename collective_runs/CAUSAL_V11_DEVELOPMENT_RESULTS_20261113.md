# Sealed causal-1.1 development run — results and gate decision

**Date:** 2026-11-13

**Scope:** nine-task sealed development split; protocol calibration only

**Evaluation status:** not authorized; no evaluation seed or tasks generated

## Decision

Do **not** begin the thirty-task evaluation.

The new generator successfully removed the near-zero-loss ceiling on several
tasks and produced genuine resource-allocation failures. It did not, however,
establish an advantage for the communicating collective. On the eight
compute-eligible tasks, the single agent was correct on every task and had mean
Brier loss `0.072844`. The communicating collective was correct on five of
eight and had mean loss `0.341287`, making it worse than the single agent by
`0.268444` on average.

Three development gates failed:

1. only eight of nine tasks passed the frozen compute envelope;
2. the communicating collective did not improve over the single agent; and
3. eligible single-agent mean loss remained below `0.10`, so the protocol's
   planned mean improvement of `0.10` was mathematically unavailable even to a
   perfect collective on this primary set.

Communication did improve over independent synthesis by `0.078038` mean Brier
loss on the eligible tasks, but the task-level result was inconsistent: the
collective was better on four tasks, tied on one, and worse on three. That is
useful development evidence, not a release gate pass.

## Run accounting and integrity

- All nine sealed tasks completed without a campaign failure.
- Eight tasks passed the `25,000 ±10%` provider-token envelope for every
  condition.
- Relational/hard was compute-ineligible: independent synthesis used `30,280`
  tokens and the communicating collective used `28,068`, above the `27,500`
  ceiling.
- No condition produced a malformed report, unsupported citation, recorded
  agent error, or failed constituent.
- Provider-reported campaign cost was `$2.1883073`.
- The campaign ledger and all nine task ledgers verify as valid SHA-256 chains.
- The task ledgers contain `1,032` records; the campaign ledger contains `20`.

## Primary eligible-only results

Lower Brier loss is better. These are development descriptions, not scientific
estimates or hypothesis tests.

| Condition | Tasks | Accuracy | Mean Brier | Median Brier | Mean tokens | Mean evidence spend | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| Single agent | 8 | 100.0% | 0.072844 | 0.062200 | 23,401 | 14.250 | $0.6352 |
| Independent vote | 8 | 25.0% | 0.697815 | 0.700992 | 23,245 | 14.625 | $0.4752 |
| Independent synthesizer | 8 | 50.0% | 0.419325 | 0.523200 | 23,502 | 14.375 | $0.4525 |
| Communicating collective | 8 | 62.5% | 0.341287 | 0.201550 | 24,280 | 13.875 | $0.3937 |

Paired task-level descriptive contrasts:

- Single minus communicating-collective Brier loss: mean `-0.268444`;
  collective lower on 1 task, tied on 1, and higher on 6.
- Independent-synthesizer minus communicating-collective Brier loss: mean
  `+0.078038`; collective lower on 4 tasks, tied on 1, and higher on 3.
- Independent-vote minus communicating-collective Brier loss: mean `+0.356528`;
  collective lower on 7 tasks and higher on 1.

No significance test is reported for this development split. The eventual
evaluation statistic remains the preregistered paired permutation test, not a
chi-square test.

## Per-task outcomes

Values are Brier losses; lower is better. A dagger marks an incorrect
categorical diagnosis. Relational/hard is shown for sensitivity only because
it failed the compute gate.

| Task | Compute | Single | Vote | Synthesizer | Communicating |
|---|---|---:|---:|---:|---:|
| Additive / easy | Eligible | 0.038150 | 0.599712 | 0.073200 | 0.068000 |
| Additive / moderate | Eligible | 0.073200 | 0.676563† | 0.051200 | 0.074700 |
| Additive / hard | Eligible | 0.115200 | 0.692188† | 0.534400† | 0.688000† |
| Relational / easy | Eligible | 0.051200 | 0.710938† | 0.051200 | 0.051200 |
| Relational / moderate | Eligible | 0.117300 | 0.710938 | 0.512000 | 0.051200 |
| Relational / hard | **Ineligible** | 0.512000 | 0.718750 | 0.800000† | 0.800000† |
| Coordination trap / easy | Eligible | 0.033200 | 0.709797† | 0.675000† | 0.328400 |
| Coordination trap / moderate | Eligible | 0.112800 | 0.800000† | 0.675000† | 0.688000† |
| Coordination trap / hard | Eligible | 0.041700 | 0.682388† | 0.782600† | 0.780800† |

As a sensitivity description including relational/hard, mean Brier losses were
`0.121639` (single), `0.700141` (vote), `0.461622` (synthesizer), and `0.392256`
(communicating). Accuracy was `100.0%`, `33.3%`, `44.4%`, and `55.6%`,
respectively. These nine-task values are not the primary comparison because the
relational/hard compute overage was material.

## What the run teaches us

### The generator now creates behavioural difficulty

Version 1.0 produced eligible single-agent mean loss of only `0.012532` and
100% categorical accuracy for every condition. Version 1.1 raised eligible
single-agent mean loss to `0.072844` and caused large, condition-specific
failures. The uncertainty layer, scarce budgets, adaptive branches, and
coordination traps therefore changed model behaviour rather than merely
changing offline structural metrics.

### Scarce resources currently favour sequential agency

The single agent controls the entire evidence budget and can condition later
purchases on earlier observations. The collective protocols divide much of
that budget before investigators communicate. Peer revision occurs after those
independent purchases, and synthesis cannot recover evidence that the split
made unaffordable or routed incorrectly.

This is especially visible on additive/hard and coordination-trap/hard: the
single agent was correct while vote, synthesis, and communication all failed.
The experiment has discovered a real mechanism, but it is currently a
fragmentation penalty rather than collective intelligence.

### Communication has some value, but not enough

Communication outperformed independent synthesis on average and rescued the
easy coordination trap categorically. It also produced the best result on
relational/moderate (`0.051200` versus `0.117300` for the single agent and
`0.512000` for synthesis). Those gains were offset by large losses on the hard
adaptive and coordination-trap cases.

### Compute control still needs a hard bound

The prospective revision reserve prevented the earlier four-revision failure,
but it did not bound the full cost of evidence-capable investigator and
synthesis episodes. On relational/hard, prompt growth plus multiple tool rounds
pushed synthesis and communication over the ceiling. A conservative estimate
before peer revision is not sufficient; every prospective model call needs a
condition-level remaining-token gate.

## Recommended next development version

Do not change the completed ledgers or reinterpret this run. Create a new
protocol version and fresh development split.

1. **Move communication into evidence allocation.** Give the communicating
   condition a staged acquisition cycle: cheap initial observations, shared
   deliberation, then a collectively chosen purchase from the remaining common
   budget. Keep independent synthesis restricted to end-of-run pooling. This
   tests whether communication improves adaptive resource allocation rather
   than merely polishing reports after resources are spent.
2. **Preserve total scarcity and compute equality.** The collective must not
   receive extra evidence or model tokens. It should receive the ability to
   redirect the same remaining budget after communication.
3. **Enforce a condition-level token ledger before every request.** Reserve the
   worst-case prompt and completion cost of required synthesis, and skip or
   shorten any optional call that cannot fit under `27,500`. Audit this bound
   over adversarially long tool traces before another live run.
4. **Retain the causal-1.1 task mechanics provisionally.** They now create
   meaningful behavioural separation. Re-audit them with the staged collective
   policy, especially all hard router branches and all coordination-trap
   provenance patterns.
5. **Make the next calibration gates explicit.** Recommended development gates
   are: all nine tasks compute-eligible; eligible single-agent mean Brier at
   least `0.12`; communicating improvement of at least `0.10` over the single
   agent and `0.05` over independent synthesis; and lower collective loss on at
   least six of nine tasks. These are calibration gates, not significance
   claims.
6. **Run another sealed nine-task development split.** Use new seeds and a new
   signed manifest. Do not generate an evaluation seed until every development
   gate passes.

## Integrity record

- Authorized development-manifest payload:
  `767d797502d52c04bc8e3493e553096f51511b882251cfc231d37a1c0c66d8a8`
- Signing-key fingerprint:
  `4fb6947ba7bbc76dac9b2b0687878e8b3be971b24586007562c2cfef002eaa4b`
- Campaign ledger head:
  `83b80e89153ce83e9258eec2fc88e06d13549e36f1ea5f6c5d355c25d939b566`
- Reproducible machine-readable summary:
  `collective_runs/CAUSAL_V11_DEVELOPMENT_RESULTS_20261113.json`
- Evaluation configuration status: `not_authorized_seed_not_generated`;
  `execution_authorization=false`; seed, commitment, and task list are null.
