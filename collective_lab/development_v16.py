"""Prepare a signed, offline-only pilot. This module has no provider client."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import secrets

from .causal_generator import CAUSAL_TASK_CLASSES, DIFFICULTIES
from .causal_generator_v16 import VERSION, generate_causal_case_v16
from .freeze_v12 import _sha256_file, _sign, _signing_key_fingerprint, _write_manifest
from .protocol_v16 import ACQUISITION_CONDITIONS, ComputePlanV16, REASONING_CONDITIONS, source_hashes


def derive_seed(master_seed, domain, index):
    return int.from_bytes(hashlib.sha256(f"{VERSION}|{domain}|{index}|{master_seed}".encode()).digest()[:8], "big")


def prepare(*, audit_path, output_dir, private_key, public_key, master_seed=None):
    audit_path, output_dir = Path(audit_path), Path(output_dir)
    private_key, public_key = Path(private_key), Path(public_key)
    audit = json.loads(audit_path.read_text())
    hashes = source_hashes()
    cells = {(kind, band): 0 for kind in CAUSAL_TASK_CLASSES for band in DIFFICULTIES}
    for row in audit.get("cases", []):
        cell = (row.get("task_class"), row.get("difficulty"))
        if (cell not in cells or not row.get("passed") or not row.get("checks") or
                not all(row["checks"].values())):
            raise ValueError("V16_AUDIT_CASE_FAILED")
        cells[cell] += 1
    if (audit.get("protocol_version") != VERSION or not audit.get("passed") or
            audit.get("scope") != "offline_population_and_public_contract" or
            len(set(audit.get("seeds", []))) < 2 or
            len({row.get("fingerprint") for row in audit.get("cases", [])}) != len(audit.get("cases", [])) or
            min(cells.values()) < 2 or audit.get("source_sha256") != hashes):
        raise ValueError("V16_FRESH_COMPLETE_AUDIT_REQUIRED")
    development_path = output_dir/"FROZEN_DEVELOPMENT_MANIFEST_CAUSAL_1_6_PREPARED.json"
    evaluation_path = output_dir/"FROZEN_EVALUATION_CONFIGURATION_CAUSAL_1_6_PREPARED.json"
    for path in (development_path, evaluation_path):
        if path.exists() or path.with_suffix(path.suffix+".sig").exists():
            raise FileExistsError(path)
    signing = {"algorithm": "Ed25519", "public_key_sha256": _sha256_file(public_key),
               "public_key_der_sha256": _signing_key_fingerprint(public_key)}
    master = master_seed if master_seed is not None else secrets.token_hex(32)
    specs = []
    for task_class in CAUSAL_TASK_CLASSES:
        for difficulty in DIFFICULTIES:
            index = len(specs)
            layout_seed, world_seed = derive_seed(master, "layout", index), derive_seed(master, "world", index)
            case = generate_causal_case_v16(layout_seed, task_class, difficulty, world_seed=world_seed)
            offset = index % len(REASONING_CONDITIONS)
            reasoning_order = REASONING_CONDITIONS[offset:] + REASONING_CONDITIONS[:offset]
            specs.append({"task_index": index, "task_class": task_class, "difficulty": difficulty,
                          "layout_seed": layout_seed, "world_seed": world_seed,
                          "task_id": case.task.task_id, "task_fingerprint": case.causal_task.fingerprint(),
                          "packet_ids": list(case.packet_ids), "acquisition_budget": case.acquisition_budget,
                          "reasoning_order": list(reasoning_order),
                          "acquisition_order": list(ACQUISITION_CONDITIONS[::1 if index%2 == 0 else -1])})
    common = {"schema": "collective-causal-v16-prepared-v1", "protocol_version": VERSION,
              "status": "prepared_offline_only", "execution_authorized": False,
              "authorized_spend_usd": 0, "source_sha256": hashes, "signing": signing,
              "audit_sha256": _sha256_file(audit_path), "compute_plan": ComputePlanV16().mapping(),
              "model": "openai/gpt-6.1-sol", "reasoning_effort": "medium",
              "reasoning_conditions": list(REASONING_CONDITIONS),
              "acquisition_conditions": list(ACQUISITION_CONDITIONS),
              "primary_contrast": ["communicating_collective", "independent_synthesizer"],
              "primary_metric": "realized_brier_loss", "automatic_promotion": False}
    _write_manifest(development_path, {**common, "split": "development", "master_seed": master,
                                       "task_count": len(specs), "tasks": specs})
    _sign(development_path, private_key)
    _write_manifest(evaluation_path, {**common, "split": "evaluation", "proposed_task_count": 30,
                                      "master_seed": None, "tasks": None,
                                      "requires_separate_analysis_and_spend_plan": True})
    _sign(evaluation_path, private_key)
    return development_path, evaluation_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--private-key", required=True, type=Path)
    parser.add_argument("--public-key", required=True, type=Path)
    args = parser.parse_args()
    paths = prepare(audit_path=args.audit, output_dir=args.output_dir,
                    private_key=args.private_key, public_key=args.public_key)
    print(json.dumps({"prepared": [str(path) for path in paths], "execution_authorized": False,
                      "paid_requests": 0}))


if __name__ == "__main__":
    main()
