# B0 Collective-Intelligence Protocol

**Protocol version:** 0.1-draft
**Date frozen for review:** 2026-10-31
**Status:** Engineering harness and capped engineering dry run authorized 2026-11-01; exploratory evaluation not yet authorized
**Programme:** Collective-intelligence research programme, scientifically distinct from the continuous-capital evolutionary ecology study

## 1. Purpose and scope

This protocol defines the B0 operational meaning of collective intelligence and the first exploratory task environment. It does not authorize implementation, experiment execution, changes to ecological rules, external publication, committing, pushing, or resource scaling.

The initial question is:

> Under an approximately matched total evidence and inference budget, can a communicating collective of isolated instances of the same model outperform a strong single agent, independent voting, and independent investigators with centralized synthesis on fresh fictional fault-isolation tasks?

The initial study deliberately excludes evolutionary selection, reproduction, inheritance, mutation, cross-model heterogeneity, adversarial agents, external web data, and agent control of the evaluator.

## 2. Operational definition

A system exhibits provisional collective intelligence when multiple agents, interacting through a prespecified protocol, produce a reproducible advantage on externally evaluated held-out tasks that cannot be explained solely by additional compute, individual-agent quality, simple aggregation, centralized synthesis, or evaluator exploitation.

The initial target is **Level 2: compute-matched collective gain**:

1. Level 0 — aggregation gain: better than the average constituent.
2. Level 1 — strong-member gain: better than a preregistered strong individual.
3. Level 2 — compute-matched collective gain: better than an equal-budget single agent and applicable simple ensemble baselines.
4. Level 3 — robust collective intelligence: Level 2 replicates across fresh seeds, task families, and distribution shift.
5. Level 4 — mechanistically attributed collective intelligence: ablations identify the collective mechanism responsible.

B0 defines and explores Level 2. Later milestones are required for Levels 3 and 4.

## 3. Units of analysis

### 3.1 Individual agent

An individual is one persistent decision-making process defined by its model, model settings, prompts, tool permissions, private context, memory, assigned role, and resource allowance. Multiple model turns remain one individual when they share identity and persistent private state. A fresh context without inherited private state is a new individual.

### 3.2 Collective

A collective consists of two or more individuals whose task-dependent outputs jointly affect a final answer through a prespecified aggregation or communication protocol. The collective includes investigators, coordinators, synthesizers, shared memory, communication, retries, and aggregation logic.

### 3.3 Protocol

The protocol fixes membership, roles, initial information, communication topology, message timing and size, aggregation, stopping conditions, resource allocation, and failure handling. A scientifically meaningful change creates a new condition or protocol version.

### 3.4 Task instance

A task instance is one immutable fictional fault-isolation problem with a hidden world state, objectively correct answer, evidence catalogue, resource prices, tool environment, evaluator version, generator version, and seed.

### 3.5 Trial and condition

A trial is one execution of:

`task instance × condition × seed × budget × environment version`

Every attempted trial receives a unique identity before execution. A condition is a fully specified protocol and configuration applied across trials and identified by a configuration hash.

### 3.6 Primary statistical unit

The task instance is the primary statistical unit. Conditions face the same tasks, so primary comparisons are paired within task. Repeated seeds within a task are nested observations and are not treated as fully independent tasks.

## 4. Task environment

### 4.1 Semantic form

Tasks are fictional fault-isolation scenarios. They use deterministic hidden causal structures and require no current external knowledge. Generation and scoring are mechanical rather than model-judged.

Each task contains:

- five components;
- four candidate root faults plus “none of the above”;
- exactly one true root fault;
- twenty purchasable evidence sources;
- a hidden directed causal graph connecting faults, latent variables, evidence, and symptoms.

### 4.2 Evidence composition

The target composition is:

- 8 relevant direct clues;
- 4 relevant clues whose meaning depends on another clue;
- 3 redundant clues;
- 3 plausible but globally resolvable misleading clues;
- 2 irrelevant clues.

