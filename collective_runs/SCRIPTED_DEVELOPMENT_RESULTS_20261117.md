# Code-only condition on the sealed development split — results

**Date:** 2026-11-17. **Scope:** the nine sealed development tasks; protocol
calibration only (amendment 0.1-G). **Evaluation status:** not authorized and
not run. **Provider cost:** none.

## Result

`scripted_code` gave Brier loss 0 and the correct diagnosis on all nine tasks.
On each it spent exactly the class's minimum sufficient cost
(additive 3/9/24, relational 6/18/48, coordination trap 4/12/17), with two
scripted calls, no tokens and no cost.

| Task | Min cost | Code only: loss / spend | Single | Vote | Synthesizer | Communicating |
|---|---:|---|---|---|---|---|
| Additive / easy | 3 | 0 / 3 | 0.003414 / 8 | 0.001821 / 26 | 0.001198 / 28 | 0.000294 / 28 |
| Additive / moderate | 9 | 0 / 9 | 0.004896 / 49 | 0.008228 / 84 | 0.014118 / 44 | 0.000818 / 53 |
| Additive / hard | 24 | 0 / 24 | 0.029400 / 64 | 0 / 96 | 0 / 76 | 0 / 76 |
| Relational / easy | 6 | 0 / 6 | 0 / 22 | 0.000021 / 72 | 0 / 24 | 0 / 24 |
| Relational / moderate | 18 | 0 / 18 | 0 / 34 | 0 / 72 | 0 / 72 | 0 / 72 |
| Relational / hard | 48 | 0 / 48 | 0 / 64 | 0.611306 / 99 | 0 / 96 | 0 / 96 |
| Trap / easy | 4 | 0 / 4 | 0.000542 / 19 | 0.001152 / 28 | 0.000128 / 28 | 0.000512 / 33 |
| Trap / moderate | 12 | 0 / 12 | 0.028800 / 29 | 0.001162 / 60 | 0.012800 / 52 | 0.002048 / 52 |
| Trap / hard | 17 | 0 / 17 | 0.033200 / 39 | 0.001341 / 83 | 0.000512 / 80 | 0.002048 / 97 |

Model columns are loss / evidence spent, from the recorded 2026-11-11
campaign (relational-easy from its completed retry). Each model condition used
about 23,000 provider-reported tokens per task; the campaign cost about $2.47.

## Reading

No model condition beat the code-only floor on any task, on loss or on
evidence spent. This sharpens the 2026-11-11 finding that the tasks are too
easy: in `causal-1.0` the evidence text is templated and names the candidate
groups outright, so a short program that reads only the public view recovers
the exact posterior at minimum cost. Whatever the collective adds cannot show
on this distribution.

For the next generator version this gives a concrete gate, beside the ones
already recommended (scarcer budgets, near-miss worlds, adaptive evidence
choice, stronger traps): a task is useful for comparing model conditions only
if `scripted_code`, or a stronger script, does not already solve it. Features
that defeat a template reader, such as varied wording, mappings that must be
inferred rather than read, and noisy channels that need weighing, are what
would give the models something to do.

The script was written with knowledge of the templates. That is what a
programmer would have, and is the point of the floor; it is not a blind test.

| Artifact | SHA-256 |
|---|---|
| `collective_runs/scripted-development-20261117-summary.json` | `ae60d7a64b26b06ae1055c288063bd5b0c6f7726729f150aa0850d340e4d66f6` |
