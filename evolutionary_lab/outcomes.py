from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from .types import canonical_json


@dataclass(frozen=True, slots=True)
class FrozenOutcome:
    """An immutable boundary record for an observed candidate outcome.

    The evolutionary loop may discover and rank candidates, but an outcome is
    recorded separately with the observation cutoff and source hash that made
    it available.  The same shape can represent a backtest, paper-shadow
    result, or an outcome from another deterministic domain.
    """

    experiment_id: str
    phase: str
    candidate_id: str
    observation_cutoff_ms: int
    observation_hash: str
    metrics: Mapping[str, Any]
    status: str = "complete"
    _metrics_json: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.experiment_id, "EXPERIMENT_ID"),
            (self.phase, "OUTCOME_PHASE"),
            (self.candidate_id, "CANDIDATE_ID"),
            (self.observation_hash, "OBSERVATION_HASH"),
            (self.status, "OUTCOME_STATUS"),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name}_REQUIRED")
        if type(self.observation_cutoff_ms) is not int or self.observation_cutoff_ms < 0:
            raise ValueError("OUTCOME_CUTOFF_INVALID")
        if not isinstance(self.metrics, Mapping):
            raise ValueError("OUTCOME_METRICS_MUST_BE_MAPPING")
        try:
            metrics_json = canonical_json(dict(self.metrics))
        except (TypeError, ValueError) as exc:
            raise ValueError("OUTCOME_METRICS_NOT_JSON") from exc
        object.__setattr__(self, "metrics", MappingProxyType(json.loads(metrics_json)))
        object.__setattr__(self, "_metrics_json", metrics_json)

    def payload(self) -> dict[str, Any]:
        """Return a JSON snapshot suitable for an append-only evidence ledger."""

        # Round-trip through canonical JSON so later mutation of a caller-owned
        # mapping cannot alter the payload that is about to be recorded.
        frozen_metrics = json.loads(self._metrics_json)
        return {
            "kind": "frozen_outcome",
            "experiment_id": self.experiment_id,
            "phase": self.phase,
            "candidate_id": self.candidate_id,
            "observation_cutoff_ms": self.observation_cutoff_ms,
            "observation_hash": self.observation_hash,
            "metrics": frozen_metrics,
            "status": self.status,
            "outcome_id": self.outcome_id(),
        }

    def outcome_id(self) -> str:
        body = {
            "experiment_id": self.experiment_id,
            "phase": self.phase,
            "candidate_id": self.candidate_id,
            "observation_cutoff_ms": self.observation_cutoff_ms,
            "observation_hash": self.observation_hash,
            "metrics": json.loads(self._metrics_json),
            "status": self.status,
        }
        return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()[:16]
