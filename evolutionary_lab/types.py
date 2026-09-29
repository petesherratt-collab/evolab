from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _require_int(value: Any, name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{name}_MUST_BE_INTEGER")
    return value


@dataclass(frozen=True, slots=True)
class StrategySpec:
    """The bounded strategy language used by the first framework version."""

    fast_window: int
    slow_window: int
    entry_threshold_bps: int
    exit_threshold_bps: int
    max_position_bps: int

    def __post_init__(self) -> None:
        if self.fast_window < 2:
            raise ValueError("FAST_WINDOW_TOO_SMALL")
        if self.slow_window <= self.fast_window:
            raise ValueError("SLOW_WINDOW_MUST_EXCEED_FAST_WINDOW")
        if not 0 <= self.entry_threshold_bps <= 1_000:
            raise ValueError("ENTRY_THRESHOLD_OUT_OF_RANGE")
        if not 0 <= self.exit_threshold_bps <= 1_000:
            raise ValueError("EXIT_THRESHOLD_OUT_OF_RANGE")
        if not 0 <= self.max_position_bps <= 10_000:
            raise ValueError("MAX_POSITION_OUT_OF_RANGE")

    @classmethod
    def from_mapping(cls, value: Any) -> "StrategySpec":
        fields = {
            "fast_window",
            "slow_window",
            "entry_threshold_bps",
            "exit_threshold_bps",
            "max_position_bps",
        }
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError("STRATEGY_FIELDS_MISMATCH")
        return cls(*(  # type: ignore[arg-type]
            _require_int(value[field], field)
            for field in (
                "fast_window",
                "slow_window",
                "entry_threshold_bps",
                "exit_threshold_bps",
                "max_position_bps",
            )
        ))

    def mapping(self) -> dict[str, int]:
        return asdict(self)

    def strategy_id(self) -> str:
        digest = hashlib.sha256(canonical_json(self.mapping()).encode("utf-8")).hexdigest()
        return digest[:16]

    def complexity_score(self) -> float:
        return (
            self.fast_window
            + self.slow_window
            + self.entry_threshold_bps / 20
            + self.exit_threshold_bps / 20
            + self.max_position_bps / 1_000
        )


def parse_strategy_json(text: str) -> StrategySpec:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("DUPLICATE_STRATEGY_KEY")
            result[key] = value
        return result

    try:
        value = json.loads(text, object_pairs_hook=reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise ValueError("INVALID_STRATEGY_JSON") from exc
    return StrategySpec.from_mapping(value)


@dataclass(frozen=True, slots=True)
class MarketBar:
    timestamp_ms: int
    close: float
    available_at_ms: int

    def __post_init__(self) -> None:
        if self.timestamp_ms < 0 or self.available_at_ms < self.timestamp_ms:
            raise ValueError("INVALID_BAR_TIMING")
        if not math.isfinite(self.close) or self.close <= 0:
            raise ValueError("INVALID_BAR_PRICE")


@dataclass(frozen=True, slots=True)
class BacktestResult:
    strategy_id: str
    starting_capital: float
    ending_capital: float
    net_return: float
    max_drawdown: float
    turnover: float
    observations: int
    trades: int
    bankrupt: bool
    data_latency_ms_p50: float
    data_latency_ms_p95: float
    evaluation_ms: float

    def summary(self) -> dict[str, Any]:
        return asdict(self)
