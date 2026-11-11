# Collective-Intelligence Engineering Results — 2026-11-01

## Status

These are engineering results only. They are permanently excluded from development and exploratory evaluation data. They do not establish collective intelligence.

Model: `openai/gpt-6.1-sol` through OpenRouter, medium reasoning effort.
Task: `eng-additive-001`, a hand-authored additive fictional fault-isolation task.
Completed comparison ledger: `eng-additive-all-rerun3-20261101.jsonl`.

The completed ledger contains 192 records and verifies as a valid SHA-256 hash chain with head:

`1156fd3a40f6890b31e44119224b7d432b37373866cdd602ace1237b53819887`

## Completed comparison

| Condition | Correct | Brier loss | Evidence spent | API requests | Total tokens | Reported cost |
|---|---:|---:|---:|---:|---:|---:|
| Strong single agent | Yes | 0.000020 | 35 | 3 | 4,222 | $0.00498 |
| Independent vote | Yes | 0.000592 | 90 | 12 | 16,980 | $0.05147 |
| Independent + synthesizer | Yes | 0.000080 | 88 | 14 | 20,119 | $0.04650 |
| Communicating collective | Yes | 0.000032 | 76 | 18 | 25,964 | $0.07843 |

All final reports passed schema validation. No condition produced an unsupported citation or recorded agent error.

The communicating collective's paired Brier improvement relative to the single agent on this task is `-0.000012`; negative values mean the collective was worse. Accuracy was tied. This single engineering task supplies no statistical inference.

## Primary finding

The live harness can isolate agent contexts, enforce evidence budgets externally, execute tool-mediated evidence purchase, aggregate or communicate reports, mechanically score calibrated outputs, record provider usage, and preserve an append-only run.

The current implementation does **not** match inference compute across conditions. The communicating collective used 25,964 tokens versus 4,222 for the single agent, a 6.15× ratio. Consequently, even a collective win would not support the protocol's Level-2 compute-matched claim. No further scientific run should occur until compute matching is redesigned and tested.

## Infrastructure incidents and spend

The preliminary single-agent smoke ledger is valid and cost $0.01210.

Two comparison processes continued after the app command host appeared to interrupt them. An external interruption annotation was appended while each process still held a cached chain head, creating forked ledgers:

- `eng-additive-all-20261101.jsonl`: first invalid link at line 59, duplicate sequence 57; observed provider cost $0.20199.
- `eng-additive-all-rerun-20261101.jsonl`: first invalid link at line 26, duplicate sequence 24; observed provider cost $0.18510.

These two files remain preserved but are invalid and unusable as scientific evidence. A detached launch attempt produced no output and made no observed model call. The valid completed comparison cost $0.18137.

Total observed provider cost across the smoke test, two invalid attempts, and valid comparison was approximately **$0.58056**.

The harness now uses an exclusive lifetime lock for each collective run ledger. A test confirms that a second writer is rejected and that the ledger can be reopened safely after the first writer exits.

## Required next change

Before another model-backed comparison:

1. Define a provider-measured token or cost ceiling shared by every condition.
2. Give the strong single agent enough staged self-review to approach that ceiling.
3. Reduce or cap collective tool-loop and communication calls so it cannot exceed the ceiling.
4. Add an automatic `compute_matched` validity check to every completed condition comparison.
5. Treat a comparison outside the preregistered tolerance as engineering-invalid without interpreting performance.

## Compute-calibrated three-task set

After the initial result exposed the compute confound, the engineering harness was amended to target 20,000 provider-reported tokens per condition with a temporary calibration tolerance of ±15%. Meaningful private or synthesis review used the remaining allowance; the independent-vote condition remained non-communicating.

Three hand-authored engineering tasks were run under the same settings: additive, relational, and coordination trap. All three ledgers verify, and every condition in every task passed the temporary envelope.

| Condition | Accuracy | Mean Brier loss | Mean tokens | Three-task cost | Recorded constituent/review errors |
|---|---:|---:|---:|---:|---:|
| Strong single agent | 100% | 0.006312 | 18,435.7 | $0.21581 | 0 |
| Independent vote | 100% | 0.119339 | 18,012.3 | $0.21930 | 4 |
| Independent + synthesizer | 100% | 0.000422 | 17,729.0 | $0.19833 | 1 |
| Communicating collective | 100% | 0.000291 | 20,460.3 | $0.21663 | 2 |

The three-task collective-minus-single mean Brier improvement is 0.006021, well below the preregistered practical threshold of 0.10. The communication-over-independent-synthesis improvement is only 0.000130. Accuracy is tied across every condition.

The calibrated engineering result is therefore a **null result for collective intelligence**. It suggests that centralized synthesis with a verification reserve improves calibration on these tasks, while the added peer-communication round contributes little or nothing beyond synthesis. Three hand-authored tasks cannot support statistical inference or generalization.

The calibrated three-task set cost $0.85007. A separate single-agent calibration cost $0.07111. Including the earlier smoke test and invalid infrastructure attempts, total observed OpenRouter cost to this point is approximately **$1.50173**.

Pre-evaluation hardening subsequently added strict JSON Schema requests, endpoint parameter enforcement, explicit constituent success/failure counts, uniform-distribution treatment for failed independent voters, a deterministic engineering task generator, and a tighter ±10% default compute envelope. These changes do not retroactively alter the three calibrated ledgers above. The generated-task semantics and leakage resistance still require review, and no thirty-task exploratory evaluation has been authorized.

