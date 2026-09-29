from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import random
from typing import Sequence

from .types import MarketBar, canonical_json


DAY_MS = 86_400_000


@dataclass(frozen=True, slots=True)
class MarketSplits:
    train: tuple[MarketBar, ...]
    validation: tuple[MarketBar, ...]
    test: tuple[MarketBar, ...]


def synthetic_market(
    *, seed: int = 20260927, count: int = 360, feed_delay_ms: int = 3_600_000
) -> tuple[MarketBar, ...]:
    """Create deterministic synthetic close data for framework testing only."""
    if count < 20:
        raise ValueError("MARKET_TOO_SHORT")
    if feed_delay_ms < 0 or feed_delay_ms >= DAY_MS:
        raise ValueError("FEED_DELAY_MUST_BE_WITHIN_BAR")

    rng = random.Random(seed)
    price = 100.0
    start = 1_700_000_000_000
    bars: list[MarketBar] = []
    for index in range(count):
        regime = 0.0007 if (index // 60) % 2 == 0 else -0.00035
        cycle = 0.0013 * math.sin(index / 11.0)
        noise = rng.gauss(0.0, 0.0075)
        price *= math.exp(regime + cycle + noise)
        timestamp = start + index * DAY_MS
        jitter = rng.randint(0, max(1, feed_delay_ms // 10))
        bars.append(
            MarketBar(
                timestamp_ms=timestamp,
                close=round(price, 8),
                available_at_ms=timestamp + feed_delay_ms + jitter,
            )
        )
    return tuple(bars)


def chronological_split(
    bars: Sequence[MarketBar], *, train_fraction: float = 0.6, validation_fraction: float = 0.2
) -> MarketSplits:
    if len(bars) < 30:
        raise ValueError("MARKET_TOO_SHORT_FOR_SPLIT")
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("INVALID_SPLIT_FRACTIONS")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("SPLITS_MUST_LEAVE_TEST_DATA")
    train_end = int(len(bars) * train_fraction)
    validation_end = train_end + int(len(bars) * validation_fraction)
    if train_end < 10 or validation_end <= train_end or validation_end >= len(bars):
        raise ValueError("SPLIT_TOO_SMALL")
    return MarketSplits(
        train=tuple(bars[:train_end]),
        validation=tuple(bars[train_end:validation_end]),
        test=tuple(bars[validation_end:]),
    )


def market_hash(bars: Sequence[MarketBar]) -> str:
    payload = [
        {
            "timestamp_ms": bar.timestamp_ms,
            "close": bar.close,
            "available_at_ms": bar.available_at_ms,
        }
        for bar in bars
    ]
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
