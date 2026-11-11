from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
from typing import Any, Mapping

from .causal_generator import (
    CAUSAL_GENERATOR_VERSION,
    CAUSAL_TASK_CLASSES,
    DIFFICULTIES,
    generate_causal_case,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    "COLLECTIVE_INTELLIGENCE_B0_PROTOCOL.md",
    "pyproject.toml",
    "collective_lab/causal.py",
    "collective_lab/causal_generator.py",
    "collective_lab/oracle.py",
    "collective_lab/core.py",
    "collective_lab/runner.py",
    "collective_lab/openrouter.py",
    "collective_lab/cli.py",
    "collective_lab/causal_audit.py",
    "collective_lab/freeze.py",
    "collective_lab/development.py",
    "tests/test_collective_lab.py",
)
DEVELOPMENT_CONDITIONS = (
    "single_agent",
    "independent_vote",
    "independent_synthesizer",
    "communicating_collective",
)
DIFFICULTY_COSTS = {
    "additive": {"easy": 3, "moderate": 9, "hard": 24},
    "relational": {"easy": 6, "moderate": 18, "hard": 48},
    "coordination_trap": {"easy": 4, "moderate": 12, "hard": 17},
}


@dataclass(frozen=True)
class FreezeArtifacts:
    development_manifest: Path
    development_signature: Path
    evaluation_manifest: Path
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


