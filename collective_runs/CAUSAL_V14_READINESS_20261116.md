# Causal 1.4 offline readiness

Implemented the prospective strategy in `CAUSAL_1_4_DEVELOPMENT_DESIGN.md`.
Historical causal-1.3 sources and results were preserved.

Validation completed:

- Full regression suite: 69 passed, 80 subtests passed (195.15 seconds).
- Eight new tests cover uniform compute bounds, preservation of future-role
  reserves, request-limit enforcement, one-attempt recovery, cost/token
  accounting, retained original errors, evidence isolation and scout handoff.
- A simulated-client integration check exercised all four conditions with
  valid final reports and a valid ledger chain. Compute matching was disabled
  for this smoke check; it is not evidence of live token sufficiency or efficacy.
- Both prepared manifest signatures verify and all frozen source hashes match.
- Nine fresh seeds cover the nine class/difficulty cells, with no seed overlap
  with the causal-1.3 development set.
- Attempting to execute the prepared manifest is rejected before client
  creation because execution is not authorized.
- Evaluation master seed and task list remain absent.

No live model calls were made during this preparation. Historical spend remains
$3.3762314. Based on the previous campaign's final pair, the fresh nine-task run
is estimated at $3–$4; larger completion caps and recovery create uncertainty.
Proposed separate allocation: $5. The old $3.50 allocation has $0.1237686 left.

The existing generator's 45/45 mechanical audit is carried forward explicitly
as generator evidence, not as validation of the new strategy. Live compute
sufficiency, report reliability and promotion gates remain untested for v1.4.

Next execution should use the signed prepared development manifest, authorize
it only after the new spending allocation is settled, monitor all billed calls
(including incomplete attempts), and stop on the first task failure. No
automatic paid retries or evaluation execution are authorized by preparation.
