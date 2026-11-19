# Experimental design corrections implemented

19 November 2026. New version: causal-1.6-dev. No provider calls or spending.

## Changes

- Separated matched-evidence reasoning from evidence-acquisition coordination.
  The four reasoning conditions receive identical packets. The primary contrast
  is communicating investigators versus independent investigators followed by
  synthesis, with matched perspectives and five calls each.
- Replaced fragmented investigator wallets with one shared wallet in the
  separate single/team acquisition comparison. Complete dependency routes are
  affordable; duplicate observations are charged once.
- Sampled complete true worlds from their declared integer weights, including
  misleading regimes and nuisance states. Public instructions now disclose the
  numerical probability model. The old faithful-world selection is discarded.
- Made purchase and finish decisions explicit. An affordable declared remaining
  bundle requires either a purchase or acknowledged deliberate early stopping.
  Reports cannot silently close acquisition. Limits and denied actions are logged.
- Separated tied diagnosis labels from unique correct probability leaders, and
  added diagnostics for missing information, interpretation error and calibration.
- Replaced minimum-token padding with a common 30,000-token ceiling. Actual
  usage remains visible; no claim of exact realized compute matching is made.

## Validation

The standard unittest suite passed **91 tests**, including 17 new version-1.6
tests. The four separate pytest acquisition-audit tests also passed: **95 total**.

The new offline audit passed all **18 cases**, covering every class/band at two
layout seeds. It checked **8,800 possible worlds and 840 distinct evidence
packets**, including public decoding, exact conditional probabilities, complete
route affordability, sampler boundaries and class-specific information structure.
Four of the 18 selected worlds were misleading regimes; they were retained.

Signed manifests were checked for canonical payload hashes, signatures, source
hashes and audit hashes: all three 1.5 manifests and both new 1.6 manifests
verified. Historical experimental sources and results were not edited.

## Prepared state and limits

Nine new development tasks are frozen, one per class/band, with separate layout
and world seeds, packet IDs, evidence budgets and condition orders. The proposed
30-task evaluation still has no seeds or task instances. Both new manifests
have `execution_authorized=false` and an authorized spend of **$0**.

This verifies experimental mechanics, not model efficacy. No live 1.6 model
results exist yet. The next operational step is a separately bounded pilot
launcher with a source check and an explicit dollar ceiling. A new evaluation
analysis/precision plan is required before generating evaluation seeds; there
is no automatic promotion. The failed 1.5 promotion verdict remains unchanged.

Full design: `CAUSAL_1_6_DEVELOPMENT_DESIGN.md`.

Machine-readable records:

- `collective_runs/CAUSAL_V16_OFFLINE_AUDIT_20261119.json`
- `collective_runs/CAUSAL_V16_FREEZE_VERIFICATION_20261119.json`
- `collective_runs/FROZEN_DEVELOPMENT_MANIFEST_CAUSAL_1_6_PREPARED.json`
- `collective_runs/FROZEN_EVALUATION_CONFIGURATION_CAUSAL_1_6_PREPARED.json`
