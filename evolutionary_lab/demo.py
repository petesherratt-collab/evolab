from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evidence import EvidenceLedger
from .evolution import EvolutionConfig, EvolutionRunner
from .market import chronological_split, synthetic_market


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the offline evolutionary strategy baseline")
    parser.add_argument("--seed", type=int, default=20260927)
    parser.add_argument("--bars", type=int, default=360)
    parser.add_argument("--population", type=int, default=24)
    parser.add_argument("--generations", type=int, default=12)
    parser.add_argument("--output", default="runs/baseline.jsonl")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    bars = synthetic_market(seed=args.seed, count=args.bars)
    splits = chronological_split(bars)
    ledger = EvidenceLedger(Path(args.output))
    config = EvolutionConfig(
        population_size=args.population,
        generations=args.generations,
        seed=args.seed,
    )
    result = EvolutionRunner(splits, config=config, ledger=ledger).run()
    print(json.dumps(result.summary(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
