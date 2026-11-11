from __future__ import annotations

import fcntl
from pathlib import Path
from typing import Any

from evolutionary_lab.evidence import EvidenceLedger


class ExclusiveRunLedger:
    """Evidence ledger guarded against concurrent writers for a run's lifetime."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self._lock_handle = self.lock_path.open("a+")
        try:
            fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._lock_handle.close()
            raise RuntimeError(f"RUN_LEDGER_ALREADY_LOCKED: {self.path}") from exc
        self._ledger = EvidenceLedger(self.path)

    def append(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._ledger.append(payload)

    def close(self) -> None:
        if not self._lock_handle.closed:
            fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_UN)
            self._lock_handle.close()

    def __enter__(self) -> "ExclusiveRunLedger":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
