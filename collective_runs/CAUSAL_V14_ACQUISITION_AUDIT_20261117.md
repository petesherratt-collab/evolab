# Causal 1.4 offline acquisition audit

Completed 17 November 2026. No model calls, new task seeds or evaluation access.
All nine original task worlds were regenerated from the authorized development
manifest; fingerprints matched their specifications and recorded ledgers.
All nine input ledger chains verified. Historical results remain unchanged.

## Diagnosis

There are three distinct problems: acquisition ends before affordable follow-up
evidence is bought; the routed generator removes some public interpretation
instructions; and some reports remain uninformative despite a complete planned
route. This is not evidence that the solution is simply a larger compute budget.

### 1. Two tool rounds turn an affordable plan into an unfinished plan

The harness offers evidence tools at rounds 0 and 1, then requires a report at
round 2. Its later private reviews cannot acquire evidence. A model may buy
multiple items per call, but several reports and deliberator proposals recommend
sequential purchases and reassessment. That plan cannot finish within two calls
when the router consumes one call and remaining purchases are made individually.

Across the nine tasks, all nine single-agent episodes and eight of nine final
coordinator episodes ended at the configured tool-round limit. The remaining
coordinator ended earlier after completing its planned route. None of these
18 final diagnostic episodes used the compute-reservation fallback; the five
fallback events occurred elsewhere in the independent-agent conditions.

Nine of these 18 final results lacked part of the generator's planned route.
Every one had enough remaining evidence budget to purchase that missing part,
and every corresponding episode reached the tool-round limit.

| Task | Condition | Spent / available | Cost to finish planned route | Outcome |
|---|---|---:|---:|---|
| Additive moderate | Collective | 7 / 11 | 3 | Route incomplete |
| Additive hard | Collective | 18 / 28 | 8 | Route incomplete |
| Relational moderate | Single | 2 / 20 | 18 | Uniform report |
| Relational moderate | Collective | 5 / 20 | 15 | Uniform report |
| Relational hard | Single | 18 / 52 | 32 | Partial discrimination |
| Relational hard | Collective | 18 / 52 | 32 | Partial discrimination |
| Coordination moderate | Single | 7 / 14 | 6 | Uniform report |
| Coordination moderate | Collective | 7 / 14 | 6 | Uniform report |
| Coordination hard | Single | 11 / 21 | 8 | Uniform report |

The relational-moderate trace makes the problem concrete. The single agent
bought routing registry E05 for 1 unit, then E17 for 1 unit. Tools were removed
at round 2 with 18 units left. Its report named the six remaining active-lane
items as recommended verification. The collective's coordinator bought E17,
then E20, and lost tool access with 15 units left; its report recommended the
five remaining active-lane items. The proposals explicitly recognized that
all six active lanes plus E17 fit the budget.

The single agent then spent **178,416 of 236,955 tokens (75.30%)** across the
nine tasks on tool-free private reviews, including recovery. The collective
spent 17,939 of 237,666 tokens (7.55%) on those calls. Equal total tokens did not
mean equal opportunities to acquire evidence. More reviews cannot reveal an
unpurchased reference or calibration.

This establishes the actual stopping mechanism. It does not prove that extra
rounds would improve scores: the collective already consumes much of its token
budget before its final report. A fix needs to rebalance planning and acquisition
within a fixed envelope, or support suitable batches, rather than just append
more calls.

### 2. The public task contract loses interpretation metadata

The base relational generator labels evidence as reference/trace members of
numbered diagnostic pairs and explains XOR in the briefing. The routed wrapper
replaces those descriptions with generic lane-option descriptions, and replaces
the briefing with generic acquisition instructions. Trace outcomes still say
"Combine with this pair's reference" but do not identify the pair.

