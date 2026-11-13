from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
from typing import Any

from .adaptive_v11 import adaptive_choice_metrics
from .causal_generator import CAUSAL_TASK_CLASSES, DIFFICULTIES
from .causal_generator_v11 import (
    CAUSAL_GENERATOR_V11_VERSION,
    generate_causal_case_v11,
)
from .protocol_v12 import (
    CAUSAL_V12_PROTOCOL_VERSION,
    ComputePlanV12,
    V12_CONDITIONS,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    "CAUSAL_1_2_DEVELOPMENT_PROTOCOL.md",
    "pyproject.toml",
    "collective_lab/causal.py",
    "collective_lab/causal_generator.py",
    "collective_lab/causal_generator_v11.py",
    "collective_lab/adaptive_v11.py",
    "collective_lab/oracle.py",
    "collective_lab/core.py",
    "collective_lab/runner.py",
    "collective_lab/runner_v11.py",
    "collective_lab/openrouter.py",
    "collective_lab/ledger.py",
    "collective_lab/protocol_v11.py",
    "collective_lab/protocol_v12.py",
    "collective_lab/runner_v12.py",
    "collective_lab/causal_audit_v12.py",
    "collective_lab/development_v12.py",
    "collective_lab/freeze_v12.py",
    "tests/test_causal_v12.py",
)