Misleading clues may arise from an unreliable source, confounding, outdated information, unmet conditions, or non-causal correlation. They must be reconcilable from the task world and must not be arbitrary falsehoods.

### 4.3 Task classes

1. **Additive:** independent clues accumulate toward the answer.
2. **Relational:** clues must be interpreted together, including at least one dependency.
3. **Coordination trap:** inexpensive early evidence favours a plausible wrong answer, while an affordable verification path reveals the truth.

### 4.4 Difficulty bands

Difficulty is determined before agent exposure from graph properties:

- Easy: several affordable sufficient evidence sets and weak traps.
- Moderate: fewer sufficient sets or an important relational dependency.
- Hard: narrow evidence paths, stronger distractors, or multiple dependencies.

Difficulty may not be assigned retrospectively from confirmation performance.

## 5. Generator validity rules

A task enters a study split only if all mechanical checks pass:

1. Exactly one candidate is correct.
2. No individual clue identifies the answer by itself.
3. At least three relevant clues are required.
4. Every sufficient set spans at least two catalogue regions.
5. At least one solution path costs no more than 60 of 100 evidence units.
6. Cheap-only acquisition does not reliably solve the task.
7. Expensive-only acquisition does not mechanically reveal the answer without relational interpretation.
8. Every coordination trap has an affordable disconfirmation path reachable with the verification reserve.
9. Candidate position, identifiers, ordering, prices, wording templates, missing fields, and text length do not reveal correctness.
10. The task remains valid independently of the tested collective topology.
11. Regeneration from the same version and seed is deterministic.

Rejected candidates and their rejection reasons are retained. Rejection may never depend on observed agent performance.

## 6. Resource economy

Resources affect what agents can do; telemetry records what they did. Telemetry is complete, external to the agents, and is not a scarce resource.

### 6.1 Evidence prices

- Cheap query: 1 unit.
- Moderate query: 3 units.
- Expensive query: 8 units.

Agents know the price and source category before purchase but not the evidence content or its usefulness.

### 6.2 Evidence allowance

Each condition receives 100 total evidence units:

- Four-agent collective conditions: 20 private units per investigator plus a 20-unit shared verification reserve.
- Independent voting: 25 private units per investigator.
- Single agent: 100 units, with 20 notionally reserved for final verification.

Queries are charged when issued, including failed, duplicated, or unhelpful queries. Unspent private units are not transferable in the initial protocol.

### 6.3 Information boundaries

An agent sees its briefing, public catalogue and prices, acquired evidence, remaining allowance, and protocol-authorized messages. It cannot see hidden ground truth, evaluator state, scientific telemetry, another agent’s private evidence, or unpurchased evidence.

## 7. Model and work allowance

The provisional model is `gpt-6.1-sol` at medium reasoning effort, subject to recording the exact model identifier and environment metadata available when the protocol is implemented. Every initial condition uses the same model and reasoning setting. Cross-model testing requires a later B3 protocol.

Each trial permits at most nine model turns:

- Strong single agent: up to nine sequential turns.
- Independent voting: two turns per agent; deterministic aggregation; the ninth turn remains unused.
- Independent plus synthesizer: two private turns per investigator and one synthesis turn.
- Communicating collective: one private investigation turn and one revision/communication turn per investigator, plus one synthesis turn.

Text ceilings are:

- initial investigator report: 250 words;
- private self-check or communication revision: 100 words;
- final answer: 250 words.

The same model, reasoning setting, briefing, tool permissions, and total visible-output allowance apply across conditions. Under a Pro-only environment, exact hidden reasoning-token use may be unavailable. The first study is therefore described as **exploratory and procedurally matched**, not as definitive exact-compute confirmation. Visible input/output, calls, tool use, failures, and elapsed time are recorded when available.

## 8. Canonical episode

1. All agents receive the same briefing, observed failure, candidates, evidence catalogue, and prices.
2. Investigators acquire evidence within their private allowances.
3. Each investigator records a diagnosis, candidate probabilities, acquired evidence identifiers, key reasoning, strongest alternative, and recommended verification.
4. The condition-specific communication or aggregation phase occurs.
5. Where applicable, the synthesizer spends the shared verification reserve and records the reason for each query.
6. The final decision-maker submits a candidate probability distribution, selected diagnosis, acquired evidence relied upon, and concise causal explanation.
7. The deterministic external evaluator scores the final output after agent activity ends.

