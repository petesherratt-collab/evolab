from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from evolutionary_lab.evidence import verify_ledger


CONDITION_ORDER = (
    "single_agent",
    "independent_vote",
    "independent_synthesizer",
    "communicating_collective",
)


def _load_run(path: Path) -> dict[str, Any]:
    verification = verify_ledger(path)
    if not verification["valid"]:
        raise ValueError(f"INVALID_LEDGER_CHAIN: {path}")
    records = [
        json.loads(line)["payload"]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    completed = [record for record in records if record.get("kind") == "run_complete"]
    if len(completed) != 1:
        raise ValueError(f"EXPECTED_ONE_RUN_COMPLETE: {path}")
    return {
        "path": str(path),
        "verification": verification,
        "run": completed[0],
    }


def _comparison(values: Iterable[tuple[float, float]]) -> dict[str, Any]:
    pairs = tuple(values)
    differences = tuple(left - right for left, right in pairs)
    epsilon = 1e-12
    return {
        "tasks": len(pairs),
        "mean_brier_improvement": sum(differences) / len(differences),
        "target_lower": sum(value > epsilon for value in differences),
        "tied": sum(abs(value) <= epsilon for value in differences),
        "target_higher": sum(value < -epsilon for value in differences),
        "task_differences": list(differences),
    }


def _aggregate(runs: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_task: dict[str, dict[str, dict[str, Any]]] = {}
    for item in runs:
        task_id = item["run"]["task_id"]
        by_task[task_id] = {}
        for result in item["run"]["results"]:
            grouped[result["condition"]].append(result)
            by_task[task_id][result["condition"]] = result

    conditions: dict[str, Any] = {}
    for condition in CONDITION_ORDER:
        results = grouped[condition]
        losses = [float(result["score"]["brier_loss"]) for result in results]
        tokens = [float(result["usage"]["total_tokens"]) for result in results]
        conditions[condition] = {
            "tasks": len(results),
            "accuracy": sum(bool(result["score"]["accurate"]) for result in results)
            / len(results),
            "mean_brier_loss": sum(losses) / len(losses),
            "median_brier_loss": median(losses),
            "mean_total_tokens": sum(tokens) / len(tokens),
            "minimum_total_tokens": min(tokens),
            "maximum_total_tokens": max(tokens),
            "mean_evidence_spent": sum(
                float(result["evidence_spent"]) for result in results
            )
            / len(results),
            "total_reported_cost": sum(
                float(result["usage"].get("cost", 0.0)) for result in results
            ),
            "recorded_errors": sum(len(result["errors"]) for result in results),
            "failed_constituents": sum(
                int(result["failed_constituents"]) for result in results
            ),
            "malformed_reports": sum(
                bool(result["score"]["malformed"]) for result in results
            ),
            "unsupported_citations": sum(
                len(result["score"]["unsupported_citations"]) for result in results
            ),
        }

    def pairs(reference: str, target: str) -> Iterable[tuple[float, float]]:
        for task in by_task.values():
            yield (
                float(task[reference]["score"]["brier_loss"]),
                float(task[target]["score"]["brier_loss"]),
            )

    contrasts = {
        "collective_vs_single": _comparison(
            pairs("single_agent", "communicating_collective")
        ),
        "collective_vs_independent_synthesizer": _comparison(
            pairs("independent_synthesizer", "communicating_collective")
        ),
        "collective_vs_independent_vote": _comparison(
            pairs("independent_vote", "communicating_collective")
        ),
    }
    return {"conditions": conditions, "contrasts": contrasts}


def summarize_v11(paths: list[Path], campaign_ledger: Path | None = None) -> dict[str, Any]:
    runs = [_load_run(path) for path in paths]
    eligible = [item for item in runs if item["run"]["compute_assessment"]["eligible"]]
    task_rows = []
    for item in runs:
        run = item["run"]
        parts = run["task_id"].split("-")
        results = {result["condition"]: result for result in run["results"]}
        task_rows.append(
            {
                "task_id": run["task_id"],
                "task_class": "coordination_trap"
                if "coordination" in run["task_id"]
                else parts[2],
                "difficulty": parts[-2],
                "compute_eligible": bool(run["compute_assessment"]["eligible"]),
                "condition_brier_loss": {
                    condition: float(results[condition]["score"]["brier_loss"])
                    for condition in CONDITION_ORDER
                },
                "condition_accurate": {
                    condition: bool(results[condition]["score"]["accurate"])
                    for condition in CONDITION_ORDER
                },
                "condition_total_tokens": {
                    condition: float(results[condition]["usage"]["total_tokens"])
                    for condition in CONDITION_ORDER
                },
                "ledger": item["path"],
                "ledger_verification": item["verification"],
            }
        )

    campaign = None
    if campaign_ledger is not None:
        campaign_verification = verify_ledger(campaign_ledger)
        if not campaign_verification["valid"]:
            raise ValueError("INVALID_CAMPAIGN_LEDGER_CHAIN")
        records = [
            json.loads(line)["payload"]
            for line in campaign_ledger.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        checkpoints = [
            record
            for record in records
            if record.get("kind") == "causal_v11_campaign_checkpoint"
        ]
        if len(checkpoints) != 1:
            raise ValueError("EXPECTED_ONE_CAMPAIGN_CHECKPOINT")
        checkpoint_summary = checkpoints[0]["summary"]
        expected_ledgers = {str(path.resolve()) for path in paths}
        checkpoint_ledgers = {
            str(Path(path).resolve()) for path in checkpoint_summary["task_ledgers"]
        }
        if checkpoint_ledgers != expected_ledgers:
            raise ValueError("CAMPAIGN_TASK_LEDGER_SET_MISMATCH")
        if not checkpoint_summary["selected_complete"]:
            raise ValueError("CAMPAIGN_NOT_COMPLETE")
        campaign = {
            "path": str(campaign_ledger),
            "verification": campaign_verification,
            "summary": checkpoint_summary,
        }

    return {
        "campaign": campaign,
        "integrity": {
            "task_ledgers": len(runs),
            "valid_task_ledgers": sum(item["verification"]["valid"] for item in runs),
            "task_ledger_records": sum(
                int(item["verification"]["records"]) for item in runs
            ),
            "compute_eligible_tasks": len(eligible),
            "compute_ineligible_task_ids": [
                item["run"]["task_id"]
                for item in runs
                if not item["run"]["compute_assessment"]["eligible"]
            ],
        },
        "eligible_only": _aggregate(eligible),
        "all_tasks_sensitivity": _aggregate(runs),
        "tasks": task_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate completed causal-1.1 development ledgers"
    )
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--campaign-ledger", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = summarize_v11(args.paths, args.campaign_ledger)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
