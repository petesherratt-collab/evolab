from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
import math
from typing import Iterable

from .causal import CausalTask, PossibleWorld
from .causal_generator_v11 import AdaptiveBranchPlan


@dataclass(frozen=True)
class AdaptiveChoiceMetrics:
    router_evidence: str
    branch_evidence: tuple[str, str]
    baseline_evidence: tuple[str, ...]
    router_outcomes: int
    selected_followups: tuple[tuple[int, str], ...]
    best_fixed_followup: str
    adaptive_conditional_entropy: float
    fixed_conditional_entropy: float
    adaptive_gain_bits: float
    threshold_bits: float

    @property
    def passed(self) -> bool:
        return (
            self.router_outcomes >= 2
            and len({item for _, item in self.selected_followups}) >= 2
            and self.adaptive_gain_bits >= self.threshold_bits
        )

    def mapping(self) -> dict[str, object]:
        value = asdict(self)
        value["selected_followups"] = [list(item) for item in self.selected_followups]
        value["passed"] = self.passed
        return value


def _entropy(worlds: Iterable[PossibleWorld]) -> float:
    masses: dict[str, float] = defaultdict(float)
    for world in worlds:
        masses[world.fault] += world.weight
    total = sum(masses.values())
    if total <= 0:
        raise ValueError("CAUSAL_V11_ADAPTIVE_EMPTY_WORLD_SET")
    return -sum(
        (mass / total) * math.log2(mass / total)
        for mass in masses.values()
        if mass > 0
    )


def _conditional_entropy(
    worlds: tuple[PossibleWorld, ...], task: CausalTask, evidence_id: str
) -> float:
    index = task.evidence_index()[evidence_id]
    groups: dict[int, list[PossibleWorld]] = defaultdict(list)
    for world in worlds:
        groups[world.outcomes[index]].append(world)
    total = sum(world.weight for world in worlds)
    return sum(
        sum(world.weight for world in group) / total * _entropy(group)
        for group in groups.values()
    )


def adaptive_choice_metrics(
    task: CausalTask,
    plan: AdaptiveBranchPlan,
    *,
    threshold_bits: float = 0.01,
) -> AdaptiveChoiceMetrics:
    """Measure whether routing changes the optimal next evidence purchase.

    The decision point is evaluated after the observed baseline clues have been
    acquired but before the router or either branch probe.  The metric compares
    an adaptive policy, which selects a probe after seeing the router, with the
    best policy forced to precommit to one probe for both router outcomes.
    """

    if threshold_bits <= 0:
        raise ValueError("CAUSAL_V11_ADAPTIVE_THRESHOLD_INVALID")
    index = task.evidence_index()
    observed = task.observed_outcomes()
    baseline_worlds = tuple(
        world
        for world in task.worlds
        if all(
            world.outcomes[index[evidence_id]] == observed[evidence_id]
            for evidence_id in plan.baseline_evidence
        )
    )
    if not baseline_worlds:
        raise ValueError("CAUSAL_V11_ADAPTIVE_BASELINE_IMPOSSIBLE")

    router_index = index[plan.router_evidence]
    routed: dict[int, tuple[PossibleWorld, ...]] = {}
    for outcome in sorted(
        {world.outcomes[router_index] for world in baseline_worlds}
    ):
        routed[outcome] = tuple(
            world
            for world in baseline_worlds
            if world.outcomes[router_index] == outcome
        )

    total_mass = sum(world.weight for world in baseline_worlds)
    selected: list[tuple[int, str]] = []
    adaptive_entropy = 0.0
    for outcome, branch_worlds in routed.items():
        best_entropy, best_evidence = min(
            (
                _conditional_entropy(branch_worlds, task, evidence_id),
                evidence_id,
            )
            for evidence_id in plan.branch_evidence
        )
        branch_mass = sum(world.weight for world in branch_worlds)
        adaptive_entropy += branch_mass / total_mass * best_entropy
        selected.append((outcome, best_evidence))

    fixed_options = []
    for evidence_id in plan.branch_evidence:
        conditional = 0.0
        for branch_worlds in routed.values():
            branch_mass = sum(world.weight for world in branch_worlds)
            conditional += (
                branch_mass
                / total_mass
                * _conditional_entropy(branch_worlds, task, evidence_id)
            )
        fixed_options.append((conditional, evidence_id))
    fixed_entropy, fixed_evidence = min(fixed_options)

    return AdaptiveChoiceMetrics(
        router_evidence=plan.router_evidence,
        branch_evidence=plan.branch_evidence,
        baseline_evidence=plan.baseline_evidence,
        router_outcomes=len(routed),
        selected_followups=tuple(selected),
        best_fixed_followup=fixed_evidence,
        adaptive_conditional_entropy=adaptive_entropy,
        fixed_conditional_entropy=fixed_entropy,
        adaptive_gain_bits=fixed_entropy - adaptive_entropy,
        threshold_bits=threshold_bits,
    )