## 9. Experimental conditions

### 9.1 Baseline 1 — strong equal-budget single agent

One persistent agent receives all 100 evidence units and up to nine sequential turns. It may plan, revisit assumptions, self-critique, and revise. Evidence is notionally staged across four investigation blocks of up to 20 units followed by up to 20 units for verification; unused units carry forward.

After each block it records its candidate probabilities, evidence, unresolved questions, next plan, and strongest alternative.

### 9.2 Baseline 2 — independent ensemble with fixed aggregation

Four isolated agents receive 25 evidence units each and cannot communicate. Each returns candidate probabilities, a diagnosis, evidence identifiers, and rationale.

Final probabilities are the arithmetic mean of member probabilities. The maximum-probability candidate wins. Exact ties follow a preregistered candidate-order rule. No model synthesizer is used.

### 9.3 Baseline 3 — independent investigators plus synthesizer

Four isolated investigators receive 20 evidence units each and two private turns. They never see one another’s reports and cannot revise in response to peers.

A synthesizer receives their sealed reports, may spend the 20-unit verification reserve, and produces the final distribution and diagnosis.

### 9.4 Condition 4 — communicating collective

Four investigators receive 20 evidence units each. After private investigation, reports are shared. Each investigator may identify disagreement, missing evidence, duplication, or suspected error and submit one constrained revision or verification recommendation.

The synthesizer receives original reports and revisions, spends up to 20 verification units, and produces the final answer.

The difference between Conditions 3 and 4 is the structured peer-information and revision round. This isolates the marginal effect of communication.

### 9.5 Constituent comparisons

Every investigator submits a pre-communication diagnosis and probability distribution. The study reports mean constituent performance, the performance of any role designated as strongest using development data, and oracle-best member performance as a descriptive upper bound. Oracle post-hoc selection is not a deployable baseline.

## 10. Scoring

### 10.1 Primary outcome

The primary outcome is Brier loss over the five candidates:

`L = Σ_k (p_k - y_k)^2`

Lower is better. Perfect prediction has loss 0; uniform abstention has loss 0.8; a maximally confident wrong prediction has loss 2.

Ordinary accuracy is a secondary outcome.

### 10.2 Output validation

Probabilities must cover all candidates, lie in `[0, 1]`, and sum to `[0.99, 1.01]`. Values within that rounding tolerance are normalized deterministically. Outputs outside it are malformed.

### 10.3 Failure treatment

- Explicit abstention: uniform distribution; loss 0.8.
- Timeout or missing final answer: loss 2 and accuracy 0.
- Malformed probability output: loss 2 and accuracy 0.
- Agent-caused tool misuse or budget exhaustion: ordinary trial failure.
- Unsupported evidence citation: protocol violation; report both raw diagnostic score and integrity-adjusted loss 2.
- Infrastructure failure before usable agent work: preserve the trial and apply the preregistered infrastructure-failure rule; any rerun receives a new identity.

### 10.4 Secondary outcomes

- evidence efficiency;
- relevant-evidence coverage;
- duplicate spending;
- unspent allowance;
- verification-reserve value;
- communication cost;
- unsupported claims and citations;
- communication compression loss;
- premature consensus;
- performance by class and difficulty;
- incomplete and failed-trial frequency.

## 11. Exploratory statistical plan

The primary comparison is communicating collective versus strong equal-budget single agent on the same tasks.

For each task:

`d_i = L_single,i - L_collective,i`

Positive values favour the collective.

The exploratory study uses:

- paired permutation test for mean Brier-loss difference;
- 90% confidence interval over the paired mean difference;
- exact McNemar test for paired accuracy;
- two-sided exploratory significance threshold `α = 0.10`.

A provisional collective advantage requires all of:

1. Mean Brier improvement of at least 0.10.
2. Paired permutation `p < 0.10`.
3. The 90% confidence interval for improvement excludes zero.
4. Collective accuracy is not materially worse than the single-agent baseline.
5. The result is not driven solely by one task class or a few extreme trials.
6. The advantage remains under integrity-adjusted scoring.
7. Failures are reported and do not explain the result.

This is suggestive exploratory evidence, not definitive confirmation. Any later confirmation uses fresh data, 95% confidence, `α = 0.05`, a prospectively selected sample size, and preferably metered inference.

## 12. Data separation

### 12.1 Engineering tasks

Engineering tasks verify implementation, logging, interfaces, scoring, and failure handling. They may be inspected freely and never enter scientific performance statistics.

### 12.2 Development set

The development set contains nine tasks: three additive, three relational, and three coordination-trap tasks. It may be used to calibrate prices, prompts, report formats, ambiguity, baseline behaviour, runtime, and resource use. All protocol changes occur here. These tasks never enter evaluation.

### 12.3 Exploratory evaluation set

The evaluation set contains thirty fresh tasks: ten per class, with three easy, four moderate, and three hard tasks within each class. Every condition receives the same instances. Once evaluation begins, prompts, budgets, aggregation, scoring, and failure definitions remain frozen.

### 12.4 Seed governance

Before evaluation:

1. Freeze the generator version.
2. Generate an evaluation master seed.
3. Record a cryptographic commitment to that seed.
4. Derive task seeds from generator version, split, task index, and master seed.
5. Keep evaluation seeds and hidden worlds outside agent-readable storage.
6. Reveal and archive the seed after evaluation.

### 12.5 Invalidation and reruns

An evaluation task may be invalidated only for a prespecified structural defect: multiple correct answers, no affordable solution, corrupted evidence, evaluator error, or independently confirmed metadata leakage. Invalidation applies across all conditions, retains all trial records, and is reported. Primary analyses do not silently replace invalidated tasks.

Failures, malformed answers, timeouts, and agent mistakes are not silently rerun. Infrastructure reruns have new trial identities and are reported separately.

## 13. Minimal protocol-integrity boundary

This is a scientific-validity boundary, not an adversarial-security programme. Prompt-injection challenges and deliberate adversarial dynamics are out of scope for B0.

Before evaluation, the harness must demonstrate:

1. Agent-facing tools cannot retrieve hidden ground truth, generator state, evaluator state, or inaccessible files.
2. Over-budget queries are rejected, logged, and return no evidence.
3. One investigator cannot retrieve another’s private state or evidence.
4. Every clue records task, query, cost, purchaser, and acquisition time.
5. Acquired citations can be distinguished from fabricated citations.
6. Missing, negative, excessive, non-numeric, and non-normalized probabilities cannot improve scores.
7. Re-evaluating the same final answer produces the same score.
8. Crashes and timeouts preserve messages, queries, costs, and failure state.
9. Metadata-only heuristics do not predict the answer above chance across a large generated audit sample.
10. Trial configuration, graph, and scoring cannot change after trial start.

Agents access evidence only through an allowlisted query interface. The evaluator runs after agent activity and exposes no intermediate score.

## 14. Interpretation constraints

- Beating the average constituent alone is ensemble gain, not sufficient evidence of collective intelligence.
- Beating an observed best member without a valid preregistered selection rule is insufficient.
- More evidence or compute does not count as a collective advantage.
- A benefit attributable only to independent sampling is an ensemble effect.
- A benefit from centralized synthesis without peer revision is a synthesis effect.
- The contrast between the communicating collective and independent-plus-synthesizer condition estimates the value of structured communication.
- Reward hacking, unsupported evidence claims, evaluator shortcuts, and systematic failures are reported as results.
- Results apply only to the declared model, protocol, budget, generator distribution, and environment.
- Null and negative results remain scientifically valid outcomes.

## 15. Approval gates and next milestone

This document consolidates B0 planning. Before implementation or execution:

