# Causal 1.3 development result

**Run date:** 2026-11-15 to 2026-11-16

**Decision:** **Do not authorize the 30-task evaluation.**

**Development tasks:** 9 of 9 completed

**Total provider spend:** **$3.3762314**

## Executive result

The causal-1.3 development campaign is complete and interpretable, but it does
not pass the preregistered promotion gates. All nine final task ledgers are
valid and compute-eligible. The single-agent difficulty floor was achieved, and
the communicating collective substantially outperformed independent synthesis.
However, the communicating collective performed materially worse than the
single agent, was lower-loss than both primary comparators on only two of nine
tasks, and produced a malformed report while independent conditions also had
malformed reports and failed constituents.

This is a valid negative development result. The evaluation configuration
remains signed but seedless and unauthorized.

## Gate decision

| Gate | Requirement | Observed | Result |
|---|---:|---:|---:|
| 1 | 9/9 tasks compute-eligible | 9/9 | Pass, with mixed-envelope limitation |
| 2 | No malformed report, unsupported citation, failed constituent, or evidence-budget violation | 2 malformed reports; 3 failed constituents; 0 unsupported citations; 0 observed evidence-budget violations | **Fail** |
| 3 | Single-agent mean Brier loss at least 0.12 | 0.211952 | Pass |
| 4 | Communicating improvement over single agent at least 0.10 | **-0.342050** | **Fail** |
| 5 | Communicating improvement over independent synthesis at least 0.05 | 0.262294 | Pass |
| 6 | Communicating loss lower than both primary comparators on at least 6/9 tasks | 2/9 | **Fail** |

No development significance test was performed, as preregistered.

## Aggregate performance

Lower Brier loss is better.

| Condition | Accuracy | Mean Brier | Median Brier | Mean tokens | Reported cost |
|---|---:|---:|---:|---:|---:|
| Single agent | 0.8889 | **0.211952** | 0.029950 | 24,219 | $0.7385867 |
| Independent vote | 0.2222 | 0.799191 | 0.800000 | 24,141 | $0.5683228 |
| Independent synthesizer | 0.4444 | 0.816296 | 0.800000 | 25,336 | $0.5541179 |
| Communicating collective | 0.7778 | 0.554002 | 0.512600 | 24,729 | $0.6538903 |

The collective was better than independent synthesis on eight of nine tasks,
but better than the single agent on only two. Communication therefore repaired
much of the weakness of independent aggregation without overcoming the much
stronger single-agent baseline.

## Task results

| Class | Difficulty | Single | Independent synthesis | Communicating | Collective lower than both? |
|---|---|---:|---:|---:|---:|
| Additive | Easy | 0.029950 | 0.051200 | 0.032950 | No |
| Additive | Moderate | 0.013268 | 0.666667 | 0.500000 | No |
| Additive | Hard | 0.012800 | 2.000000 | 0.666668 | No |
| Relational | Easy | 0.051200 | 0.051200 | 0.028800 | Yes |
| Relational | Moderate | 0.500000 | 0.800000 | 0.668000 | No |
| Relational | Hard | 0.800000 | 0.800000 | 2.000000 | No |
| Coordination trap | Easy | 0.018300 | 0.800000 | 0.512600 | No |
| Coordination trap | Moderate | 0.002048 | 1.377600 | 0.575000 | No |
| Coordination trap | Hard | 0.480000 | 0.800000 | 0.002000 | Yes |

## Mechanical bands and causal classes

The generator produced a clear mechanical difficulty gradient for the primary
single-agent baseline:

| Band | Mean single-agent Brier | Mean communicating Brier |
|---|---:|---:|
| Easy | 0.033150 | 0.191450 |
| Moderate | 0.171772 | 0.581000 |
| Hard | 0.430933 | 0.889556 |

Performance also differed meaningfully by causal class:

| Class | Mean single | Mean synthesis | Mean communicating | Communicating improvement over synthesis |
|---|---:|---:|---:|---:|
| Additive | 0.018673 | 0.905956 | 0.399873 | +0.506083 |
| Relational | 0.450400 | 0.550400 | 0.898933 | **-0.348533** |
| Coordination trap | 0.166783 | 0.992533 | 0.363200 | +0.629333 |

These differences support the claim that causal-1.3 contains genuinely distinct
task structures and difficulty bands. They also isolate the principal strategy
failure: communication was useful against weak independent synthesis on
additive and coordination-trap tasks, but harmful on the relational class and
consistently inferior to the single-agent baseline overall.

## Reliability and integrity

- All 13 task ledgers, including four retained partial attempts, have valid hash
  chains.
- The 36-record campaign ledger has a valid hash chain.
- All nine selected final ledgers contain exactly one completed run and are
  compute-eligible.
- The final selected ledgers contain 921 records.
- No unsupported citations were recorded.
- Independent vote had three failed constituents. The communicating collective
  and independent synthesizer each had one malformed scored report.
- Several conditions also recorded recoverable JSON/truncation or missing-report
  errors; these are retained in the ledgers and are not hidden by the aggregate.

The first seven completed tasks used the original 22,500–27,500-token envelope.
After prospectively documented reservation and prompt-estimation amendments,
the final two used a 25,000–30,000-token envelope. Every final task passed its
applicable compute-balance check, but the campaign is not a uniform-envelope
nine-task experiment. That limitation is another reason not to treat this run
as evaluation evidence.

## Cost accounting

| Category | Cost |
|---|---:|
| Nine completed final attempts | $2.5149177 |
| Four retained partial attempts | $0.8613137 |
| **Total provider spend** | **$3.3762314** |

The campaign remained below the approved $3.50 ceiling. No model calls are
needed for the remaining analysis or remediation work.

## Promotion decision and next move

The 30-task evaluation remains locked. The next development version should
change the strategy rather than merely generate more tasks:

1. harden structured-output recovery so a truncated or missing report cannot
   become a malformed scored answer;
2. add a coordinator conflict check that preserves a strong, well-supported
   individual diagnosis unless communication supplies explicit contradictory
   evidence;
3. target the relational failure mode, where communication amplified error;
4. rerun a fresh nine-task development split under one uniform compute envelope;
5. authorize evaluation only if every preregistered gate passes on that fresh
   split.

## Frozen artifacts

- Authorized development payload: `8c4e9072880d0eac81b2f77df3afc11c28fe7d821475cc5612980b25dac8a0a2`
- Prepared evaluation payload: `9668d70fbc6a6d5e183343b1259ee0857ee26e5e29cda3f60d9f7d0fcd97fa98`
- Signing-key fingerprint: `4fb6947ba7bbc76dac9b2b0687878e8b3be971b24586007562c2cfef002eaa4b`
- Evaluation master seed: absent
- Evaluation execution authorization: false

Machine-readable aggregate results are in
`collective_runs/CAUSAL_V13_DEVELOPMENT_RESULTS_20261116.json`.
