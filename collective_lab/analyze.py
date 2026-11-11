from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any

from evolutionary_lab.evidence import verify_ledger


def load_completed_run(path: Path) -> dict[str, Any]:
    verification = verify_ledger(path)
    complete = None
    for line in path.read_text(encoding="utf-8").splitlines():
        payload = json.loads(line)["payload"]
        if payload.get("kind") == "run_complete":
            complete = payload
    if complete is None:
        raise ValueError(f"RUN_COMPLETE_MISSING: {path}")
    return {"path": str(path), "verification": verification, "run": complete}


def summarize(paths: list[Path]) -> dict[str, Any]:
    runs = [load_completed_run(path) for path in paths]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in runs:
        if not item["run"]["compute_assessment"]["eligible"]:
            raise ValueError(f"COMPUTE_ASSESSMENT_INELIGIBLE: {item['path']}")
        for result in item["run"]["results"]:
            grouped[result["condition"]].append(result)
    aggregate = {}
    for condition, results in sorted(grouped.items()):
        aggregate[condition] = {
            "tasks": len(results),
            "accuracy": sum(result["score"]["accurate"] for result in results) / len(results),
            "mean_brier_loss": sum(result["score"]["brier_loss"] for result in results) / len(results),
            "mean_total_tokens": sum(result["usage"]["total_tokens"] for result in results) / len(results),
            "total_reported_cost": sum(result["usage"].get("cost", 0.0) for result in results),
            "recorded_errors": sum(len(result["errors"]) for result in results),
        }
    collective = aggregate.get("communicating_collective")
    single = aggregate.get("single_agent")
    synthesizer = aggregate.get("independent_synthesizer")
    contrasts = {}
    if collective and single:
        contrasts["collective_minus_single_brier_improvement"] = (
            single["mean_brier_loss"] - collective["mean_brier_loss"]
        )
    if collective and synthesizer:
        contrasts["communication_over_synthesis_brier_improvement"] = (
            synthesizer["mean_brier_loss"] - collective["mean_brier_loss"]
        )
    return {"runs": runs, "aggregate": aggregate, "contrasts": contrasts}


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate valid compute-eligible engineering ledgers")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.paths), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
