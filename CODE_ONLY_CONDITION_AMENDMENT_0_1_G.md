# Code-only condition amendment 0.1-G (development only)

**Date:** 2026-11-17. **Status:** development use only; does not authorize
evaluation.

This amendment sits beside `COLLECTIVE_INTELLIGENCE_B0_PROTOCOL.md` rather than
inside it, because that file's hash, and the harness source's, are recorded in
the signed development and evaluation manifests. Editing them would break the
manifests' verification. Nothing frozen is changed: the four model conditions,
the generator, `runner.py`, the manifests and the evaluation configuration are
as they were.

## What is added

A fifth condition, `scripted_code`, suggested by the owner as a code-only arm
with no provider cost. It runs through the ordinary harness (its evidence
tool, budget accounting, ledger and `score_report`) with `ScriptedClient`
(`collective_lab/scripted.py`) in place of the model client.

It stands for a programmer who has read the task templates and writes an
ordinary program:

- it sees only what an agent sees: the public briefing, the catalogue
  descriptions and the results of evidence it buys; it never reads hidden
  worlds, the correct candidate or the oracle;
- it buys the cheapest route the descriptions name: the direct channel for each
  signature bit (additive); the three cheapest reference and trace pairs
  (relational); the polarity calibration and the three physical measurements
  (coordination trap);
- it intersects the candidate sets the results name, applying the XOR and the
  polarity correction, and reports a uniform distribution over what remains;
- one episode on the single agent's 100-unit budget, no review calls, no
  tokens, and therefore outside the compute-matching envelope.

## Offline checker

The exact oracle checks the script: `tests/test_scripted.py` asserts, for every
class and difficulty, that the script's distribution equals the oracle
posterior on the evidence it bought, and that its spend equals the class's
minimum sufficient cost. The condition is a floor that costs nothing: a model
condition is worth its compute only where it beats this program.

## The one run this amendment covers

`collective_lab/scripted_development.py` runs the condition once on the nine
sealed development tasks, rebuilt from the signed V2 development manifest with
fingerprints checked. Amendment 0.1-E allows these tasks for protocol
calibration. Ledgers go to `collective_runs/scripted-development-20261117/`;
the summary sets the code-only result beside the four model conditions'
recorded results. No provider call is made.

Source hashes before that run:

| File | SHA-256 |
|---|---|
| `collective_lab/scripted.py` | `619f1091f09b012279974e87a44b6ca48c6f45320e39a8b60e8b1561255dd002` |
| `collective_lab/scripted_development.py` | `b9145743c38d703807ff03f0d644cc593d77b175699a0ae270e08b5b69819e16` |
| `tests/test_scripted.py` | `06455b1a6dcdbfff58667388c339fdff5aa3c2d5033600c4cfa00505c9f248aa` |
