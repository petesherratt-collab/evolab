# Causal 1.4: report reliability and evidence-grounded coordination

Status: prospective development protocol. Evaluation remains seedless and locked.

The causal-1.3 run failed promotion: collective mean Brier 0.554002 versus
single-agent 0.211952, two malformed scored reports, and three failed voting
constituents. Relational hard included a missing collective report scored at
the maximum loss. These observations do not isolate reasoning quality from
formatting failures, and do not prove that communication caused the losses.
The apparent difficulty gradient is descriptive on only three tasks per band.

## Changes

Keep the causal-1.3 generator and evidence allocation. Use a fresh development
master seed with a causal-1.4 derivation namespace, one task per class/band cell.
Retain the generator's existing 45-case mechanical audit as generator evidence;
it is not an audit of the new strategy. Test the new harness separately.

All nine tasks and all four conditions use the same 25,000–30,000 token bounds,
27,500 target, and existing 18-request limit. Increase per-call completion cap
from 1,000 to 1,800 and minimum from 96 to 512 within those bounds. Reasoning
tokens share the completion cap; this change is a hypothesis about reducing
truncation, not a guarantee of valid output.

If optional evidence acquisition cannot fit, release only the current episode's
reserve and preserve reserves for later participants. If an episode has no
valid report, permit exactly one tool-free recovery using only its purchased
evidence. Recovery is charged to the same request and token budget. Original
errors, recovery outcome, usage and cost remain recorded. Invalid optional
reviews continue to preserve the last valid report, as in the earlier harness.

The coordinator receives the scout's report alongside the acquisition
proposals. Shared evidence remains the only source of observations. Apply the
same evidence-discipline instruction to every condition: resolve routing,
polarity and joint dependencies before combining evidence; require purchased
evidence to justify a diagnosis change; do not treat agent confidence as proof.
No automatic confidence-based override or reference to the answer key is used.

## Promotion and interpretation

The six existing gates remain unchanged: 9/9 compute-eligible; no malformed
final reports, unsupported citations, failed constituents or evidence-budget
violations; single mean Brier >= 0.12; collective improvement >= 0.10 over
single and >= 0.05 over synthesis; collective lower than both on >= 6/9 tasks.
Report recovered failures separately. Do not perform significance tests on
development tasks. Multiple simultaneous changes mean a successful run would
validate the combined protocol, not identify an individual causal mechanism.

Stop after the first failed task. No automatic paid retries. Before execution,
freeze source hashes, fresh task fingerprints, model configuration and a dollar
budget. The previous campaign's $3.50 envelope has only $0.1237686 remaining;
a fresh campaign requires a separate spending allocation. Expected cost based
on the previous final pair is roughly $3–$4, with uncertainty from the larger
completion cap and recovery calls. Proposed new campaign ceiling: $5.
