# Evolutionary Strategy Lab v0.1

An offline framework for an AI-assisted evolutionary strategy experiment.

The local model is a proposal generator. Deterministic code owns the strategy
grammar, execution rules, backtest, fitness calculation and evidence ledger.
This first version uses a random generator so the scientific instrument can be
tested before adding Gemma, Qwen or another model backend.

## Current boundary

- Synthetic market data only.
- Virtual capital only; no broker, exchange or live trading connection.
- Long/flat moving-average strategies only.
- One-step execution lag and explicit transaction fees.
- Chronological train, validation and test splits.
- Append-only, SHA-256 hash-chained generation snapshots.
- Frozen outcome records with an observation cutoff and source hash.
- Linux resource telemetry when available: RAM, swap, load, process CPU and temperatures.
- No claim that historical performance predicts future profitability.

The simulator is an authority for exact outcomes under its stated assumptions,
not an authority about future markets.

## Run the baseline

From this directory:

```bash
python3 -m unittest discover -s tests -t . -v
python3 -m evolutionary_lab.demo
```

The demo writes generation snapshots to `runs/baseline.jsonl`. Existing
evidence is appended to rather than overwritten. Verify the chain with:

```bash
python3 -c 'from evolutionary_lab.evidence import verify_ledger; print(verify_ledger("runs/baseline.jsonl"))'
```

Use a different output path for a new run:

```bash
python3 -m evolutionary_lab.demo \
  --seed 20260927 \
  --population 24 \
  --generations 12 \
  --output runs/run-001.jsonl
```

## Architecture

1. `StrategySpec` is the closed strategy language and rejects malformed fields.
2. `DeterministicBacktester` replays a strategy without future bars in its signal history.
3. `EvolutionRunner` ranks candidates using return, drawdown, turnover and complexity.
4. `TelemetrySample` records the computing environment around each generation.
5. `EvidenceLedger` freezes every generation as a hash-chained JSONL record.
6. `FrozenOutcome` records what was observed after a candidate was frozen,
   keeping the outcome boundary separate from evolutionary selection.

The protected boundary is deliberate: a future model adapter may propose
strategies, but it may not modify the simulator, scoring rules, or frozen
outcomes during a run.  The trading backtester remains a first domain adapter;
the outcome record is intended to be reusable for other deterministic arenas.

## Next safe extension

Add a model adapter that emits JSON matching `StrategySpec`, preserve its raw
responses, and run it beside the random baseline. Do not add live data or real
capital until the deterministic engine, leakage tests, baselines and holdout
protocol are independently trustworthy.
