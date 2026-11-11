from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
import math
from typing import Iterable

from .causal import CausalTask, PossibleWorld


@dataclass(frozen=True)
class OracleMetrics:
    minimum_sufficient_cost: int
    minimum_sufficient_clues: int
    minimal_sufficient_sets: int
    minimum_cost_sufficient_sets: int
    prior_entropy: float
    observed_full_posterior: float
    maximum_single_information_gain: float
    maximum_pair_synergy: float
    cheap_distractor: str | None
    cheap_distractor_posterior: float
    cheap_correct_posterior: float

    def mapping(self) -> dict[str, object]:
        return asdict(self)


class ExactOracle:
    def __init__(self, task: CausalTask) -> None:
        self.task = task
        self._index = task.evidence_index()
        self._all_worlds_mask = (1 << len(task.worlds)) - 1
        observed = task.observed_outcomes()
        self._observed_world_masks = {
            evidence_id: sum(
                1 << world_index
                for world_index, world in enumerate(task.worlds)
                if world.outcomes[evidence_index] == observed[evidence_id]
            )
            for evidence_id, evidence_index in self._index.items()
        }
        self._candidate_index = {
            candidate: index for index, candidate in enumerate(task.candidates)
        }
        self._correct_index = self._candidate_index[task.correct_candidate]
        self._world_fault_indexes = tuple(
            self._candidate_index[world.fault] for world in task.worlds
        )
        self._world_weights = tuple(world.weight for world in task.worlds)

    def _consistent_worlds(self, observations: dict[str, int]) -> list[PossibleWorld]:
        indexed = [(self._index[evidence_id], outcome) for evidence_id, outcome in observations.items()]
        return [
            world
            for world in self.task.worlds
            if all(world.outcomes[index] == outcome for index, outcome in indexed)
        ]

    def posterior(self, observations: dict[str, int]) -> dict[str, float]:
        worlds = self._consistent_worlds(observations)
        masses = {candidate: 0.0 for candidate in self.task.candidates}
        for world in worlds:
            masses[world.fault] += world.weight
        total = sum(masses.values())
        if total <= 0:
            raise ValueError("ORACLE_IMPOSSIBLE_OBSERVATION")
        return {candidate: mass / total for candidate, mass in masses.items()}

    def observed_posterior(self, evidence_ids: Iterable[str]) -> dict[str, float]:
        actual = self.task.observed_outcomes()
        return self.posterior({evidence_id: actual[evidence_id] for evidence_id in evidence_ids})

    def _observed_correct_probability(self, evidence_ids: Iterable[str]) -> float:
        """Fast exact posterior for the true candidate under observed outcomes.

        ``minimal_sufficient_sets`` calls this tens of thousands of times.  Integer
        masks make consistency intersection exact while avoiding repeated scans and
        dictionary construction for every subset.
        """

        consistent = self._all_worlds_mask
        for evidence_id in evidence_ids:
            consistent &= self._observed_world_masks[evidence_id]
        if not consistent:
            raise ValueError("ORACLE_IMPOSSIBLE_OBSERVATION")
        total = 0.0
        correct = 0.0
        remaining = consistent
        while remaining:
            least_bit = remaining & -remaining
            world_index = least_bit.bit_length() - 1
            weight = self._world_weights[world_index]
            total += weight
            if self._world_fault_indexes[world_index] == self._correct_index:
                correct += weight
            remaining ^= least_bit
        return correct / total

    @staticmethod
    def entropy(distribution: dict[str, float]) -> float:
        return -sum(value * math.log2(value) for value in distribution.values() if value > 0)

    def information_gain(self, evidence_ids: Iterable[str]) -> float:
        ids = tuple(evidence_ids)
        prior = self.posterior({})
        prior_entropy = self.entropy(prior)
        outcome_masses: dict[tuple[int, ...], float] = {}
        total_mass = sum(world.weight for world in self.task.worlds)
        indexes = [self._index[evidence_id] for evidence_id in ids]
        for world in self.task.worlds:
            outcome = tuple(world.outcomes[index] for index in indexes)
            outcome_masses[outcome] = outcome_masses.get(outcome, 0.0) + world.weight
        conditional_entropy = 0.0
        for outcome, mass in outcome_masses.items():
            observations = dict(zip(ids, outcome, strict=True))
            conditional_entropy += mass / total_mass * self.entropy(self.posterior(observations))
        return prior_entropy - conditional_entropy

    def synergy(self, evidence_ids: Iterable[str]) -> float:
        ids = tuple(evidence_ids)
        return self.information_gain(ids) - sum(self.information_gain((item,)) for item in ids)

    def minimal_sufficient_sets(
        self,
        *,
        threshold: float = 0.90,
        max_size: int = 6,
    ) -> list[tuple[str, ...]]:
        ids = tuple(item.evidence_id for item in self.task.evidence)
        evidence_bits = {evidence_id: 1 << index for index, evidence_id in enumerate(ids)}
        sufficient: list[tuple[str, ...]] = []
        sufficient_masks: list[int] = []
        for size in range(1, max_size + 1):
            for subset in combinations(ids, size):
                subset_mask = sum(evidence_bits[evidence_id] for evidence_id in subset)
                if any(existing & subset_mask == existing for existing in sufficient_masks):
                    continue
                if self._observed_correct_probability(subset) >= threshold:
                    sufficient.append(subset)
                    sufficient_masks.append(subset_mask)
        return sufficient

    def metrics(
        self,
        *,
        threshold: float = 0.90,
        max_size: int = 6,
        cheap_ids: Iterable[str] | None = None,
    ) -> OracleMetrics:
        sufficient = self.minimal_sufficient_sets(threshold=threshold, max_size=max_size)
        if not sufficient:
            raise ValueError("ORACLE_NO_SUFFICIENT_SET")
        cost = {item.evidence_id: item.cost for item in self.task.evidence}
        costs = [sum(cost[item] for item in subset) for subset in sufficient]
        single_gains = [
            self.information_gain((item.evidence_id,)) for item in self.task.evidence
        ]
        pair_synergies = [
            self.synergy((left.evidence_id, right.evidence_id))
            for left, right in combinations(self.task.evidence, 2)
        ]
        selected_cheap_ids = (
            list(cheap_ids)
            if cheap_ids is not None
            else [item.evidence_id for item in self.task.evidence if item.cost == 1]
        )
        cheap_posterior = self.observed_posterior(selected_cheap_ids)
        distractor = max(
            (candidate for candidate in self.task.candidates if candidate != self.task.correct_candidate),
            key=cheap_posterior.get,
        )
        full = self.observed_posterior(item.evidence_id for item in self.task.evidence)
        return OracleMetrics(
            minimum_sufficient_cost=min(costs),
            minimum_sufficient_clues=min(len(subset) for subset in sufficient),
            minimal_sufficient_sets=len(sufficient),
            minimum_cost_sufficient_sets=sum(value == min(costs) for value in costs),
            prior_entropy=self.entropy(self.posterior({})),
            observed_full_posterior=full[self.task.correct_candidate],
            maximum_single_information_gain=max(single_gains),
            maximum_pair_synergy=max(pair_synergies),
            cheap_distractor=distractor,
            cheap_distractor_posterior=cheap_posterior[distractor],
            cheap_correct_posterior=cheap_posterior[self.task.correct_candidate],
        )
