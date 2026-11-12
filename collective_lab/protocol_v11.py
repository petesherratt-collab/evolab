from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib


V11_CONDITIONS = (
    "single_agent",
    "independent_vote",
    "independent_synthesizer",
    "communicating_collective",
)


@dataclass(frozen=True)
class EvidenceAllocation:
    condition: str
    total_budget: int
    investigator_budgets: tuple[int, ...]
    synthesis_budget: int

    def __post_init__(self) -> None:
        if self.condition not in V11_CONDITIONS:
            raise ValueError("CAUSAL_V11_CONDITION_UNKNOWN")
        if self.total_budget <= 0 or any(value < 0 for value in self.investigator_budgets):
            raise ValueError("CAUSAL_V11_EVIDENCE_ALLOCATION_INVALID")
        if self.synthesis_budget < 0:
            raise ValueError("CAUSAL_V11_SYNTHESIS_BUDGET_INVALID")
        if sum(self.investigator_budgets) + self.synthesis_budget != self.total_budget:
            raise ValueError("CAUSAL_V11_EVIDENCE_ALLOCATION_NOT_CONSERVED")

    def mapping(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ComputePlan:
    target_tokens: int = 25_000
    tolerance: float = 0.10
    collective_revision_limit: int = 2
    estimated_revision_tokens: int = 1_800
    estimated_private_review_tokens: int = 3_000
    synthesis_reserve_tokens: int = 5_000

    @property
    def lower_bound(self) -> float:
        return round(self.target_tokens * (1.0 - self.tolerance), 10)

    @property
    def upper_bound(self) -> float:
        return round(self.target_tokens * (1.0 + self.tolerance), 10)

    def permits_collective_revision(self, used_tokens: float) -> bool:
        return (
            used_tokens
            + self.estimated_revision_tokens
            + self.synthesis_reserve_tokens
            <= self.upper_bound
        )

    def permits_private_review(self, used_tokens: float) -> bool:
        return used_tokens + self.estimated_private_review_tokens <= self.upper_bound

    def mapping(self) -> dict[str, object]:
        return {
            **asdict(self),
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
        }


def _pack_costs(
    costs: tuple[int, ...], parts: int, *, rotation: int
) -> tuple[int, ...]:
    """Greedily pack indivisible clue prices into rotated investigator bins."""

    if parts <= 0 or any(cost <= 0 for cost in costs):
        raise ValueError("CAUSAL_V11_PATH_COSTS_INVALID")
    values = [0] * parts
    rotated = tuple((rotation + offset) % parts for offset in range(parts))
    for cost in sorted(costs, reverse=True):
        target = min(rotated, key=lambda index: (values[index], rotated.index(index)))
        values[target] += cost
    return tuple(values)


def _add_reserve(
    budgets: tuple[int, ...], reserve: int, *, rotation: int
) -> tuple[int, ...]:
    if reserve < 0:
        raise ValueError("CAUSAL_V11_VERIFICATION_RESERVE_INVALID")
    values = list(budgets)
    for offset in range(reserve):
        values[(rotation + offset) % len(values)] += 1
    return tuple(values)


def _task_rotation(task_id: str, parts: int) -> int:
    digest = hashlib.sha256(task_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % parts


def evidence_allocation(
    condition: str,
    total_budget: int,
    *,
    task_id: str,
    minimum_path_costs: tuple[int, ...],
) -> EvidenceAllocation:
    if condition not in V11_CONDITIONS:
        raise ValueError(f"CAUSAL_V11_CONDITION_UNKNOWN: {condition}")
    if total_budget <= 0:
        raise ValueError("CAUSAL_V11_TOTAL_BUDGET_INVALID")
    minimum_path_cost = sum(minimum_path_costs)
    if not minimum_path_costs or minimum_path_cost > total_budget:
        raise ValueError("CAUSAL_V11_MINIMUM_PATH_UNAFFORDABLE")
    reserve = total_budget - minimum_path_cost
    if condition == "single_agent":
        return EvidenceAllocation(condition, total_budget, (total_budget,), 0)

    rotation = _task_rotation(task_id, 4)
    if condition == "independent_vote":
        path_budgets = _pack_costs(minimum_path_costs, 4, rotation=rotation)
        return EvidenceAllocation(
            condition,
            total_budget,
            _add_reserve(path_budgets, reserve, rotation=rotation),
            0,
        )

    synthesis_path_cost = max(minimum_path_costs)
    remaining_path = list(minimum_path_costs)
    remaining_path.remove(synthesis_path_cost)
    investigator_budgets = _pack_costs(
        tuple(remaining_path), 4, rotation=rotation
    )
    synthesis_budget = synthesis_path_cost + reserve
    return EvidenceAllocation(
        condition,
        total_budget,
        investigator_budgets,
        synthesis_budget,
    )


def collective_revision_order(task_id: str, investigator_count: int = 4) -> tuple[int, ...]:
    if investigator_count <= 0:
        raise ValueError("CAUSAL_V11_INVESTIGATOR_COUNT_INVALID")
    start = _task_rotation(task_id, investigator_count)
    return tuple((start + offset) % investigator_count for offset in range(investigator_count))


def permitted_collective_revisions(
    task_id: str,
    cumulative_tokens: tuple[float, ...],
    *,
    plan: ComputePlan = ComputePlan(),
) -> tuple[int, ...]:
    """Select a deterministic prefix that preserves the synthesis reserve.

    ``cumulative_tokens`` contains the provider-reported total before each
    prospective revision.  A revision is permitted only if the conservative
    revision estimate plus the frozen synthesis reserve remains under the hard
    compute ceiling.
    """

    order = collective_revision_order(task_id)
    selected: list[int] = []
    for agent_index, used_tokens in zip(order, cumulative_tokens, strict=False):
        if len(selected) >= plan.collective_revision_limit:
            break
        if not plan.permits_collective_revision(used_tokens):
            break
        selected.append(agent_index)
    return tuple(selected)
