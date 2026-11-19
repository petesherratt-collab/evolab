# Causal 1.6: separate reasoning from acquisition

Prospective design, 19 November 2026. This replaces neither the signed 1.5
protocol nor its failed promotion verdict. Historical files and scores remain
unchanged. Implementation and validation are offline; paid execution and the
30-task evaluation remain locked.

## Questions and comparisons

**Primary reasoning question:** does exchanging intermediate interpretations
improve diagnosis when investigators have identical observations?

Every condition receives the same fixed packet, with the same descriptions,
numeric probability model and candidate order. The packet is chosen from the
class structure before sampling truth. Hard packets contain both branch probes
and their routing observation; membership cannot reveal the sampled branch.
Trap packets include cached observations and provenance as well as physical
measurements and calibration. Telemetry acquisition is outside this experiment.

| Condition | Four analysis calls | Final aggregation |
|---|---|---|
| Single agent | Sequential private revisions, all four perspectives | Fifth report call |
| Independent vote | Four isolated investigators, one perspective each | Deterministic mean; no model call |
| Independent synthesizer | Four isolated investigators, one perspective each | Fifth report call |
| Communicating collective | Four investigators in sequence; each sees earlier reports | Fifth report call |

The primary contrast is collective minus independent synthesis: same evidence,
perspectives and call count; earlier peer reports are the communication
treatment. Investigator order rotates deterministically by task, identically
in these two conditions. Final synthesis instructions match. Single-agent and
voting contrasts are secondary architecture comparisons, not isolated tests
of communication. The collective is specifically sequential communication,
not a claim about every multi-agent architecture.

**Separate acquisition question:** how well does one continuing investigator
versus a rotating four-perspective team choose evidence from one shared wallet?
Both get the same public catalogue, probability model, total evidence budget,
shared purchase log, at most six decisions, and one final diagnosis call. A
purchase is charged once and is visible to every participant. No participant
gets an unusably small private allocation. The old fragmented independent
baselines are not used as evidence of a reasoning advantage.

The anonymous topology-lane toll is removed in this version. Public catalogue
descriptions explain dependencies, including paired XOR and polarity correction.
The hard branch router remains a real observation costing one unit; it is paid
once. Difficulty therefore no longer includes the old hidden-lane search task.
Changing both contracts means 1.6 is a new experiment, not a direct efficacy
comparison with 1.5.

## Population and mechanical difficulty

For each structural layout, sample **one complete possible world with probability
proportional to its declared weight**, including latent fault, observation
regime, noise, reference phases, calibration, proxy state and active branch.
Separate layout and world seeds are derived from different domains. Integer
ticket sampling is deterministic and reproducible; no rejection, retry or
filtering based on the answer, observed difficulty, faithful regime or score.
The inherited constructor's specially selected true world is discarded.

Five faults have equal priors. A single shared observation regime is faithful
with probabilities 19/23, 7/11 and 5/9 for easy, moderate and hard respectively;
each other regime gets the remaining probability divided by four. The numerical
model and nuisance distributions are disclosed to every agent. Resolving the
observed signature does not eliminate latent-fault uncertainty. Alias cases
stay in the experiment even when the most likely diagnosis is wrong.

Class mechanisms remain distinct: additive channels have marginal information;
relational reference/trace members require joint XOR; the coordination-trap
population includes stale/current cached sources and physical calibration.
Because worlds are sampled honestly, not every trap instance is misleading.

Bands specify known acquisition prices, hard branch routing and residual
uncertainty, not a guarantee that every sampled answer needs three clues or
has a particular realized loss. Single bit patterns can resolve some signatures
earlier than others. Acquisition budget equals the full structural route cost
plus a reserve of 2/1/2 units. Every possible branch must have an affordable
complete route. Reasoning comparisons do not turn higher evidence prices into
a claim of greater reasoning difficulty.

## Explicit stopping and resource accounting