For relational moderate, the active references are E20 (phase 1), E18 (phase 0)
and E07 (phase 0). Traces E14, E02 and E11 disclose XOR candidate mappings but
not which reference belongs to each trace. Internally the generator knows the
pairings. The displayed lane labels do not explicitly define that relationship,
and the catalogue warns against inferring diagnostic value from order.

The wrapper also removes the earlier class-specific calibration explanation,
the reliability-regime warning, and the hard-task branch A/B probe descriptions.
Purchased results retain some interpretation information, but public sufficiency
has not been established by the existing mechanical oracle audit.

Therefore **an oracle-sufficient hidden world is not by itself a sufficiently
specified public task**. This is a generator-contract defect that should be
addressed before attributing every failure to model reasoning. The observed
relational runs also missed evidence, so the present audit cannot quantify how
much of their loss arose from missing pair identifiers alone.

### 3. Complete acquisition can still yield an uncertain report

The single agent on additive hard bought its entire planned route for 26 units
but returned a uniform distribution. The collective on coordination hard also
bought its full route for 19 units and returned uniform probabilities.

On coordination hard, the purchased record contains:

- E01: the active lane registry;
- E14: branch B is active;
- E03: normal polarity;
- E17, E12 and E16: physical bits and their candidate compatibility lists.

The three disclosed candidate lists intersect at `actuator_stiction`. The
collective nevertheless said that branch-conditioned joint interpretation and
shared dependencies remained undisclosed, and declined to use their overlap.
The exact generator posterior on the acquired set assigns the true candidate
0.555556, compared with the report's 0.2.

The protocol's blanket caution about marginal intersections and unresolved
dependencies is a plausible contributor. It does not distinguish combining
explicit compatibility constraints from multiplying correlated probabilities.
The missing public class instructions are another plausible contributor.
This audit identifies the discrepancy; it does not establish either hypothesis
as the sole cause or imply that the model could reproduce hidden oracle weights.

## Recommended correction order

1. Restore sufficient public interpretation instructions. Reveal pair identifiers
   and branch/probe relationships with purchased results or paid routing data;
   retain class-specific combination and calibration rules. Preserve uncertainty
   about unpurchased values and avoid revealing the true diagnosis. Add tests of
   what the public representation discloses, beyond private-oracle solvability.
2. Make acquisition plans executable within the tool schedule. Teach every
   condition the actual call limit and batch capability. Purchase known required
   bundles when affordable; permit adaptive follow-up when the branch cannot be
   known in advance. Reallocate tool-free review tokens rather than silently
   increasing the overall budget.
3. Narrow the reasoning caution. Permit explicitly defined XOR, calibration and
   compatibility operations once their prerequisites are available. Distinguish
   those operations from unsupported independence assumptions.
4. Improve observability in the next version: record requested IDs, denied IDs
   and reasons, explicit stop reasons, and tools offered/disabled. The current
   ledger records successful purchases but cannot reveal every attempted or
   rejected purchase.
5. Test the revised public interface and acquisition schedule offline before
   freezing another fresh development split. Keep the existing promotion gates
   and the locked evaluation unchanged. Use separate ablations if the objective
   is to identify which correction caused any improvement.

## Scope and reproducibility

`collective_lab/acquisition_audit_v14.py` produces the companion JSON from the
authorized manifest and original task directory. The JSON includes regenerated
catalogues, purchased-result text, episode call boundaries, budgets, missing
planned-route items, exact posteriors, proposals and final reports. This is
privileged development analysis and must never be supplied as agent input.

The planned route is one sufficient route, not necessarily the only possible
solution. Oracle posteriors use a joint distribution unavailable to the agents.
Pooled independent evidence is an analytical upper bound, not an individual
agent's information set. No counterfactual model outcomes were generated.

Two focused tests of stop classification passed. The completed audit verified
all nine regenerated fingerprints and ledger chains. The live harness and its
signed configuration were not edited, so no new live-harness regression run was
needed. Current campaign spend remains $2.7361679, with $2.2638321 unused.
