"""Prospective population sampling; never select cases by the realized answer."""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, replace
import hashlib
import random

from .causal import CausalTask
from .causal_generator import generate_causal_case
from .causal_generator_v11 import _with_hard_adaptive_branch, _with_observation_regime
from .causal_generator_v15 import _reweight_observation_regime, faithful_regime_probability_v15

VERSION = "causal-1.6-dev"


def world_weight_boundaries(task: CausalTask) -> tuple[int, ...]:
    """Exact integer tickets, avoiding floating point cumulative sampling bias."""
    boundaries = []
    total = 0
    for world in task.worlds:
        weight = int(world.weight)
        if weight <= 0 or weight != world.weight:
            raise ValueError("V16_NONINTEGER_WORLD_WEIGHT")
        total += weight
        boundaries.append(total)
    return tuple(boundaries)


def sample_world_index(task: CausalTask, world_seed: int) -> int:
    boundaries = world_weight_boundaries(task)
    material = f"{VERSION}|world|{world_seed}".encode()
    rng = random.Random(int.from_bytes(hashlib.sha256(material).digest(), "big"))
    return bisect_right(boundaries, rng.randrange(boundaries[-1]))


@dataclass(frozen=True)
class CausalGeneratedCaseV16:
    causal_task: CausalTask
    packet_ids: tuple[str, ...]
    acquisition_budget: int
    faithful_probability: float

    @property
    def task(self):
        return self.causal_task.to_fault_task()

    def packet(self) -> dict[str, str]:
        evidence = self.task.evidence_map()
        return {eid: evidence[eid].result for eid in self.packet_ids}


def generate_causal_case_v16(
    layout_seed: int, task_class: str, difficulty: str, *, world_seed: int,
) -> CausalGeneratedCaseV16:
    # The legacy constructor supplies a structural template, not the new truth.
    # Its original selected world and answer are discarded below.
    base = generate_causal_case(layout_seed, task_class, difficulty)
    structural = base.causal_task
    packet = set(base.core_evidence)
    route_cost = sum(e.cost for e in structural.evidence if e.evidence_id in packet)
    if difficulty == "hard":
        structural, _, _, branch = _with_hard_adaptive_branch(base, layout_seed)
        # Both probes are included regardless of the sampled branch. Packet
        # membership must not reveal a private world-dependent path.
        packet.update((branch.router_evidence, *branch.branch_evidence))
        route_cost += 1  # one routing check and one active probe, not both probes
    if task_class == "coordination_trap":
        packet.update(e.evidence_id for e in structural.evidence
                      if e.role == "cheap_correlated_proxy" or
                      "Check whether the cached estimator" in e.description)

    # Make previously ambiguous hard-repeat semantics explicit. These items
    # remain available in the acquisition experiment, but are not diagnostic.
    evidence = []
    for item in structural.evidence:
        description = item.description
        if difficulty == "hard":
            if item.role == "independent_weak":
                description += "; at this setting it is independent noise, P(bit=1)=1/4, not a signature reading"
            if item.role in {"redundant", "redundant_pair_member", "redundant_physical"}:
                description += "; at this setting this is a fixed diagnostic-independent placeholder"
            if "Trace member of diagnostic pair 4" in description:
                description += "; at this setting it copies the reference, so XOR is always zero and is not diagnostic"
        if item.role == "misleading_summary":
            description += "; this reports the stored proxy candidate even when the estimator is current"
        evidence.append(replace(item, description=description))
    structural = replace(structural, evidence=tuple(evidence))
    population = _reweight_observation_regime(_with_observation_regime(structural))
    index = sample_world_index(population, world_seed)
    faithful = faithful_regime_probability_v15(difficulty)
    identifier = hashlib.sha256(
        f"{VERSION}|{layout_seed}|{world_seed}|{task_class}|{difficulty}".encode()
    ).hexdigest()[:24]
    probability_model = (
        " Public probability model: the five latent faults have equal prior probability. "
        f"One shared observation regime equals the latent fault with probability {faithful:.16g}; "
        f"each other candidate regime has probability {(1-faithful)/4:.16g}. "
        "Diagnostic signature mappings identify the regime, not necessarily the latent fault. "
        "Do not multiply this shared reliability factor once per clue. "
        "Relational reference phases are independent fair bits. Calibration inversion, "
        "cached-source staleness and the hard active branch are independent fair bits. "
        "The stored proxy candidate is independent and uniform over all five candidates. "
        "Additive repeat noise bits are independent with P(flip)=1/4; repeats of the same "
        "bit share that noise bit. Ignore the inactive hard branch probe. "
        "Apply only the disclosed dependencies; residual regime uncertainty remains even "
        "after resolving the diagnostic signature."
    )
    task = replace(population, true_world_index=index,
                   correct_candidate=population.worlds[index].fault,
                   task_id=f"causal-v16-{identifier}", generator_version=VERSION,
                   briefing=population.briefing + probability_model)
    return CausalGeneratedCaseV16(
        task, tuple(sorted(packet)), route_cost + {"easy": 2, "moderate": 1, "hard": 2}[difficulty],
        faithful,
    )