@dataclass(frozen=True)
class PreparedFreezeV12Artifacts:
    development_manifest: Path
    development_signature: Path
    evaluation_configuration: Path
    evaluation_signature: Path
    signing_key_fingerprint: str


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_manifest(path: Path, payload: dict[str, Any]) -> None:
    document = {
        "payload": payload,
        "payload_sha256": _sha256_bytes(_canonical(payload)),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sign(path: Path, private_key: Path) -> Path:
    signature = path.with_suffix(path.suffix + ".sig")
    subprocess.run(
        [
            "openssl",
            "pkeyutl",
            "-sign",
            "-rawin",
            "-inkey",
            str(private_key),
            "-in",
            str(path),
            "-out",
            str(signature),
        ],
        check=True,
    )
    return signature


def _signing_key_fingerprint(public_key: Path) -> str:
    der = subprocess.check_output(
        ["openssl", "pkey", "-pubin", "-in", str(public_key), "-outform", "DER"]
    )
    return _sha256_bytes(der)


def derive_v12_task_seed(
    master_seed: str,
    *,
    split: str,
    task_class: str,
    difficulty: str,
    task_index: int,
) -> int:
    material = (
        f"{CAUSAL_V12_PROTOCOL_VERSION}|{CAUSAL_GENERATOR_V11_VERSION}|{split}|"
        f"{task_class}|{difficulty}|{task_index}|{master_seed}"
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def create_prepared_freeze_v12(
    *,
    audit_summary: str | Path,
    private_key: str | Path,
    public_key: str | Path,
    development_manifest: str | Path,
    evaluation_configuration: str | Path,
    development_master_seed: str | None = None,
) -> PreparedFreezeV12Artifacts:
    audit_path = Path(audit_summary).resolve()
    private_key_path = Path(private_key).resolve()
    public_key_path = Path(public_key).resolve()
    development_path = Path(development_manifest).resolve()
    evaluation_path = Path(evaluation_configuration).resolve()
    for output in (development_path, evaluation_path):
        if output.exists() or output.with_suffix(output.suffix + ".sig").exists():
            raise FileExistsError(f"CAUSAL_V12_FREEZE_OUTPUT_EXISTS: {output}")

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if not audit.get("passed"):
        raise ValueError("CAUSAL_V12_FREEZE_AUDIT_NOT_ELIGIBLE")
    if audit.get("protocol_version") != CAUSAL_V12_PROTOCOL_VERSION:
        raise ValueError("CAUSAL_V12_FREEZE_PROTOCOL_VERSION_INVALID")
    if audit.get("generator_lineage") != CAUSAL_GENERATOR_V11_VERSION:
        raise ValueError("CAUSAL_V12_FREEZE_GENERATOR_LINEAGE_INVALID")

    signing_fingerprint = _signing_key_fingerprint(public_key_path)
    compute_plan = ComputePlanV12()
    common = {
        "schema": "collective-intelligence-causal-v12-prepared-v1",
        "protocol_version": CAUSAL_V12_PROTOCOL_VERSION,
        "generator_lineage": CAUSAL_GENERATOR_V11_VERSION,
        "generator_version": CAUSAL_GENERATOR_V11_VERSION,
        "source_sha256": {
            name: _sha256_file(ROOT / name) for name in SOURCE_FILES
        },
        "audit": {
            "summary_path": str(audit_path.relative_to(ROOT)),
            "summary_sha256": _sha256_file(audit_path),
            "ledger_head": audit["ledger_head"],
            "attempted": audit["attempted"],
            "accepted": audit["accepted"],
            "rejected": audit["rejected"],
        },
        "signing": {
            "algorithm": "Ed25519",
            "public_key_path": str(public_key_path.relative_to(ROOT)),
            "public_key_sha256": _sha256_file(public_key_path),
            "public_key_der_sha256": signing_fingerprint,
        },
        "task_classes": list(CAUSAL_TASK_CLASSES),
        "difficulties": list(DIFFICULTIES),
        "conditions": list(V12_CONDITIONS),
        "harness": {
            "model": "openai/gpt-6.1-sol",
            "reasoning_effort": "medium",
            "max_completion_tokens": compute_plan.max_completion_tokens,
            "max_tool_rounds": 2,
            "request_timeout_seconds": 300,
            "primary_metric": "five_class_brier_loss",
            "compute_plan_parameters": asdict(compute_plan),
            "compute_plan": compute_plan.mapping(),
            "evidence_allocation": (
                "v11_controls_and_shared_scout_deliberate_coordinate_collective"
            ),
        },
    }

    master_seed = development_master_seed or secrets.token_hex(32)
    tasks: list[dict[str, object]] = []
    task_index = 0
    for task_class in CAUSAL_TASK_CLASSES:
        for difficulty in DIFFICULTIES:
            seed = derive_v12_task_seed(
                master_seed,
                split="development",
                task_class=task_class,
                difficulty=difficulty,
                task_index=task_index,
            )
            case = generate_causal_case_v11(seed, task_class, difficulty)
            adaptive = (
                adaptive_choice_metrics(
                    case.causal_task, case.adaptive_branch
                ).mapping()
                if case.adaptive_branch
                else None
            )
            tasks.append(
                {
                    "task_index": task_index,
                    "task_class": task_class,
                    "difficulty": difficulty,
                    "seed": seed,
                    "causal_fingerprint": case.causal_task.fingerprint(),
                    "public_fingerprint": _sha256_bytes(
                        _canonical(case.task.public())
                    ),
                    "evidence_budget": case.evidence_budget,
                    "minimum_path_costs": list(case.minimum_path_costs),
                    "sufficiency_threshold": case.sufficiency_threshold,
                    "faithful_regime_probability": (
                        case.faithful_regime_probability
                    ),
                    "adaptive_metrics": adaptive,
                }
            )
            task_index += 1

    development_payload = {
        **common,
        "manifest_type": "causal_v12_development",
        "status": "sealed_development_prepared_not_execution_authorized",
        "master_seed": master_seed,
        "seed_derivation": (
            "uint64_be(SHA256(protocol_version|generator_lineage|split|"
            "task_class|difficulty|task_index|master_seed)[0:8])"
        ),
        "task_count": len(tasks),
        "tasks": tasks,
        "scientific_use": "protocol_calibration_only_never_evaluation",
        "execution_authorization": False,
    }
    evaluation_payload = {
        **common,
        "manifest_type": "causal_v12_evaluation_configuration",
        "status": "not_authorized_seed_not_generated",
        "task_count": 30,
        "distribution_per_class": {"easy": 3, "moderate": 4, "hard": 3},
        "master_seed": None,
        "master_seed_commitment": None,
        "tasks": None,
        "execution_authorization": False,
    }
    _write_manifest(development_path, development_payload)
    _write_manifest(evaluation_path, evaluation_payload)
    development_signature = _sign(development_path, private_key_path)
    evaluation_signature = _sign(evaluation_path, private_key_path)
    return PreparedFreezeV12Artifacts(
        development_manifest=development_path,
        development_signature=development_signature,
        evaluation_configuration=evaluation_path,
        evaluation_signature=evaluation_signature,
        signing_key_fingerprint=signing_fingerprint,
    )


def authorize_prepared_development_v12(
    *,
    prepared_manifest: str | Path,
    private_key: str | Path,
    authorized_manifest: str | Path,
) -> Path:
    prepared_path = Path(prepared_manifest).resolve()
    output = Path(authorized_manifest).resolve()
    if output.exists() or output.with_suffix(output.suffix + ".sig").exists():
        raise FileExistsError(f"CAUSAL_V12_AUTHORIZATION_OUTPUT_EXISTS: {output}")
    document = json.loads(prepared_path.read_text(encoding="utf-8"))
    payload = dict(document["payload"])
    if payload.get("status") != "sealed_development_prepared_not_execution_authorized":
        raise ValueError("CAUSAL_V12_PREPARED_STATUS_INVALID")
    payload["status"] = "sealed_development_authorized"
    payload["execution_authorization"] = True
    payload["authorization_parent_payload_sha256"] = document["payload_sha256"]
    _write_manifest(output, payload)
    _sign(output, Path(private_key).resolve())
    return output
