from __future__ import annotations

from dataclasses import dataclass, replace

from .causal import CausalNode, CausalTask, PossibleWorld
from .causal_generator import (
    CAUSAL_TASK_CLASSES,
    DIFFICULTIES,
    CausalGeneratedCase,
    generate_causal_case,
)
from .oracle import ExactOracle, OracleMetrics


CAUSAL_GENERATOR_V11_VERSION = "causal-1.1-dev"
_CANDIDATE_COUNT = 5

# The observation regime is usually faithful to the latent fault, but a complete
# evidence history cannot eliminate a small, explicitly modelled chance that the
# regime mimics another candidate.  This prevents the exact oracle and calibrated
# agents from collapsing to probability 1.0 on almost every task.
_FAITHFUL_REGIME_WEIGHT = {
    "easy": 19.0,
    "moderate": 11.0,
    "hard": 7.0,
}
_ALIAS_REGIME_WEIGHT = 1.0

# Sufficient evidence must identify the most likely observation regime.  The
# threshold falls with the irreducible posterior ceiling, while remaining well
# above the balanced five-candidate prior of 0.20.
_SUFFICIENCY_THRESHOLD = {
    "easy": 0.75,
    "moderate": 0.65,
    "hard": 0.55,
}

# A condition can afford one minimum sufficient route and a small amount of
# verification.  It cannot indiscriminately buy the catalogue as it could with
# the former fixed budget of 100.
_VERIFICATION_RESERVE = {
    "easy": 2,
    "moderate": 3,
    "hard": 4,
}


@dataclass(frozen=True)
class CausalGeneratedCaseV11:
    causal_task: CausalTask
    metrics: OracleMetrics
    core_evidence: tuple[str, ...]
    verification_evidence: tuple[str, ...]
    distractor: str
    minimum_path_costs: tuple[int, ...]
    evidence_budget: int
    sufficiency_threshold: float
    faithful_regime_probability: float

    @property
    def task(self):
        return self.causal_task.to_fault_task()


def faithful_regime_probability(difficulty: str) -> float:
    faithful = _FAITHFUL_REGIME_WEIGHT[difficulty]
    alternatives = (_CANDIDATE_COUNT - 1) * _ALIAS_REGIME_WEIGHT
    return faithful / (faithful + alternatives)


def _with_observation_regime(base: CausalGeneratedCase) -> CausalTask:
    """Insert a noisy fault-to-observation layer without changing class mechanics.

    Each original possible world becomes an observation regime.  For every latent
    source fault, the faithful regime receives a larger weight and the four alias
    regimes remain possible.  Keeping every original nuisance configuration is
    essential: additive marginal gain, relational XOR synergy, and coordination
    traps therefore survive the transformation exactly.
    """

    task = base.causal_task
    faithful_weight = _FAITHFUL_REGIME_WEIGHT[task.intended_difficulty]
    worlds: list[PossibleWorld] = []
    true_world_index = -1
    for source_fault in task.candidates:
        for base_index, base_world in enumerate(task.worlds):
            observation_regime = base_world.fault
            nuisance = tuple(
                sorted((*base_world.nuisance, ("observation_regime", observation_regime)))
            )
            worlds.append(
                PossibleWorld(
                    fault=source_fault,
                    nuisance=nuisance,
                    outcomes=base_world.outcomes,
                    weight=base_world.weight
                    * (
                        faithful_weight
                        if source_fault == observation_regime
                        else _ALIAS_REGIME_WEIGHT
                    ),
                )
            )
            if (
                source_fault == task.correct_candidate
                and base_index == task.true_world_index
            ):
                true_world_index = len(worlds) - 1

    if true_world_index < 0:
        raise ValueError("CAUSAL_V11_TRUE_WORLD_NOT_FOUND")

    evidence = tuple(
        replace(item, parents=(*item.parents, "observation_regime"))
        for item in task.evidence
    )
    nodes = tuple(
        replace(node, parents=(*node.parents, "observation_regime"))
        if node.kind == "observation"
        else node
        for node in task.nodes
    ) + (CausalNode("observation_regime", "latent", ("fault",)),)

    return replace(
        task,
        task_id=task.task_id.replace("causal-", "causal-v11-", 1),
        briefing=(
            f"{task.briefing} Observations pass through a shared reliability regime; "
            "even complete evidence can leave calibrated residual uncertainty."
        ),
        evidence=evidence,
        nodes=nodes,
        worlds=tuple(worlds),
        true_world_index=true_world_index,
        generator_version=CAUSAL_GENERATOR_V11_VERSION,
    )


