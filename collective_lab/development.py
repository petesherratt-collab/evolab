from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from evolutionary_lab.evidence import verify_ledger

from .causal_generator import generate_causal_case
from .freeze import verify_manifest
from .ledger import ExclusiveRunLedger
from .runner import run_engineering_task


@dataclass(frozen=True)
class DevelopmentRunSummary:
    manifest_payload_sha256: str
    tasks_declared: int
    tasks_completed: int
    task_ledgers: tuple[str, ...]
    total_reported_cost: float
    failures: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return self.tasks_completed == self.tasks_declared and not self.failures

    def mapping(self) -> dict[str, object]:
        return {
            "manifest_payload_sha256": self.manifest_payload_sha256,
            "tasks_declared": self.tasks_declared,
            "tasks_completed": self.tasks_completed,
            "task_ledgers": list(self.task_ledgers),
            "total_reported_cost": self.total_reported_cost,
            "failures": list(self.failures),
            "complete": self.complete,
        }


def _read_records(path: Path) -> list[dict[str, Any]]:
    verify_ledger(path)
    records = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line)["payload"])
    return records


def _completed_task_cost(path: Path) -> float:
    records = _read_records(path)
    completed = [item for item in records if item.get("kind") == "run_complete"]
    if len(completed) != 1:
        raise ValueError(f"DEVELOPMENT_TASK_INCOMPLETE: {path}")
    results = completed[0].get("results", [])
    return sum(
        float(dict(result).get("usage", {}).get("cost", 0.0))
        for result in results
    )


def run_development_set(
    *,
    manifest: str | Path,
    signature: str | Path,
    public_key: str | Path,
    output_directory: str | Path,
    campaign_ledger: str | Path,
    model: str = "openai/gpt-6.1-sol",
    max_tasks: int | None = None,
    start_index: int = 0,
    attempt: int = 0,
) -> DevelopmentRunSummary:
    manifest_path = Path(manifest).resolve()
    signature_path = Path(signature).resolve()
    public_key_path = Path(public_key).resolve()
    verification = verify_manifest(manifest_path, signature_path, public_key_path)
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = document["payload"]
    if payload.get("manifest_type") != "development":
        raise ValueError("DEVELOPMENT_MANIFEST_TYPE_INVALID")
    if payload.get("status") != "sealed_development_authorized":
        raise ValueError("DEVELOPMENT_MANIFEST_NOT_AUTHORIZED")
    if model != payload["harness"]["model"]:
        raise ValueError("DEVELOPMENT_MODEL_MISMATCH")

    output_dir = Path(output_directory).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = Path(campaign_ledger).resolve()
    manifest_reference = {
        "path": str(manifest_path),
        "payload_sha256": str(verification["payload_sha256"]),
        "signature_sha256": hashlib.sha256(signature_path.read_bytes()).hexdigest(),
        "signing_key_fingerprint": str(verification["signing_key_fingerprint"]),
    }
    tasks = list(payload["tasks"])
    if start_index < 0 or attempt < 0:
        raise ValueError("DEVELOPMENT_RESUME_ARGUMENT_INVALID")
    remaining = [task for task in tasks if int(task["task_index"]) >= start_index]
    selected = remaining if max_tasks is None else remaining[:max_tasks]
    completed_ledgers: list[str] = []
    failures: list[str] = []
    total_cost = 0.0

    with ExclusiveRunLedger(ledger_path) as campaign:
        campaign.append(
            {
                "kind": "development_campaign_started",
                "manifest_reference": manifest_reference,
                "tasks_declared": len(tasks),
                "tasks_selected_this_run": len(selected),
                "start_index": start_index,
                "attempt": attempt,
            }
        )
        for task_spec in selected:
            index = int(task_spec["task_index"])
            task_class = str(task_spec["task_class"])
            difficulty = str(task_spec["difficulty"])
            seed = int(task_spec["seed"])
            case = generate_causal_case(seed, task_class, difficulty)
            if case.causal_task.fingerprint() != task_spec["causal_fingerprint"]:
                raise ValueError(f"DEVELOPMENT_TASK_FINGERPRINT_INVALID: {index}")
            attempt_suffix = f"-attempt-{attempt}" if attempt else ""
            task_path = output_dir / (
                f"task-{index:02d}-{task_class}-{difficulty}-{seed}"
                f"{attempt_suffix}.jsonl"
            )
            if task_path.exists():
                try:
                    cost = _completed_task_cost(task_path)
                except ValueError as exc:
                    failures.append(str(exc))
                    campaign.append(
                        {
                            "kind": "development_task_blocked",
                            "task_index": index,
                            "ledger": str(task_path),
                            "reason": str(exc),
                        }
                    )
                    break
                completed_ledgers.append(str(task_path))
                total_cost += cost
                campaign.append(
                    {
                        "kind": "development_task_reused",
                        "task_index": index,
                        "ledger": str(task_path),
                        "reported_cost": cost,
                    }
                )
                continue

            campaign.append(
                {
                    "kind": "development_task_started",
                    "task_index": index,
                    "task_class": task_class,
                    "difficulty": difficulty,
                    "seed": seed,
                    "task_fingerprint": task_spec["causal_fingerprint"],
                    "ledger": str(task_path),
                }
            )
            try:
                results = run_engineering_task(
                    case.task,
                    output=task_path,
                    model=model,
                    conditions=tuple(payload["conditions"]),
                    max_tokens=int(payload["harness"]["max_completion_tokens"]),
                    max_tool_rounds=int(payload["harness"]["max_tool_rounds"]),
                    seed=20261111 + index * 1000,
                    target_tokens=int(payload["harness"]["target_provider_reported_tokens"]),
                    compute_tolerance=float(payload["harness"]["compute_tolerance"]),
                    manifest_reference=manifest_reference,
                    request_timeout_seconds=int(
                        payload["harness"]["request_timeout_seconds"]
                    ),
                )
            except Exception as exc:
                reason = f"{type(exc).__name__}: {exc}"
                failures.append(reason)
                campaign.append(
                    {
                        "kind": "development_task_failed",
                        "task_index": index,
                        "ledger": str(task_path),
                        "reason": reason[:2000],
                    }
                )
                break
            cost = sum(float(result.usage.get("cost", 0.0)) for result in results)
            completed_ledgers.append(str(task_path))
            total_cost += cost
            campaign.append(
                {
                    "kind": "development_task_completed",
                    "task_index": index,
                    "ledger": str(task_path),
                    "reported_cost": cost,
                }
            )

        summary = DevelopmentRunSummary(
            manifest_payload_sha256=str(verification["payload_sha256"]),
            tasks_declared=len(tasks),
            tasks_completed=len(completed_ledgers),
            task_ledgers=tuple(completed_ledgers),
            total_reported_cost=total_cost,
            failures=tuple(failures),
        )
        campaign.append({"kind": "development_campaign_checkpoint", "summary": summary.mapping()})
    return summary


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the sealed nine-task development set")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--signature", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--campaign-ledger", type=Path, required=True)
    parser.add_argument("--model", default="openai/gpt-6.1-sol")
    parser.add_argument("--max-tasks", type=int)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--attempt", type=int, default=0)
    args = parser.parse_args()
    summary = run_development_set(
        manifest=args.manifest,
        signature=args.signature,
        public_key=args.public_key,
        output_directory=args.output_directory,
        campaign_ledger=args.campaign_ledger,
        model=args.model,
        max_tasks=args.max_tasks,
        start_index=args.start_index,
        attempt=args.attempt,
    )
    print(json.dumps(summary.mapping(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
