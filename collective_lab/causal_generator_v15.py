from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json

from .causal import CausalEvidence, CausalNode, CausalTask, PossibleWorld
from .causal_generator import CAUSAL_TASK_CLASSES, DIFFICULTIES, _REGIONS
from .causal_generator_v11 import (
    CAUSAL_GENERATOR_V11_VERSION,
    CausalGeneratedCaseV11,
    generate_causal_case_v11,
)
from .oracle import ExactOracle, OracleMetrics
from .protocol_v13 import PERSPECTIVE_LENSES


CAUSAL_GENERATOR_V15_VERSION = "causal-1.5-dev"

# Easy remains a transparent control. Moderate and hard retain residual
# uncertainty while making calibrated losses above the 0.12 development floor
# mechanically possible.
_FAITHFUL_REGIME_WEIGHT_V15 = {
    "easy": 19.0,
    "moderate": 7.0,
    "hard": 5.0,
}
_FAITHFUL_REGIME_WEIGHT_V11 = {
    "easy": 19.0,
    "moderate": 11.0,
    "hard": 7.0,
}
_SUFFICIENCY_THRESHOLD_V15 = {
    "easy": 0.75,
    "moderate": 0.55,
    "hard": 0.48,
}
_VERIFICATION_RESERVE_V15 = {
    "easy": 2,
    "moderate": 1,
    "hard": 2,
}


@dataclass(frozen=True)
class AcquisitionLane:
    lane_id: str
    region: str
    active_option: str
    alternative_option: str
    active_label: str

    def mapping(self) -> dict[str, str]:
        return {
            "lane_id": self.lane_id,
            "region": self.region,
            "active_option": self.active_option,
            "alternative_option": self.alternative_option,
            "active_label": self.active_label,
        }


@dataclass(frozen=True)
class CausalGeneratedCaseV15:
    causal_task: CausalTask
    metrics: OracleMetrics
    core_evidence: tuple[str, ...]
    verification_evidence: tuple[str, ...]
    distractor: str
    minimum_path_costs: tuple[int, ...]
    evidence_budget: int
    sufficiency_threshold: float
    faithful_regime_probability: float
    topology_router: str | None
    acquisition_lanes: tuple[AcquisitionLane, ...]
    perspective_lenses: tuple[str, ...]
    source_generator: str = CAUSAL_GENERATOR_V11_VERSION

    @property
    def task(self):
        return self.causal_task.to_fault_task()


def faithful_regime_probability_v15(difficulty: str) -> float:
    faithful = _FAITHFUL_REGIME_WEIGHT_V15[difficulty]
    return faithful / (faithful + 4.0)


def _reweight_observation_regime(task: CausalTask) -> CausalTask:
    old_faithful = _FAITHFUL_REGIME_WEIGHT_V11[task.intended_difficulty]
    new_faithful = _FAITHFUL_REGIME_WEIGHT_V15[task.intended_difficulty]
    worlds = []
    for world in task.worlds:
        regime = world.nuisance_mapping().get("observation_regime")
        faithful = regime == world.fault
        old_factor = old_faithful if faithful else 1.0
        new_factor = new_faithful if faithful else 1.0
        worlds.append(replace(world, weight=world.weight / old_factor * new_factor))
    return replace(task, worlds=tuple(worlds))


def _stable_bit(seed: int, *values: str) -> int:
    material = "|".join((str(seed), *values)).encode("utf-8")
    return hashlib.sha256(material).digest()[0] & 1


def _decoy_priority(item: CausalEvidence) -> tuple[int, int, str]:
    role = item.role
    if "irrelevant" in role:
        tier = 0
    elif "misleading" in role:
        tier = 1
    elif "redundant" in role:
        tier = 2
    elif "proxy" in role:
        tier = 3
    else:
        tier = 4
    return tier, item.cost, item.evidence_id


