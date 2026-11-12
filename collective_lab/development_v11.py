from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import platform
import sys
from typing import Any

from evolutionary_lab.evidence import verify_ledger

from .causal_generator_v11 import generate_causal_case_v11
from .freeze import verify_manifest
from .ledger import ExclusiveRunLedger
from .openrouter import OpenRouterClient
from .protocol_v11 import ComputePlan, V11_CONDITIONS
from .runner import ConditionResult, compute_assessment
from .runner_v11 import HarnessV11


@dataclass(frozen=True)
class DevelopmentV11Summary:
    manifest_payload_sha256: str
    tasks_declared: int
    tasks_selected: int
    tasks_completed: int
    task_ledgers: tuple[str, ...]
    total_reported_cost: float
    failures: tuple[str, ...]

    @property
    def selected_complete(self) -> bool:
        return self.tasks_completed == self.tasks_selected and not self.failures

    def mapping(self) -> dict[str, object]:
        return {**asdict(self), "selected_complete": self.selected_complete}


def _canonical_hash(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_payloads(path: Path) -> list[dict[str, Any]]:
    verify_ledger(path)
    return [
        json.loads(line)["payload"]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _completed_cost(path: Path) -> float:
    complete = [
        payload for payload in _read_payloads(path)
        if payload.get("kind") == "run_complete"
    ]
    if len(complete) != 1:
        raise ValueError(f"CAUSAL_V11_TASK_INCOMPLETE: {path}")
    return sum(
        float(dict(result).get("usage", {}).get("cost", 0.0))
        for result in complete[0].get("results", [])
    )


def run_v11_task(
    case,
    *,
    output: Path,
    model: str,
    manifest_reference: dict[str, str],
    max_tokens: int,
    max_tool_rounds: int,
    seed: int,
    request_timeout_seconds: int,
    compute_plan: ComputePlan,
) -> list[ConditionResult]:
    if output.exists():
        raise FileExistsError(f"CAUSAL_V11_OUTPUT_EXISTS: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    task = case.task
    config = {
        "phase": "causal_v11_development",
        "model": model,
        "conditions": list(V11_CONDITIONS),
        "max_tokens": max_tokens,
        "max_tool_rounds": max_tool_rounds,
        "seed": seed,
        "request_timeout_seconds": request_timeout_seconds,
        "manifest_reference": manifest_reference,
        "evidence_budget": case.evidence_budget,
        "minimum_path_costs": list(case.minimum_path_costs),
        "adaptive_branch": (
            asdict(case.adaptive_branch) if case.adaptive_branch else None
        ),
        "compute_plan": compute_plan.mapping(),
    }
    config_hash = _canonical_hash(config)
    results: list[ConditionResult] = []
    with ExclusiveRunLedger(output) as ledger:
        ledger.append(
            {
                "kind": "run_started",
                "config": config,
                "config_hash": config_hash,
                "task_id": task.task_id,
                "task_fingerprint": task.fingerprint(),
                "causal_fingerprint": case.causal_task.fingerprint(),
                "environment": {
                    "python": sys.version,
                    "platform": platform.platform(),
                },
            }
        )
        harness = HarnessV11(
            OpenRouterClient(
                model=model,
                timeout_seconds=request_timeout_seconds,
            ),
            ledger,
            max_tokens=max_tokens,
            max_tool_rounds=max_tool_rounds,
            seed=seed,
        )
        try:
            for condition in V11_CONDITIONS:
                results.append(
                    harness.run_condition(
                        task,
                        condition,
                        evidence_budget=case.evidence_budget,
                        minimum_path_costs=case.minimum_path_costs,
                        target_tokens=compute_plan.target_tokens,
                        tolerance=compute_plan.tolerance,
                        compute_plan=compute_plan,
                    )
                )
        except Exception as exc:
            ledger.append(
                {
                    "kind": "run_failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:2000],
                }
            )
            raise
        ledger.append(
            {
                "kind": "run_complete",
                "task_id": task.task_id,
                "results": [result.mapping() for result in results],
                "compute_assessment": compute_assessment(
                    results,
                    compute_plan.target_tokens,
                    compute_plan.tolerance,
                ),
            }
        )
    return results


def run_development_set_v11(
    *,
    manifest: str | Path,
    signature: str | Path,
    public_key: str | Path,
    output_directory: str | Path,
    campaign_ledger: str | Path,
    start_index: int = 0,
    max_tasks: int | None = None,
    attempt: int = 0,
) -> DevelopmentV11Summary:
    manifest_path = Path(manifest).resolve()
    signature_path = Path(signature).resolve()
    public_key_path = Path(public_key).resolve()
    verification = verify_manifest(manifest_path, signature_path, public_key_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))["payload"]
    if payload.get("manifest_type") != "causal_v11_development":
        raise ValueError("CAUSAL_V11_MANIFEST_TYPE_INVALID")
    if payload.get("status") != "sealed_development_authorized":
        raise ValueError("CAUSAL_V11_DEVELOPMENT_NOT_AUTHORIZED")
    if start_index < 0 or attempt < 0:
        raise ValueError("CAUSAL_V11_RESUME_ARGUMENT_INVALID")

    harness = dict(payload["harness"])
    compute_plan = ComputePlan(**dict(harness["compute_plan_parameters"]))
    manifest_reference = {
        "path": str(manifest_path),
        "payload_sha256": str(verification["payload_sha256"]),
        "signature_sha256": hashlib.sha256(signature_path.read_bytes()).hexdigest(),
        "signing_key_fingerprint": str(verification["signing_key_fingerprint"]),
    }
    tasks = list(payload["tasks"])
    remaining = [task for task in tasks if int(task["task_index"]) >= start_index]
    selected = remaining if max_tasks is None else remaining[:max_tasks]
    output_dir = Path(output_directory).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    completed: list[str] = []
    failures: list[str] = []
    total_cost = 0.0

    with ExclusiveRunLedger(Path(campaign_ledger).resolve()) as campaign:
        campaign.append(
            {
                "kind": "causal_v11_campaign_started",
                "manifest_reference": manifest_reference,
                "tasks_declared": len(tasks),
                "tasks_selected": len(selected),
                "start_index": start_index,
                "attempt": attempt,
            }
        )
        for spec in selected:
            index = int(spec["task_index"])
            task_class = str(spec["task_class"])
            difficulty = str(spec["difficulty"])
            task_seed = int(spec["seed"])
            case = generate_causal_case_v11(task_seed, task_class, difficulty)
            if case.causal_task.fingerprint() != spec["causal_fingerprint"]:
                raise ValueError(f"CAUSAL_V11_TASK_FINGERPRINT_INVALID: {index}")
            if _canonical_hash(case.task.public()) != spec["public_fingerprint"]:
                raise ValueError(f"CAUSAL_V11_PUBLIC_FINGERPRINT_INVALID: {index}")
            if case.evidence_budget != int(spec["evidence_budget"]):
                raise ValueError(f"CAUSAL_V11_TASK_BUDGET_INVALID: {index}")
            if list(case.minimum_path_costs) != list(spec["minimum_path_costs"]):
                raise ValueError(f"CAUSAL_V11_PATH_COSTS_INVALID: {index}")

            suffix = f"-attempt-{attempt}" if attempt else ""
            task_path = output_dir / (
                f"task-{index:02d}-{task_class}-{difficulty}-{task_seed}{suffix}.jsonl"
            )
            if task_path.exists():
                try:
                    cost = _completed_cost(task_path)
                except ValueError as exc:
                    failures.append(str(exc))
                    campaign.append(
                        {
                            "kind": "causal_v11_task_blocked",
                            "task_index": index,
                            "ledger": str(task_path),
                            "reason": str(exc),
                        }
                    )
                    break
                completed.append(str(task_path))
                total_cost += cost
                campaign.append(
                    {
                        "kind": "causal_v11_task_reused",
                        "task_index": index,
                        "ledger": str(task_path),
                        "reported_cost": cost,
                    }
                )
                continue

            campaign.append(
                {
                    "kind": "causal_v11_task_started",
                    "task_index": index,
                    "task_class": task_class,
                    "difficulty": difficulty,
                    "seed": task_seed,
                    "ledger": str(task_path),
                }
            )
            try:
                results = run_v11_task(
                    case,
                    output=task_path,
                    model=str(harness["model"]),
                    manifest_reference=manifest_reference,
                    max_tokens=int(harness["max_completion_tokens"]),
                    max_tool_rounds=int(harness["max_tool_rounds"]),
                    seed=20261200 + index * 1000,
                    request_timeout_seconds=int(harness["request_timeout_seconds"]),
                    compute_plan=compute_plan,
                )
            except Exception as exc:
                reason = f"{type(exc).__name__}: {exc}"
                failures.append(reason)
                campaign.append(
                    {
                        "kind": "causal_v11_task_failed",
                        "task_index": index,
                        "ledger": str(task_path),
                        "reason": reason[:2000],
                    }
                )
                break
            cost = sum(float(result.usage.get("cost", 0.0)) for result in results)
            completed.append(str(task_path))
            total_cost += cost
            campaign.append(
                {
                    "kind": "causal_v11_task_completed",
                    "task_index": index,
                    "ledger": str(task_path),
                    "reported_cost": cost,
                }
            )

        summary = DevelopmentV11Summary(
            manifest_payload_sha256=str(verification["payload_sha256"]),
            tasks_declared=len(tasks),
            tasks_selected=len(selected),
            tasks_completed=len(completed),
            task_ledgers=tuple(completed),
            total_reported_cost=total_cost,
            failures=tuple(failures),
        )
        campaign.append(
            {"kind": "causal_v11_campaign_checkpoint", "summary": summary.mapping()}
        )
    return summary


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run a sealed causal-1.1 development split")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--signature", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--campaign-ledger", type=Path, required=True)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--max-tasks", type=int)
    parser.add_argument("--attempt", type=int, default=0)
    args = parser.parse_args()
    print(
        json.dumps(
            run_development_set_v11(
                manifest=args.manifest,
                signature=args.signature,
                public_key=args.public_key,
                output_directory=args.output_directory,
                campaign_ledger=args.campaign_ledger,
                start_index=args.start_index,
                max_tasks=args.max_tasks,
                attempt=args.attempt,
            ).mapping(),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
