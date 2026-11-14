from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from typing import Any

from .protocol_v11 import EvidenceAllocation, V11_CONDITIONS, evidence_allocation


CAUSAL_V12_PROTOCOL_VERSION = "causal-1.2-dev"
V12_CONDITIONS = V11_CONDITIONS


@dataclass(frozen=True)
class StagedEvidenceAllocation:
    condition: str
    total_budget: int
    scout_ceiling: int
    coordinator_guaranteed_budget: int
    deliberator_count: int = 4

    def __post_init__(self) -> None:
        if self.condition != "communicating_collective":
            raise ValueError("CAUSAL_V12_STAGED_CONDITION_INVALID")
        if self.total_budget <= 0:
            raise ValueError("CAUSAL_V12_TOTAL_BUDGET_INVALID")
        if not 0 < self.scout_ceiling < self.total_budget:
            raise ValueError("CAUSAL_V12_SCOUT_CEILING_INVALID")
        if self.coordinator_guaranteed_budget != self.total_budget - self.scout_ceiling:
            raise ValueError("CAUSAL_V12_STAGED_BUDGET_NOT_CONSERVED")
        if self.deliberator_count <= 0:
            raise ValueError("CAUSAL_V12_DELIBERATOR_COUNT_INVALID")

    def coordinator_budget_after(self, scout_spent: int) -> int:
        if not 0 <= scout_spent <= self.scout_ceiling:
            raise ValueError("CAUSAL_V12_SCOUT_SPEND_INVALID")
        return self.total_budget - scout_spent

    def mapping(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ComputePlanV12:
    target_tokens: int = 25_000
    tolerance: float = 0.10
    max_completion_tokens: int = 1_000
    minimum_completion_tokens: int = 96
    prompt_characters_per_token: float = 4.0
    prompt_token_overhead: int = 384
    post_call_safety_margin: int = 256
    mandatory_episode_reserve_tokens: int = 2_200
    optional_call_reserve_tokens: int = 2_600
    max_condition_requests: int = 18
    max_private_reviews: int = 12

    def __post_init__(self) -> None:
        if self.target_tokens < 0 or not 0 <= self.tolerance < 1:
            raise ValueError("CAUSAL_V12_COMPUTE_TARGET_INVALID")
        if self.max_completion_tokens < self.minimum_completion_tokens:
            raise ValueError("CAUSAL_V12_COMPLETION_LIMIT_INVALID")
        if self.prompt_characters_per_token <= 0:
            raise ValueError("CAUSAL_V12_PROMPT_ESTIMATE_INVALID")
        if self.max_condition_requests <= 0 or self.max_private_reviews < 0:
            raise ValueError("CAUSAL_V12_REQUEST_LIMIT_INVALID")

    @property
    def enabled(self) -> bool:
        return self.target_tokens > 0

    @property
    def lower_bound(self) -> float:
        return round(self.target_tokens * (1.0 - self.tolerance), 10)

    @property
    def upper_bound(self) -> float:
        return round(self.target_tokens * (1.0 + self.tolerance), 10)

    def estimate_prompt_tokens(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> int:
        payload = {
            "messages": messages,
            "tools": tools,
            "response_format": response_format,
        }
        characters = len(
            json.dumps(payload, sort_keys=True, separators=(",", ":"))
        )
        return (
            math.ceil(characters / self.prompt_characters_per_token)
            + self.prompt_token_overhead
        )

    def reserve_for_mandatory_episodes(self, count: int) -> int:
        if count < 0:
            raise ValueError("CAUSAL_V12_MANDATORY_EPISODE_COUNT_INVALID")
        return count * self.mandatory_episode_reserve_tokens

    def completion_cap(
        self,
        *,
        used_tokens: float,
        estimated_prompt_tokens: int,
        reserve_after: int,
        requested_max: int,
    ) -> int:
        if not self.enabled:
            return requested_max
        available = math.floor(
            self.upper_bound
            - used_tokens
            - estimated_prompt_tokens
            - reserve_after
            - self.post_call_safety_margin
        )
        if available < self.minimum_completion_tokens:
            return 0
        return min(requested_max, self.max_completion_tokens, available)

    def permits_optional_call(self, used_tokens: float) -> bool:
        return (
            not self.enabled
            or used_tokens + self.optional_call_reserve_tokens <= self.upper_bound
        )

    def mapping(self) -> dict[str, object]:
        return {
            **asdict(self),
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
        }


def staged_evidence_allocation(
    total_budget: int,
    *,
    minimum_path_costs: tuple[int, ...],
) -> StagedEvidenceAllocation:
    minimum_path_cost = sum(minimum_path_costs)
    if not minimum_path_costs or any(cost <= 0 for cost in minimum_path_costs):
        raise ValueError("CAUSAL_V12_PATH_COSTS_INVALID")
    if minimum_path_cost >= total_budget:
        raise ValueError("CAUSAL_V12_SCOUT_RESERVE_MISSING")
    scout_ceiling = total_budget - minimum_path_cost
    return StagedEvidenceAllocation(
        condition="communicating_collective",
        total_budget=total_budget,
        scout_ceiling=scout_ceiling,
        coordinator_guaranteed_budget=minimum_path_cost,
    )


def v12_evidence_allocation(
    condition: str,
    total_budget: int,
    *,
    task_id: str,
    minimum_path_costs: tuple[int, ...],
) -> EvidenceAllocation | StagedEvidenceAllocation:
    if condition == "communicating_collective":
        return staged_evidence_allocation(
            total_budget,
            minimum_path_costs=minimum_path_costs,
        )
    return evidence_allocation(
        condition,
        total_budget,
        task_id=task_id,
        minimum_path_costs=minimum_path_costs,
    )