def generate_causal_case_v11(
    seed: int, task_class: str, difficulty: str
) -> CausalGeneratedCaseV11:
    if task_class not in CAUSAL_TASK_CLASSES:
        raise ValueError(f"CAUSAL_V11_TASK_CLASS_UNKNOWN: {task_class}")
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"CAUSAL_V11_DIFFICULTY_UNKNOWN: {difficulty}")

    base = generate_causal_case(seed, task_class, difficulty)
    task = _with_observation_regime(base)
    oracle = ExactOracle(task)
    threshold = _SUFFICIENCY_THRESHOLD[difficulty]
    proxy_ids = [
        item.evidence_id
        for item in task.evidence
        if item.role in {"cheap_correlated_proxy", "misleading_summary"}
    ]
    metrics = oracle.metrics(
        threshold=threshold,
        max_size=6,
        cheap_ids=proxy_ids if task_class == "coordination_trap" else None,
    )
    evidence_budget = (
        metrics.minimum_sufficient_cost + _VERIFICATION_RESERVE[difficulty]
    )
    evidence_by_id = {item.evidence_id: item for item in task.evidence}
    minimum_path_costs = tuple(
        evidence_by_id[evidence_id].cost for evidence_id in base.core_evidence
    )
    expected_posterior = faithful_regime_probability(difficulty)

    if abs(metrics.observed_full_posterior - expected_posterior) > 1e-12:
        raise ValueError("CAUSAL_V11_POSTERIOR_CEILING_INVALID")
    if metrics.observed_full_posterior <= threshold:
        raise ValueError("CAUSAL_V11_THRESHOLD_UNREACHABLE")
    if evidence_budget <= metrics.minimum_sufficient_cost:
        raise ValueError("CAUSAL_V11_BUDGET_HAS_NO_VERIFICATION_RESERVE")
    if evidence_budget >= sum(item.cost for item in task.evidence):
        raise ValueError("CAUSAL_V11_BUDGET_NOT_SCARCE")
    if metrics.minimum_sufficient_cost != base.metrics.minimum_sufficient_cost:
        raise ValueError("CAUSAL_V11_CLASS_MECHANICS_CHANGED")
    if sum(minimum_path_costs) != metrics.minimum_sufficient_cost:
        raise ValueError("CAUSAL_V11_CORE_PATH_COST_INVALID")
    if metrics.minimum_sufficient_clues != base.metrics.minimum_sufficient_clues:
        raise ValueError("CAUSAL_V11_CLUE_MECHANICS_CHANGED")
    if task_class == "coordination_trap":
        if metrics.cheap_distractor != base.distractor:
            raise ValueError("CAUSAL_V11_TRAP_DISTRACTOR_INVALID")
        if metrics.cheap_distractor_posterior <= metrics.cheap_correct_posterior:
            raise ValueError("CAUSAL_V11_TRAP_NOT_MISLEADING")

    return CausalGeneratedCaseV11(
        causal_task=task,
        metrics=metrics,
        core_evidence=base.core_evidence,
        verification_evidence=base.verification_evidence,
        distractor=base.distractor,
        minimum_path_costs=minimum_path_costs,
        evidence_budget=evidence_budget,
        sufficiency_threshold=threshold,
        faithful_regime_probability=expected_posterior,
    )