1. Conduct scientific review of construct validity, fairness, and confounds.
2. Approve or revise this protocol as a new version.
3. Approve a separate B1 harness design.
4. Implement and test the harness only after explicit authorization.
5. Perform a dry run only after explicit authorization.
6. Execute exploratory trials only after separate explicit authorization.

B1 must specify deterministic seeds, append-only event and message logs, configuration hashes, environment capture, unique outputs, incomplete-run preservation, replay verification, tamper tests, and sandboxing. B1 implementation does not itself authorize experimental execution.

## 16. Engineering amendment 0.1-A

On 2026-11-01, the user authorized implementation of the auditable harness and a capped engineering dry run intended to produce preliminary infrastructure and cost results. This does not authorize the 30-task exploratory evaluation.

The engineering adapter uses OpenRouter with model identifier `openai/gpt-6.1-sol` and medium reasoning effort. The existing credential remains outside this worktree and must never be copied into logs, source files, or model prompts. OpenRouter provider metadata, token usage, reported cost when available, and model identifier are recorded per request.

Engineering tasks and all outputs produced before a later evaluation freeze are permanently excluded from scientific evaluation. Deviations discovered during engineering must be documented and corrected through a new protocol version before evaluation.

### Engineering compute-calibration amendment 0.1-B

The first completed engineering comparison showed that the communicating collective consumed 6.15 times the provider-reported tokens of the single agent. Its performance result is therefore compute-invalid.

Further engineering comparisons use a provisional target of 20,000 provider-reported total tokens per condition with a calibration tolerance of ±15%. Native private or synthesis review calls may use the remaining allowance, but they must not introduce communication into the independent-vote condition or expose hidden evidence. Every run records an automatic compute-validity assessment. This wide tolerance is only for harness calibration; it does not authorize evaluation. Before exploratory evaluation, a new reviewed protocol must reduce the tolerance and freeze condition-specific allocation rules.

### Pre-evaluation hardening amendment 0.1-C

The harness now requests strict JSON Schema output for every report-producing call and requires OpenRouter routing to an endpoint advertising support for the requested parameters. Local semantic validation remains authoritative: provider acceptance of a schema does not replace candidate, probability-sum, citation, or evidence-budget checks.

The engineering per-call completion ceiling is 1,400 tokens. A 700-token structured-output smoke produced incomplete JSON, demonstrating that schema enforcement cannot prevent truncation at an undersized completion ceiling. Provider finish reasons are now retained in the append-only ledger and attached to parse failures.

Generated engineering tasks use deterministic generator version `generated-0.3`. Hidden construction metadata records evidence roles, formal single-clue candidate compatibility, relational pairs and phase markers, a multi-region sufficient set, and (for coordination traps) an affordable verification set. Generation rejects individual clues or ordinary clue pairs that uniquely identify truth, invalid evidence composition, duplicate metadata, asymmetric or phase-inconsistent relational pairs, insufficient region diversity, over-budget solution paths, cheap-only or expensive-only designated solutions, and over-budget trap verification. Version `generated-0.2` was retired after its first smoke test exposed inconsistent phase assignment. Version `generated-0.2.1` then exposed a distribution leak because `none_of_the_above` was never true. Both are preserved as engineering-invalid histories. Version `generated-0.3` balances every correct label and displayed position over each 25-seed cycle. The generator remains engineering-only until its class-specific causal semantics, difficulty manipulation, wording diversity, split derivation, and rejection archive receive a separate review.

Constituent failure handling is fixed as follows for engineering calibration:

- A missing or malformed independent voter contributes the uniform five-candidate distribution to the deterministic arithmetic mean. It is never silently dropped.
- Missing reports are passed to a synthesizer as explicit null entries, and valid/failed constituent counts are recorded in the condition result.
- A malformed revision leaves the agent's last valid private report in place and records the revision error.
- A missing or malformed final report still receives loss 2 and accuracy 0 under Section 10.3.