def _with_routed_ambiguous_catalog(
    task: CausalTask,
    core_evidence: tuple[str, ...],
    seed: int,
) -> tuple[CausalTask, tuple[str, ...], str, tuple[AcquisitionLane, ...]]:
    """Pair every planned clue with an equal-cost alternative.

    The topology router reveals the active option labels but carries no fault
    information. This removes role-name leakage while preserving a fair,
    affordable route for every condition.
    """

    evidence_by_id = {item.evidence_id: item for item in task.evidence}
    core = [evidence_by_id[evidence_id] for evidence_id in core_evidence]
    noncore = [item for item in task.evidence if item.evidence_id not in core_evidence]
    router = min(
        noncore,
        key=lambda item: (
            0 if "irrelevant" in item.role else 1,
            item.cost,
            item.evidence_id,
        ),
    )
    candidates = sorted(
        (item for item in noncore if item.evidence_id != router.evidence_id),
        key=_decoy_priority,
    )
    if len(candidates) < len(core):
        raise ValueError("CAUSAL_V15_DECOY_SLOTS_MISSING")

    lanes: list[AcquisitionLane] = []
    replacements: dict[str, CausalEvidence] = {}
    active_labels: list[str] = []
    for index, active in enumerate(core):
        alternative = candidates[index]
        region = _REGIONS[index % len(_REGIONS)]
        active_is_a = _stable_bit(seed, active.evidence_id, alternative.evidence_id) == 0
        active_label = "A" if active_is_a else "B"
        alternative_label = "B" if active_is_a else "A"
        lane_id = f"L{index + 1}"
        shared = (
            "Operational observation with a potentially shared latent cause. "
            "Use the topology registry and purchased results; do not infer value "
            "from catalogue order."
        )
        replacements[active.evidence_id] = replace(
            active,
            region=region,
            description=f"Lane {lane_id} option {active_label}. {shared}",
        )
        replacements[alternative.evidence_id] = replace(
            alternative,
            region=region,
            cost=active.cost,
            description=f"Lane {lane_id} option {alternative_label}. {shared}",
        )
        active_labels.append(f"{lane_id}:{active_label}")
        lanes.append(
            AcquisitionLane(
                lane_id=lane_id,
                region=region,
                active_option=active.evidence_id,
                alternative_option=alternative.evidence_id,
                active_label=active_label,
            )
        )

    router_index = task.evidence_index()[router.evidence_id]
    replacements[router.evidence_id] = replace(
        router,
        region="controls",
        cost=1,
        role="acquisition_router",
        description=(
            "Topology registry for active acquisition-lane options. It routes "
            "purchases but is not a fault observation by itself."
        ),
        outcome_text=(
            "Active lane options: " + "; ".join(active_labels) + ". "
            + "Interpretation registry: " + json.dumps({
                "active_items": [
                    {"evidence_id": lane.active_option,
                     "interpretation": evidence_by_id[lane.active_option].description,
                     "cost": evidence_by_id[lane.active_option].cost}
                    for lane in lanes
                ],
                "rules": task.briefing,
            }, sort_keys=True),
        ),
        parents=(),
    )

    remainder_index = 0
    evidence = []
    for item in task.evidence:
        if item.evidence_id in replacements:
            replacement = replacements[item.evidence_id]
            if item.evidence_id != router.evidence_id:
                replacement = replace(replacement, outcome_text=tuple(
                    f"Interpretation: {item.description}. {outcome}"
                    for outcome in item.outcome_text
                ))
            evidence.append(replacement)
            continue
        region = _REGIONS[remainder_index % len(_REGIONS)]
        remainder_index += 1
        evidence.append(
            replace(
                item,
                region=region,
                description=(
                    f"Unassigned {region} observation. It may be direct, relational, "
                    "redundant, or share provenance with another channel."
                ),
                outcome_text=tuple(
                    f"Interpretation: {item.description}. {outcome}"
                    for outcome in item.outcome_text
                ),
            )
        )

    worlds: list[PossibleWorld] = []
    for world in task.worlds:
        outcomes = list(world.outcomes)
        outcomes[router_index] = 0
        worlds.append(replace(world, outcomes=tuple(outcomes)))

    nodes = []
    for node in task.nodes:
        if node.node_id == router.evidence_id:
            nodes.append(replace(node, parents=()))
        else:
            nodes.append(node)

    briefing = (
        "Fictional fault isolation with scarce telemetry. Catalogue wording does "
        "not identify diagnostic value. Purchase the topology registry before "
        "committing expensive lane options. Purchased results disclose their own "
        "candidate mappings. Track joint dependencies, shared provenance, and "
        "disconfirming evidence. " + task.briefing
    )
    return (
        replace(
            task,
            briefing=briefing,
            evidence=tuple(evidence),
            nodes=tuple(nodes),
            worlds=tuple(worlds),
        ),
        (router.evidence_id, *core_evidence),
        router.evidence_id,
        tuple(lanes),
    )


