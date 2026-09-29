from __future__ import annotations

from pathlib import Path
import hashlib
import json
from typing import Any

from .outcomes import FrozenOutcome
from .types import canonical_json


ZERO_HASH = "0" * 64


class EvidenceLedger:
    """Append-only hash-chained JSONL snapshots; existing evidence is never replaced."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.sequence = -1
        self.previous_hash = ZERO_HASH
        if self.path.exists():
            self._load_existing()

    def _load_existing(self) -> None:
        expected_previous = ZERO_HASH
        expected_sequence = 0
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                _verify_record(record, expected_sequence, expected_previous)
                expected_sequence += 1
                expected_previous = record["record_hash"]
        self.sequence = expected_sequence - 1
        self.previous_hash = expected_previous

    def append(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = {
            "sequence": self.sequence + 1,
            "previous_hash": self.previous_hash,
            "payload": payload,
        }
        record_hash = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
        record = {**body, "record_hash": record_hash}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(record) + "\n")
        self.sequence = body["sequence"]
        self.previous_hash = record_hash
        return record

    def append_outcome(self, outcome: FrozenOutcome) -> dict[str, Any]:
        """Append a frozen observation without allowing in-place updates."""

        return self.append(outcome.payload())


def _verify_record(record: dict[str, Any], sequence: int, previous_hash: str) -> None:
    if record.get("sequence") != sequence or record.get("previous_hash") != previous_hash:
        raise ValueError("EVIDENCE_CHAIN_LINK_INVALID")
    body = {
        "sequence": record["sequence"],
        "previous_hash": record["previous_hash"],
        "payload": record["payload"],
    }
    expected_hash = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
    if record.get("record_hash") != expected_hash:
        raise ValueError("EVIDENCE_RECORD_HASH_INVALID")


def verify_ledger(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    count = 0
    head = ZERO_HASH
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                _verify_record(record, count, head)
                count += 1
                head = record["record_hash"]
    return {"records": count, "head": head, "valid": True}