New engineering comparisons initially defaulted to a 20,000-token target with a ±10% provider-reported total-token envelope. The first four-condition `generated-0.3` calibration showed that the communicating protocol's required investigation, four revision calls, and synthesis naturally consumed 25,485 tokens while all baselines fell inside the 18,000–22,000 envelope. That comparison is compute-invalid and is not interpreted. Prospectively, engineering calibration uses a 25,000-token target with the same ±10% envelope; baselines may use additional private, non-communicating audit calls to reach the floor. The earlier ledgers retain their original recorded interpretation. This remains an engineering calibration rule, not authorization for the thirty-task evaluation; evaluation requires a frozen allocation rule and a separately reviewed final tolerance.

### Causal-generator development amendment 0.1-D

The template generator remains available as `generated-0.3` so its engineering ledgers remain reproducible. It is not eligible for exploratory evaluation. A separate development generator, `causal-1.0-dev`, represents tasks as explicit fault, latent, nuisance, and observation nodes plus a finite weighted set of possible worlds. An exact oracle conditions those worlds on purchased evidence and computes candidate posteriors without model judgment.

The causal task classes are structurally distinct:

- **Additive:** independently informative channels reveal separate candidate-signature dimensions. The true candidate requires three accumulated dimensions.
- **Relational:** each reference or trace has zero marginal information about the fault; the XOR of a paired reference and trace reveals one signature dimension. Three pairs are required.
- **Coordination trap:** correlated cached proxies favour a specified wrong candidate. Provenance reveals the shared stale source, while calibrated physical measurements provide an affordable disconfirmation path.

Difficulty is assigned mechanically from the exact oracle. Easy, moderate, and hard cells have class-specific minimum sufficient costs and path multiplicities. Easy cells must have at least four equally cheap sufficient paths. Moderate and hard cells must have exactly one cheapest path; hard cells additionally use the highest class-specific sufficient cost and remove cheap substitute paths. Current development targets are additive `3/9/24`, relational `6/18/48`, and coordination-trap `4/12/17` for easy/moderate/hard minimum sufficient cost respectively.

Candidate mappings are not present in the public briefing. They are disclosed piecemeal only in purchased evidence. This rule was added after a manual audit found that a public full codebook exposed the structurally central true signature. Before evaluation, `causal-1.0-dev` still requires a larger seed audit, automated metadata/text leakage probes, frozen renderer templates, an append-only rejection archive, and a signed evaluation manifest. This amendment does not authorize model-backed causal-task runs or the thirty-task evaluation.

### Causal freeze amendment 0.1-E

On 2026-11-11, the expanded offline audit and public-view leakage gates passed. The frozen generator identifier is `causal-1.0`; changing from the development identifier changes deterministic layouts and therefore requires a new full audit rather than relabelling earlier tasks. Frozen source, protocol, audit, threshold, renderer, probe, and harness hashes are recorded in detached Ed25519-signed manifests.

The sealed development split contains one easy, one moderate, and one hard task from each causal class. Its nine seeds are derived from a development master seed committed inside the signed development manifest. These tasks are authorized only for protocol and compute calibration and are permanently excluded from evaluation.

The evaluation configuration manifest freezes the planned thirty-task distribution and harness configuration but contains no evaluation seed, seed commitment, hidden world, or task fingerprint. Its status remains `frozen_but_not_authorized_seed_not_generated`. Creating or signing that configuration does not authorize the exploratory evaluation. Evaluation seed generation, commitment, and execution require a later explicit authorization after the development run is reviewed.

### Development infrastructure amendment 0.1-F

The first sealed development campaign completed the three additive tasks and three conditions of the relational-easy task before an OpenRouter response exceeded the 180-second HTTP read timeout. The failed task ledger and all incurred cost remain preserved. This was an infrastructure timeout, not a malformed report or an agent mistake.

Prospectively, sealed development requests use a 300-second read timeout. Infrastructure retries use a new attempt number and output ledger, retain the original failed attempt, and are identified in the campaign ledger. Explicit start-index and attempt controls may resume the signed development task list without changing its master seed, task seeds, causal fingerprints, or public fingerprints. This amendment applies only to development; it does not authorize evaluation or silent scientific-trial reruns.