def _retag(task: CausalTask) -> CausalTask:
    return replace(
        task,
        task_id=task.task_id.replace("causal-v11-", "causal-v15-", 1),
        generator_version=CAUSAL_GENERATOR_V15_VERSION,
    )


def generate_causal_case_v15(
    seed: int, task_class: str, difficulty: str
) -> CausalGeneratedCaseV15:
    if task_class not in CAUSAL_TASK_CLASSES:
        raise ValueError(f"CAUSAL_V15_TASK_CLASS_UNKNOWN: {task_class}")
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"CAUSAL_V15_DIFFICULTY_UNKNOWN: {difficulty}")

    source: CausalGeneratedCaseV11 = generate_causal_case_v11(
        seed, task_class, difficulty
    )
    task = _reweight_observation_regime(source.causal_task)
    route = source.core_evidence
    router = None
    lanes: tuple[AcquisitionLane, ...] = ()
    if difficulty in {"moderate", "hard"}:
        task, route, router, lanes = _with_routed_ambiguous_catalog(
            task, source.core_evidence, seed
        )
    task = _retag(task)

    threshold = _SUFFICIENCY_THRESHOLD_V15[difficulty]
    proxy_ids = [
        item.evidence_id
        for item in task.evidence
        if item.role in {"cheap_correlated_proxy", "misleading_summary"}
    ]
    metrics = ExactOracle(task).metrics(
        threshold=threshold,
        max_size=7,
        cheap_ids=proxy_ids if task_class == "coordination_trap" else None,
    )
    evidence_by_id = {item.evidence_id: item for item in task.evidence}
    minimum_path_costs = tuple(evidence_by_id[item].cost for item in route)
    planned_path_cost = sum(minimum_path_costs)
    evidence_budget = planned_path_cost + _VERIFICATION_RESERVE_V15[difficulty]
    expected = faithful_regime_probability_v15(difficulty)

    if abs(metrics.observed_full_posterior - expected) > 1e-12:
        raise ValueError("CAUSAL_V15_POSTERIOR_CEILING_INVALID")
    if metrics.observed_full_posterior <= threshold:
        raise ValueError("CAUSAL_V15_THRESHOLD_UNREACHABLE")
    if metrics.minimum_sufficient_cost > planned_path_cost:
        raise ValueError("CAUSAL_V15_PLANNED_ROUTE_INSUFFICIENT")
    if evidence_budget >= sum(item.cost for item in task.evidence):
        raise ValueError("CAUSAL_V15_BUDGET_NOT_SCARCE")
    if difficulty in {"moderate", "hard"}:
        if router is None or len(lanes) != len(source.core_evidence):
            raise ValueError("CAUSAL_V15_ROUTING_CONTRACT_INVALID")
        if len({lane.region for lane in lanes}) < 3:
            raise ValueError("CAUSAL_V15_PERSPECTIVE_REGION_COVERAGE_INVALID")
        for lane in lanes:
            active = evidence_by_id[lane.active_option]
            alternative = evidence_by_id[lane.alternative_option]
            if active.cost != alternative.cost or active.region != alternative.region:
                raise ValueError("CAUSAL_V15_LANE_AMBIGUITY_INVALID")

    return CausalGeneratedCaseV15(
        causal_task=task,
        metrics=metrics,
        core_evidence=route,
        verification_evidence=source.verification_evidence,
        distractor=source.distractor,
        minimum_path_costs=minimum_path_costs,
        evidence_budget=evidence_budget,
        sufficiency_threshold=threshold,
        faithful_regime_probability=expected,
        topology_router=router,
        acquisition_lanes=lanes,
        perspective_lenses=tuple(lens.lens_id for lens in PERSPECTIVE_LENSES),
    )
