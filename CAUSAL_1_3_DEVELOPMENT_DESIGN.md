# Causal-1.3 development design

**Status:** offline design and mechanical audit only

**Evaluation:** locked; no seed, commitment, hidden world, or evaluation task may
be generated

## Why causal-1.2 did not pass

Causal-1.2 showed that communication during evidence allocation has value. The
communicating collective improved mean Brier loss by `0.175322` over independent
synthesis and rescued the hard coordination trap. It still lost to the single
agent by `0.183106` because the catalogue visibly labelled the exact sufficient
route. The single agent bought that route on nearly every task and was correct on
all nine.

The next experiment must remove this acquisition shortcut without giving the
collective additional evidence, compute, private metadata, or an easier task.

## Hypothesis

A collective advantage is possible when success requires both:

1. choosing among equally plausible acquisition alternatives under scarcity;
   and
2. maintaining several kinds of causal bookkeeping at once.

The collective distributes four public interpretive lenses across deliberators.
The single agent receives the same complete charter but must execute all four
lenses itself. The manipulation is organization and communication, not access
to information.

## Generator changes

The causal-1.1 hidden-world mechanics remain the source lineage. Causal-1.3
changes the acquisition surface and uncertainty bands prospectively.

### Easy controls

Easy tasks retain transparent catalogues, the original `19:1` faithful-to-alias
regime weight, and two units of verification reserve. They test whether the new
protocol creates regressions where no ambiguity is needed.

### Moderate and hard acquisition lanes

Each planned clue is paired with a distinct alternative that has the same cost
and region. Catalogue order and wording do not reveal the active option. A
cost-one topology registry identifies the active option label for each lane but
contains zero information about the fault.

The exact planned route is therefore affordable and public, but must be routed
before expensive purchases. Moderate tasks have one unit of verification
reserve; hard tasks have two. A careless expensive purchase cannot be repaired
by buying the entire catalogue.

### Uncertainty bands

The faithful observation-regime weights are:

| Difficulty | Faithful weight | Alias weight each | Full-evidence ceiling |
|---|---:|---:|---:|
| Easy | 19 | 1 | 0.8261 |
| Moderate | 7 | 1 | 0.6364 |
| Hard | 5 | 1 | 0.5556 |

Sufficiency thresholds are `0.75`, `0.55`, and `0.48`. These bands make a
single-agent mean Brier above `0.12` mechanically possible while retaining an
exactly solvable route and balanced five-candidate prior.

## Distinct causal structures

- **Additive:** individually informative channels accumulate candidate-signature
  constraints.
- **Relational:** marginally uninformative observations become useful through
  paired synergy.
- **Coordination trap:** correlated proxies point toward a distractor until
  provenance and calibration are checked.

The topology registry changes acquisition order only. It does not replace or
homogenize these three mechanisms.

## Public perspective charter

Every condition receives all four lenses:

1. causal support and falsification;
2. joint and conditional dependency structure;
3. provenance, calibration, and shared confounding; and
4. adversarial resource accounting.

In the communicating condition one deliberator owns each lens. In the single
condition the same agent owns all four. No lens contains task-specific evidence
IDs, active options, hidden outcomes, or oracle metadata.

## Compute and evidence equality

- Keep the causal-1.2 target of `25,000 ±10%` provider tokens per condition.
- Keep the `27,500` actual-token ceiling and 18-request maximum.
- Keep one shared evidence pool in the communicating condition.
- Charge the topology registry and every lane purchase to the same evidence
  budget used by every condition.
- Do not add retries or extra evidence after observing a scientific failure.

## Offline audit requirements

Before any live development manifest exists:

1. every sampled task must have a balanced prior and exact posterior ceiling;
2. the planned route must be sufficient and the full catalogue unaffordable;
3. every moderate/hard planned clue must have an equal-cost, same-region
   alternative;
4. the topology registry must have zero information gain;
5. active lanes must span at least three regions;
6. catalogue descriptions must not leak the old role labels;
7. additive marginal gain, relational pair synergy, and the coordination trap
   must remain present;
8. path costs must rise strictly from easy to moderate to hard; and
9. the public four-lens charter must contain no private task metadata.

Passing this audit authorizes only preparation of a fresh nine-task development
split. It does not authorize model calls.

## Live development gates

The causal-1.2 gates remain unchanged:

1. all nine tasks compute-eligible;
2. no malformed report, unsupported citation, failed constituent, or evidence
   budget violation;
3. single-agent mean Brier at least `0.12`;
4. communicating improvement at least `0.10` over the single agent;
5. communicating improvement at least `0.05` over independent synthesis; and
6. communicating loss strictly lower than both primary comparators on at least
   six of nine tasks.

No significance test is performed on development tasks. The thirty-task
evaluation remains forbidden until every development gate passes.

## Development infrastructure amendment: 2026-11-15

The first authorized campaign completed two tasks, then the hard additive task
stopped during independent synthesis. It had used 21,806 actual tokens, but the
preflight gate could not reserve both another tool-capable call and a later
mandatory report beneath the 27,500-token ceiling.

Prospectively, if a tool-capable request fails only this reservation check, the
harness releases the future-tool reserve and makes one terminal report request
with tools disabled. The terminal request is still dynamically capped against
the unchanged actual-token ceiling. Request-count, evidence-budget, and compute
eligibility checks remain unchanged. The failed ledger is retained, and the
same sealed task seeds and fingerprints must be used for the resumed attempt.

The resumed campaign completed three more tasks, then hard relational stopped
after its four investigator episodes used 23,193 tokens before mandatory
synthesis could begin. The 2,200-token future-episode reserve was below observed
episode size. Causal-1.3 therefore raises only that reservation to 3,200 tokens.
This forces optional tool exploration to terminate earlier when a mandatory
future investigator or synthesizer must still run. The `25,000 ±10%` target,
27,500-token ceiling, completion cap, request limit, and evidence budgets remain
unchanged.

Hard relational then completed synthesis but stopped before the coordinator's
terminal report. Across that attempt, the four-character prompt estimator was
1.28x to 1.90x provider-reported prompt usage. Calibration to five serialized
characters per token replays those requests at 1.06x to 1.56x actual usage.
The separate 256-token post-call margin remains. This calibration changes no
actual-token ceiling, evidence allocation, request maximum, task seed, or task
fingerprint.

Seven tasks ultimately completed, including hard relational. The moderate
coordination trap then reached 23,562 tokens before its synthesizer's terminal
report and could not fit beneath 27,500. For the two remaining tasks only, the
target becomes 27,500 with bounds of 25,000 to 30,000 tokens. This is the
previously approved bounded ceiling increase, not an unbounded retry. The final
report must treat the mixed compute envelopes as a development limitation; it
cannot silently claim a uniform nine-task envelope.