The first generated-task structured-output smoke (`generated-structured-smoke-20261101.jsonl`) verified the live schema/tool path and produced a valid 17-record ledger with no output errors, but exposed a generator defect: phase labels followed catalogue encounter order rather than declared relational-pair order. Its $0.015092 result is engineering-invalid and is not interpreted. The generator was corrected, given explicit symmetric-pair and complementary-phase validation, and version-bumped from `generated-0.2` to `generated-0.2.1`.

The first corrected-generator smoke (`generated-structured-smoke-v021-20261101.jsonl`) used a deliberately low 700-token completion ceiling. Its final JSON was incomplete and local validation correctly recorded a malformed report with loss 2. The 13-record chain is valid and the $0.014415 run is retained as a report-ceiling failure test, not performance evidence.

The final corrected-generator smoke (`generated-structured-smoke-v021b-20261101.jsonl`) used a 1,400-token completion ceiling. It completed with no errors or unsupported citations, selected the correct candidate, and achieved Brier loss 0.001336. It spent 20 evidence units across two API requests, used 3,311 provider-reported tokens, and cost $0.008743. Its 14-record hash chain verifies with head `f97558b3257a511af449a3f87cf403c5ac110c5b529141d82957eb68562119b1`. Compute matching was deliberately disabled because this was a single-condition interface smoke, not a comparison.

Including these three structured-output/generator smokes, total observed OpenRouter engineering spend is approximately **$1.53998**.

## Generated-task four-condition calibration

Generator `generated-0.3` was mechanically audited over 3,000 cases. All fingerprints were unique; each of the five truth labels and each displayed candidate position occurred exactly 600 times; evidence composition, individual-clue ambiguity, ordinary clue-pair ambiguity, relational pairing, multi-region sufficiency, and trap-verification checks passed. The audit also found and removed a prior distribution leak: `generated-0.2.1` never made `none_of_the_above` true.

The first four-condition `generated-0.3` comparison (`gen03-trap-252-all-cal1.jsonl`) produced a valid 150-record chain with head `726c9babc45fcb771848b96ca7c29b9caf78a978cb226310c7fd837fe88e202a` and cost $0.314012. Provider-reported token totals were 18,336 (single), 19,275 (vote), 18,417 (independent synthesizer), and 25,485 (communicating collective). The final condition exceeded the 20,000 ±10% envelope, making the entire comparison compute-invalid. Its apparent scores are not interpreted. The natural collective floor motivated a prospective 25,000 ±10% engineering target with additional private baseline audits; validation must use a fresh task seed.

Total observed OpenRouter engineering spend through this invalid calibration is approximately **$1.85399**.

### Fresh-seed 25,000-token validation

The prospective calibration was tested on fresh task `gen-coordination_trap-253` in `gen03-trap-253-all-cal2.jsonl`. All four conditions fell inside the 25,000 ±10% envelope: 23,784 tokens (single), 23,908 (vote), 23,375 (independent synthesizer), and 24,866 (communicating collective). The maximum-to-minimum ratio was 1.064. The ledger contains 159 records and verifies with head `07dbaf9dd8fa2deef967f2df8b681c65ec0005f406a9539db8a8a57d01e61524`.

| Condition | Correct | Brier loss | Evidence spent | API requests | Tokens | Cost |
|---|---:|---:|---:|---:|---:|---:|
| Strong single agent | Yes | 0.518750 | 18 | 12 | 23,784 | $0.091407 |
| Independent vote | No | 0.529722 | 39 | 13 | 23,908 | $0.098691 |
| Independent + synthesizer | No | 0.542150 | 40 | 12 | 23,375 | $0.094645 |
| Communicating collective | No | 0.531200 | 38 | 14 | 24,866 | $0.086794 |

No report was malformed, no citation was unsupported, and all constituents produced valid reports. Relative to the single agent, the communicating collective's Brier improvement was -0.012450: it was slightly worse. Communication improved Brier by 0.010950 relative to independent synthesis, but both conditions selected the wrong diagnosis. This is one engineering task and provides no statistical inference; it is a negative result for the collective-intelligence hypothesis, not confirmation.

The valid comparison cost $0.371536. Total observed OpenRouter engineering spend is now approximately **$2.22553**.

## Offline causal-generator milestone — 2026-11-06

A separate `causal-1.0-dev` generator and exact finite-world oracle were added without making any API calls. The earlier `generated-0.3` implementation remains unchanged for ledger reproducibility.

The oracle was exercised on 27 tasks covering three seeds × three causal classes × three difficulty bands. All 27 causal fingerprints were unique and all acceptance gates passed. Across every seed, minimum sufficient costs and cheapest-path counts were:

| Class | Easy | Moderate | Hard |
|---|---:|---:|---:|
| Additive | cost 3, 8 paths | cost 9, 1 path | cost 24, 1 path |
| Relational | cost 6, 8 paths | cost 18, 1 path | cost 48, 1 path |
| Coordination trap | cost 4, 8 paths | cost 12, 1 path | cost 17, 1 path |

Additive core clues have positive individual information gain. Relational pair members have zero individual information gain and positive joint synergy. Coordination-trap cheap proxies increase the posterior of the designated distractor above the truth, while the verification path raises the true candidate to at least 0.90 and costs no more than 20.

A manual leakage review found and removed an initial public-codebook leak before any model-backed run. Candidate mappings are now revealed only inside purchased evidence. The causal generator remains development-only pending a larger distribution audit, automated wording/metadata probes, renderer freeze, rejection ledger, and sealed task manifest. OpenRouter spend remains **$2.22553**.
