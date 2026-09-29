from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from time import perf_counter
from typing import Any, Sequence

from .evidence import EvidenceLedger
from .generators import RandomStrategyGenerator, StrategyGenerator, crossover, mutate
from .market import MarketSplits, market_hash
from .simulator import DeterministicBacktester
from .telemetry import sample
from .types import BacktestResult, MarketBar, StrategySpec


@dataclass(frozen=True, slots=True)
class FitnessWeights:
    drawdown_penalty: float = 1.5
    turnover_penalty: float = 0.002
    complexity_penalty: float = 0.0005


@dataclass(frozen=True, slots=True)
class EvolutionConfig:
    population_size: int = 24
    generations: int = 12
    elite_count: int = 4
    seed: int = 20260927
    fitness: FitnessWeights = FitnessWeights()

    def __post_init__(self) -> None:
        if self.population_size < 2:
            raise ValueError("POPULATION_TOO_SMALL")
        if not 1 <= self.elite_count < self.population_size:
            raise ValueError("INVALID_ELITE_COUNT")
        if self.generations < 1:
            raise ValueError("GENERATIONS_TOO_SMALL")


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    strategy: StrategySpec
    result: BacktestResult
    fitness: float

    def summary(self, rank: int) -> dict[str, Any]:
        return {
            "rank": rank,
            "strategy": self.strategy.mapping(),
            "strategy_id": self.strategy.strategy_id(),
            "fitness": self.fitness,
            "backtest": self.result.summary(),
        }


@dataclass(frozen=True, slots=True)
class EvolutionResult:
    champion: StrategySpec
    train: RankedCandidate
    validation: BacktestResult
    test: BacktestResult
    generations: int
    evidence_path: str | None
    evidence_head: str | None

    def summary(self) -> dict[str, Any]:
        return {
            "champion": self.champion.mapping(),
            "champion_id": self.champion.strategy_id(),
            "train": self.train.summary(1),
            "validation": self.validation.summary(),
            "test": self.test.summary(),
            "generations": self.generations,
            "evidence_path": self.evidence_path,
            "evidence_head": self.evidence_head,
        }


def _fitness(
    strategy: StrategySpec, result: BacktestResult, weights: FitnessWeights
) -> float:
    return (
        result.net_return
        - weights.drawdown_penalty * result.max_drawdown
        - weights.turnover_penalty * result.turnover
        - weights.complexity_penalty * strategy.complexity_score()
    )


class EvolutionRunner:
    def __init__(
        self,
        splits: MarketSplits,
        *,
        config: EvolutionConfig | None = None,
        backtester: DeterministicBacktester | None = None,
        generator: StrategyGenerator | None = None,
        ledger: EvidenceLedger | None = None,
    ):
        self.splits = splits
        self.config = config or EvolutionConfig()
        self.backtester = backtester or DeterministicBacktester()
        self.generator = generator or RandomStrategyGenerator()
        self.ledger = ledger
        self.full_market_hash = market_hash(
            (*splits.train, *splits.validation, *splits.test)
        )

    def _rank(self, population: Sequence[StrategySpec]) -> list[RankedCandidate]:
        ranked = [
            RankedCandidate(
                strategy=strategy,
                result=self.backtester.run(self.splits.train, strategy),
                fitness=0.0,
            )
            for strategy in population
        ]
        ranked = [
            RankedCandidate(
                strategy=item.strategy,
                result=item.result,
                fitness=_fitness(item.strategy, item.result, self.config.fitness),
            )
            for item in ranked
        ]
        return sorted(ranked, key=lambda item: (-item.fitness, item.strategy.strategy_id()))

    def _snapshot(
        self,
        generation: int,
        ranked: Sequence[RankedCandidate],
        started: float,
        telemetry_before: dict[str, Any],
        telemetry_after: dict[str, Any],
    ) -> None:
        if self.ledger is None:
            return
        payload = {
            "kind": "generation_snapshot",
            "generation": generation,
            "generator": self.generator.name,
            "market_hash": self.full_market_hash,
            "config": asdict(self.config),
            "population_size": len(ranked),
            "candidates": [item.summary(rank + 1) for rank, item in enumerate(ranked)],
            "telemetry_before": telemetry_before,
            "telemetry_after": telemetry_after,
            "generation_elapsed_ms": (perf_counter() - started) * 1_000,
        }
        self.ledger.append(payload)

    def run(self) -> EvolutionResult:
        rng = random.Random(self.config.seed)
        population = self.generator.generate(rng, self.config.population_size)
        last_ranked: list[RankedCandidate] = []

        for generation in range(self.config.generations):
            started = perf_counter()
            before = sample().mapping()
            last_ranked = self._rank(population)
            after = sample().mapping()
            self._snapshot(generation, last_ranked, started, before, after)
            if generation == self.config.generations - 1:
                break

            elites = [item.strategy for item in last_ranked[: self.config.elite_count]]
            next_population = list(elites)
            seen = {item.strategy_id() for item in next_population}
            while len(next_population) < self.config.population_size:
                if rng.random() < 0.25:
                    child = crossover(rng.choice(elites), rng.choice(elites), rng)
                else:
                    child = mutate(rng.choice(elites), rng)
                if child.strategy_id() in seen:
                    continue
                seen.add(child.strategy_id())
                next_population.append(child)
            population = next_population

        champion = last_ranked[0]
        validation = self.backtester.run(self.splits.validation, champion.strategy)
        test = self.backtester.run(self.splits.test, champion.strategy)
        return EvolutionResult(
            champion=champion.strategy,
            train=champion,
            validation=validation,
            test=test,
            generations=self.config.generations,
            evidence_path=str(self.ledger.path) if self.ledger else None,
            evidence_head=self.ledger.previous_hash if self.ledger else None,
        )
