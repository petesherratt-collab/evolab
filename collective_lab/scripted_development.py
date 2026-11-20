"""Run the code-only condition on the sealed development split. No provider call.

The nine sealed development tasks are rebuilt from the signed manifest, their
fingerprints checked, and each is run once through the ordinary harness with
``ScriptedClient`` under the condition ``scripted_code``. Ledgers are written
next to, never over, the model campaign's. A summary sets the code-only Brier
loss and evidence spend beside the four model conditions' recorded results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys

from evolutionary_lab.evidence import verify_ledger

from .causal_generator import generate_causal_case
from .freeze import verify_manifest
from .ledger import ExclusiveRunLedger
from .runner import Harness
from .scripted import SCRIPTED_MODEL, ScriptedClient, run_scripted_condition


def _payloads(path: Path) -> list[dict]:
    verify_ledger(path)
    return [json.loads(line)["payload"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def model_results(directory: Path, index: int) -> dict[str, dict]:
    """The four model conditions' results for one task, from its completed ledger
    (the retry, where the first attempt failed)."""
    for path in sorted(directory.glob(f"task-{index:02d}-*.jsonl")):
        done = [p for p in _payloads(path) if p.get("kind") == "run_complete"]
        if done:
            return {r["condition"]: r for r in done[0]["results"]}
    return {}


def run(manifest: Path, signature: Path, public_key: Path, output_directory: Path,
        model_directory: Path) -> dict:
    verification = verify_manifest(manifest, signature, public_key)
    payload = json.loads(manifest.read_text(encoding="utf-8"))["payload"]
    if payload.get("status") != "sealed_development_authorized":
        raise ValueError("DEVELOPMENT_MANIFEST_NOT_AUTHORIZED")
    output_directory.mkdir(parents=True, exist_ok=True)
    rows = []
    for spec in payload["tasks"]:
        index = int(spec["task_index"])
        case = generate_causal_case(int(spec["seed"]), spec["task_class"], spec["difficulty"])
        if case.causal_task.fingerprint() != spec["causal_fingerprint"]:
            raise ValueError(f"DEVELOPMENT_TASK_FINGERPRINT_INVALID: {index}")
        task = case.task
        path = output_directory / f"task-{index:02d}-{spec['task_class']}-{spec['difficulty']}-scripted.jsonl"
        config = {"phase": "development_code_only", "model": SCRIPTED_MODEL,
                  "conditions": ["scripted_code"], "manifest_payload_sha256": verification["payload_sha256"]}
        with ExclusiveRunLedger(path) as ledger:
            ledger.append({
                "kind": "run_started", "config": config,
                "config_hash": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
                "task_id": task.task_id, "task_fingerprint": task.fingerprint(),
                "environment": {"python": sys.version, "platform": platform.platform()},
            })
            result = run_scripted_condition(Harness(ScriptedClient(), ledger), task)
            ledger.append({"kind": "run_complete", "task_id": task.task_id, "results": [result.mapping()],
                           "compute_assessment": {"eligible": None, "reason": "NO_MODEL_COMPUTE"}})
        models = model_results(model_directory, index)
        rows.append({
            "task_index": index, "task_class": spec["task_class"], "difficulty": spec["difficulty"],
            "minimum_sufficient_cost": payload["difficulty_minimum_sufficient_costs"]
            .get(spec["task_class"], {}).get(spec["difficulty"]),
            "scripted": {"brier": result.score.brier_loss, "accurate": result.score.accurate,
                         "evidence_spent": result.evidence_spent, "api_requests": result.api_requests,
                         "tokens": result.usage.get("total_tokens", 0.0)},
            "models": {name: {"brier": r["score"]["brier_loss"], "accurate": r["score"]["accurate"],
                              "evidence_spent": r["evidence_spent"],
                              "tokens": r["usage"].get("total_tokens", 0.0),
                              "cost": r["usage"].get("cost", 0.0)}
                       for name, r in models.items()},
            "ledger": path.name,
        })
    return {"manifest_payload_sha256": verification["payload_sha256"], "tasks": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--signature", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--model-directory", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    if args.summary.exists():
        parser.error("summary exists; evidence is never overwritten")
    summary = run(args.manifest, args.signature, args.public_key, args.output_directory,
                  args.model_directory)
    args.summary.write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
