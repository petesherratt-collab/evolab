from __future__ import annotations

from typing import Protocol
import random

from .types import StrategySpec


class StrategyGenerator(Protocol):
    name: str

    def generate(
        self, rng: random.Random, count: int, existing_ids: set[str] | None = None
    ) -> list[StrategySpec]: ...


class RandomStrategyGenerator:
    """A no-model baseline and a safe placeholder for future Gemma/Qwen adapters."""

    name = "random-baseline"

    def generate(
        self, rng: random.Random, count: int, existing_ids: set[str] | None = None
    ) -> list[StrategySpec]:
        existing = set(existing_ids or ())
        generated: list[StrategySpec] = []
        attempts = 0
        while len(generated) < count:
            attempts += 1
            if attempts > count * 200:
                raise RuntimeError("STRATEGY_SEARCH_SPACE_EXHAUSTED")
            fast = rng.randint(2, 12)
            slow = rng.randint(fast + 2, 35)
            candidate = StrategySpec(
                fast_window=fast,
                slow_window=slow,
                entry_threshold_bps=rng.choice((0, 5, 10, 20, 40, 80)),
                exit_threshold_bps=rng.choice((0, 5, 10, 20, 40, 80)),
                max_position_bps=rng.choice((2_500, 5_000, 7_500, 10_000)),
            )
            if candidate.strategy_id() in existing:
                continue
            existing.add(candidate.strategy_id())
            generated.append(candidate)
        return generated


def mutate(parent: StrategySpec, rng: random.Random) -> StrategySpec:
    values = parent.mapping()
    field = rng.choice(tuple(values))
    if field == "fast_window":
        values[field] = max(2, min(20, values[field] + rng.choice((-2, -1, 1, 2))))
    elif field == "slow_window":
        values[field] = max(values["fast_window"] + 1, min(45, values[field] + rng.choice((-3, -1, 1, 3))))
    elif field in {"entry_threshold_bps", "exit_threshold_bps"}:
        values[field] = max(0, min(1_000, values[field] + rng.choice((-20, -5, 5, 20))))
    else:
        values[field] = max(500, min(10_000, values[field] + rng.choice((-1_000, -500, 500, 1_000))))
    if values["slow_window"] <= values["fast_window"]:
        values["slow_window"] = values["fast_window"] + 1
    return StrategySpec.from_mapping(values)


def crossover(left: StrategySpec, right: StrategySpec, rng: random.Random) -> StrategySpec:
    left_values = left.mapping()
    right_values = right.mapping()
    values = {
        field: rng.choice((left_values[field], right_values[field]))
        for field in left_values
    }
    values["slow_window"] = max(values["fast_window"] + 1, values["slow_window"])
    return StrategySpec.from_mapping(values)