def derive_task_seed(
    master_seed: str,
    *,
    split: str,
    task_class: str,
    difficulty: str,
    task_index: int,
) -> int:
    material = (
        f"{CAUSAL_GENERATOR_VERSION}|{split}|{task_class}|{difficulty}|"
        f"{task_index}|{master_seed}"
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _source_hashes() -> dict[str, str]:
    return {name: _sha256_file(ROOT / name) for name in SOURCE_FILES}


def _public_fingerprint(public: Mapping[str, object]) -> str:
    return _sha256_bytes(_canonical(public))


def _signing_key_fingerprint(public_key: Path) -> str:
    der = subprocess.check_output(
        ["openssl", "pkey", "-pubin", "-in", str(public_key), "-outform", "DER"]
    )
    return _sha256_bytes(der)


def _write_manifest(path: Path, payload: dict[str, Any]) -> None:
    document = {
        "payload": payload,
        "payload_sha256": _sha256_bytes(_canonical(payload)),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def _common_payload(
    *, audit_summary: Path, public_key: Path, signing_key_fingerprint: str
) -> dict[str, Any]:
    audit = json.loads(audit_summary.read_text(encoding="utf-8"))
    if not audit.get("passed") or audit.get("generator_version") != CAUSAL_GENERATOR_VERSION:
        raise ValueError("FREEZE_AUDIT_NOT_ELIGIBLE")
    return {
        "schema": "collective-intelligence-freeze-v1",
        "generator_version": CAUSAL_GENERATOR_VERSION,
        "task_classes": list(CAUSAL_TASK_CLASSES),
        "difficulties": list(DIFFICULTIES),
        "difficulty_minimum_sufficient_costs": DIFFICULTY_COSTS,
        "source_sha256": _source_hashes(),
        "audit": {
            "summary_path": str(audit_summary.relative_to(ROOT)),
            "summary_sha256": _sha256_file(audit_summary),
            "ledger_head": audit["ledger_head"],
            "attempted": audit["attempted"],
            "accepted": audit["accepted"],
            "rejected": audit["rejected"],
        },
        "signing": {
            "algorithm": "Ed25519",
            "public_key_path": str(public_key.relative_to(ROOT)),
            "public_key_sha256": _sha256_file(public_key),
            "public_key_der_sha256": signing_key_fingerprint,
        },
        "seed_derivation": (
            "uint64_be(SHA256(generator_version|split|task_class|difficulty|"
            "task_index|master_seed)[0:8])"
        ),
        "conditions": list(DEVELOPMENT_CONDITIONS),
        "harness": {
            "model": "openai/gpt-6.1-sol",
            "reasoning_effort": "medium",
            "max_completion_tokens": 1400,
            "max_tool_rounds": 3,
            "request_timeout_seconds": 300,
            "evidence_budget_per_condition": 100,
            "target_provider_reported_tokens": 25000,
            "compute_tolerance": 0.10,
            "primary_metric": "five_class_brier_loss",
            "integrity_adjusted_failure_loss": 2.0,
            "conditions": list(DEVELOPMENT_CONDITIONS),
        },
        "leakage_probe": {
            "feature_sets": ["metadata_only", "text_only"],
            "targets": ["correct_label", "correct_position"],
            "held_out_threshold": 0.40,
            "split_rule": "seed-disjoint balanced Latin diagonals 0 and 2",
        },
    }


def create_freeze_package(
    *,
    audit_summary: str | Path,
    private_key: str | Path,
    public_key: str | Path,
    development_manifest: str | Path,
    evaluation_manifest: str | Path,
    development_master_seed: str | None = None,
) -> FreezeArtifacts:
    audit_path = Path(audit_summary).resolve()
    private_key_path = Path(private_key).resolve()
    public_key_path = Path(public_key).resolve()
    development_path = Path(development_manifest).resolve()
    evaluation_path = Path(evaluation_manifest).resolve()
    for output in (development_path, evaluation_path):
        if output.exists() or output.with_suffix(output.suffix + ".sig").exists():
            raise FileExistsError(f"FREEZE_OUTPUT_EXISTS: {output}")
    signing_fingerprint = _signing_key_fingerprint(public_key_path)
    common = _common_payload(
        audit_summary=audit_path,
        public_key=public_key_path,
        signing_key_fingerprint=signing_fingerprint,
    )

    master_seed = development_master_seed or secrets.token_hex(32)
    development_tasks: list[dict[str, object]] = []
    task_index = 0
    for task_class in CAUSAL_TASK_CLASSES:
        for difficulty in DIFFICULTIES:
            seed = derive_task_seed(
                master_seed,
                split="development",
                task_class=task_class,
                difficulty=difficulty,
                task_index=task_index,
            )
            case = generate_causal_case(seed, task_class, difficulty)
            development_tasks.append(
                {
                    "task_index": task_index,
                    "task_class": task_class,
                    "difficulty": difficulty,
                    "seed": seed,
                    "causal_fingerprint": case.causal_task.fingerprint(),
                    "public_fingerprint": _public_fingerprint(case.task.public()),
                }
            )
            task_index += 1

    development_payload = {
        **common,
        "manifest_type": "development",
        "status": "sealed_development_authorized",
        "master_seed": master_seed,
        "task_count": 9,
        "tasks": development_tasks,
        "scientific_use": "protocol_calibration_only_never_evaluation",
    }
    evaluation_payload = {
        **common,
        "manifest_type": "evaluation_configuration",
        "status": "frozen_but_not_authorized_seed_not_generated",
        "master_seed": None,
        "master_seed_commitment": None,
        "task_count": 30,
        "distribution_per_class": {"easy": 3, "moderate": 4, "hard": 3},
        "tasks": None,
        "authorization": False,
    }
    _write_manifest(development_path, development_payload)
    _write_manifest(evaluation_path, evaluation_payload)
    development_signature = _sign(development_path, private_key_path)
    evaluation_signature = _sign(evaluation_path, private_key_path)
    return FreezeArtifacts(
        development_manifest=development_path,
        development_signature=development_signature,
        evaluation_manifest=evaluation_path,
        evaluation_signature=evaluation_signature,
        signing_key_fingerprint=signing_fingerprint,
    )


def verify_manifest(
    manifest: str | Path, signature: str | Path, public_key: str | Path
) -> dict[str, object]:
    manifest_path = Path(manifest).resolve()
    signature_path = Path(signature).resolve()
    public_key_path = Path(public_key).resolve()
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = document["payload"]
    if document.get("payload_sha256") != _sha256_bytes(_canonical(payload)):
        raise ValueError("FREEZE_PAYLOAD_HASH_INVALID")
    subprocess.run(
        [
            "openssl",
            "pkeyutl",
            "-verify",
            "-pubin",
            "-inkey",
            str(public_key_path),
            "-rawin",
            "-in",
            str(manifest_path),
            "-sigfile",
            str(signature_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    for name, expected in payload["source_sha256"].items():
        if _sha256_file(ROOT / name) != expected:
            raise ValueError(f"FREEZE_SOURCE_HASH_INVALID: {name}")
    audit_path = ROOT / payload["audit"]["summary_path"]
    if _sha256_file(audit_path) != payload["audit"]["summary_sha256"]:
        raise ValueError("FREEZE_AUDIT_HASH_INVALID")
    if payload["manifest_type"] == "development":
        for task in payload["tasks"]:
            case = generate_causal_case(
                int(task["seed"]), str(task["task_class"]), str(task["difficulty"])
            )
            if case.causal_task.fingerprint() != task["causal_fingerprint"]:
                raise ValueError("FREEZE_DEVELOPMENT_CAUSAL_FINGERPRINT_INVALID")
            if _public_fingerprint(case.task.public()) != task["public_fingerprint"]:
                raise ValueError("FREEZE_DEVELOPMENT_PUBLIC_FINGERPRINT_INVALID")
    return {
        "valid": True,
        "manifest_type": payload["manifest_type"],
        "generator_version": payload["generator_version"],
        "payload_sha256": document["payload_sha256"],
        "signing_key_fingerprint": payload["signing"]["public_key_der_sha256"],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Create or verify frozen causal manifests")
    parser.add_argument("--audit-summary", type=Path)
    parser.add_argument("--private-key", type=Path)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--development-manifest", type=Path)
    parser.add_argument("--evaluation-manifest", type=Path)
    parser.add_argument("--development-master-seed")
    parser.add_argument("--reuse-development-manifest", type=Path)
    parser.add_argument("--verify-manifest", type=Path)
    parser.add_argument("--signature", type=Path)
    args = parser.parse_args()
    if args.verify_manifest:
        if not args.signature:
            parser.error("--signature is required with --verify-manifest")
        print(
            json.dumps(
                verify_manifest(args.verify_manifest, args.signature, args.public_key),
                indent=2,
                sort_keys=True,
            )
        )
        return
    required = (
        args.audit_summary,
        args.private_key,
        args.development_manifest,
        args.evaluation_manifest,
    )
    if any(value is None for value in required):
        parser.error(
            "creation requires --audit-summary, --private-key, "
            "--development-manifest, and --evaluation-manifest"
        )
    development_master_seed = args.development_master_seed
    if args.reuse_development_manifest:
        previous = json.loads(
            args.reuse_development_manifest.read_text(encoding="utf-8")
        )
        development_master_seed = str(previous["payload"]["master_seed"])
    artifacts = create_freeze_package(
        audit_summary=args.audit_summary,
        private_key=args.private_key,
        public_key=args.public_key,
        development_manifest=args.development_manifest,
        evaluation_manifest=args.evaluation_manifest,
        development_master_seed=development_master_seed,
    )
    print(json.dumps({key: str(value) for key, value in asdict(artifacts).items()}, indent=2))


if __name__ == "__main__":
    main()