An acquisition response must be a structured `buy` or `finish` decision. It must
state remaining uncertainty, a reason and the best remaining relevant bundle
(or an explicitly empty list). Purchases execute atomically: an over-budget or
invalid bundle buys nothing; previously acquired items cost nothing again.

If a finish decision lists an affordable unbought bundle, it must explicitly
acknowledge deliberate early stopping. Otherwise the next available decision
remains available. This prevents an ordinary report from silently discarding
a purchase opportunity. It does not force all spending or judge relevance
using the private oracle. An empty bundle and claimed relevance remain agent
judgments, available for later audit, not proof that no useful evidence exists.

Log explicit finish, acknowledged early stop, decision-limit exhaustion,
compute-limit exhaustion, denied actions and malformed responses separately.
Malformed responses consume a decision and make the condition ineligible for
a clean protocol pass. No hidden repair or automatic paid retry is allowed.

All conditions have a 30,000-token ceiling and at most seven requests, with
1,800 completion tokens per request. The reasoning schedules use four or five
requests; acquisition uses at most seven. There is no minimum-token padding.
Prompt estimates govern preflight limits; returned usage is checked afterward.
An estimate cannot guarantee the provider will never exceed the token ceiling:
an observed excess aborts and remains a recorded protocol failure. Missing
usage also aborts. This is an equal-budget-cap comparison, not equal realized
compute. Actual tokens, calls and reported dollar costs must accompany scores.

## Scores and interpretation

Realized multiclass Brier loss remains primary. Report paired task differences,
all constituent failures, unsupported citations and incomplete conditions.
Never silently drop a failed or alias task to improve a mean. Failed reports
receive loss 2. Failed voting constituents contribute uniform probabilities
and make the condition ineligible; their failure is not disguised as success.

Also report:

- Probability ties and unique correct leaders separately from diagnosis labels.
- Exact posterior given acquired evidence and its uncertainty, to distinguish
  missing information from misinterpretation.
- Squared distance of the report from that acquired-evidence posterior.
- Expected Brier loss under the complete reference packet, as a secondary
  model-based diagnostic that reduces random-label noise. It cannot replace
  the preregistered realized score after seeing results.
- Purchases, spend, finish reasons, tokens, requests and costs for each arm.

The exact oracle is used only after inference and for offline validation. It
does not supply prompts, live purchases, stop decisions or agent probability
vectors. A public-rule reference planner is used only in offline tests.

## Development and evaluation locks

Prepare nine new development tasks, one per class/band, from a fresh master
seed. Freeze layout/world seeds, task fingerprints, packet IDs, budgets and
condition orders before any model response. Run order rotates within each arm;
the two acquisition conditions alternate first position. The pilot checks
protocol operation and estimates variation; nine tasks cannot establish broad
efficacy. Do not reuse old 1.5 thresholds as though these were the same estimands.

No automatic evaluation promotion is implemented. Before evaluation, fix the
primary estimand, effect-size target, precision/power assessment, failure policy,
model settings, dollar ceiling and paired analysis in a separate signed plan.
Thirty proposed tasks would give ten per class and ten per band (four in each
diagonal class/band cell and three in each other cell); adequacy depends on pilot
variation and the effect worth detecting. Evaluation seeds stay unset until
that plan is fixed. No development significance testing or post-hoc threshold
tuning is justified by the nine-task pilot.

A prepared manifest is not execution authorization. The preparation command
does not open a provider connection. A future live campaign needs a separately
bounded, source-verified launcher; this change deliberately supplies no command
that can silently start spending the user's account balance.

## Offline reproduction

```sh
python -m unittest tests.test_causal_v16 -v
python -m collective_lab.causal_audit_v16 --output /tmp/causal-v16-audit.json
python -m collective_lab.development_v16 --help
```

The audit checks all distinct possible packets, not only the selected true
world, for public interpretation, exact conditional probabilities and complete
route affordability. It checks both integer-sampler interval boundaries, the
declared population mass and deterministic sampling smoke frequencies, plus
class-specific information structure. Full regression and old frozen-source
verification remain required before delivering prepared artifacts.
