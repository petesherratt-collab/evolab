from __future__ import annotations

from dataclasses import dataclass
import random

from .core import EvidenceItem, FaultTask


GENERATOR_VERSION = "generated-0.3"
TASK_CLASSES = ("additive", "relational", "coordination_trap")

_DOMAINS = (
    ("cryogenic transfer loop", "transfer instability", ("supply", "return", "controls", "instrumentation")),
    ("orbital thermal test rig", "temperature excursion", ("cold plate", "radiator", "controls", "telemetry")),
    ("closed-loop nutrient skid", "delivery oscillation", ("feed", "recovery", "controls", "analysis")),
    ("vacuum coating line", "film nonuniformity", ("source", "chamber", "controls", "metrology")),
)

_FAULTS = (
    "actuator_stiction",
    "circulation_loss",
    "sensor_bias",
    "controller_timing_fault",
    "none_of_the_above",
)

_ROLE_COUNTS = {
    "direct": 8,
    "relational": 4,
    "redundant": 3,
    "misleading": 3,
    "irrelevant": 2,
}


@dataclass(frozen=True)
class GeneratedCase:
    task: FaultTask
    seed: int
    role_by_evidence: dict[str, str]
    sufficient_set: tuple[str, ...]
    verification_set: tuple[str, ...]
    relational_pairs: dict[str, str]
    phase_marker_by_evidence: dict[str, str]
    compatible_candidates: dict[str, tuple[str, ...]]


def _ordered_candidates(seed: int, correct: str) -> tuple[str, ...]:
    others = [candidate for candidate in _FAULTS if candidate != correct]
    random.Random(seed ^ 0xC011EC7).shuffle(others)
    position = seed % len(_FAULTS)
    others.insert(position, correct)
    return tuple(others)


def generate_case(
    seed: int,
    task_class: str,
    *,
    difficulty: str = "moderate",
) -> GeneratedCase:
    if task_class not in TASK_CLASSES:
        raise ValueError(f"TASK_CLASS_UNKNOWN: {task_class}")
    if difficulty not in {"easy", "moderate", "hard"}:
        raise ValueError(f"DIFFICULTY_UNKNOWN: {difficulty}")

    rng = random.Random(seed)
    system, symptom, regions = _DOMAINS[seed % len(_DOMAINS)]
    # Hold the fault identity fixed for blocks of five seeds while rotating its
    # displayed position through every candidate slot.
    correct = _FAULTS[(seed // 5) % len(_FAULTS)]
    candidates = _ordered_candidates(seed, correct)
    wrong = [candidate for candidate in _FAULTS if candidate != correct]
    trap_fault = wrong[seed % len(wrong)]

    roles = [role for role, count in _ROLE_COUNTS.items() for _ in range(count)]
    rng.shuffle(roles)
    numeric_ids = list(range(1, 21))
    rng.shuffle(numeric_ids)
    ids = [f"E{number:02d}" for number in numeric_ids]
    role_by_id = dict(zip(ids, roles, strict=True))

    ids_by_role: dict[str, list[str]] = {role: [] for role in _ROLE_COUNTS}
    for evidence_id, role in role_by_id.items():
        ids_by_role[role].append(evidence_id)
    for values in ids_by_role.values():
        values.sort()

    sufficient = (
        ids_by_role["direct"][0],
        ids_by_role["relational"][0],
        ids_by_role["relational"][1],
    )
    verification = (
        ids_by_role["direct"][1],
        ids_by_role["relational"][2],
        ids_by_role["relational"][3],
    )
    relational_pairs = {
        ids_by_role["relational"][0]: ids_by_role["relational"][1],
        ids_by_role["relational"][1]: ids_by_role["relational"][0],
        ids_by_role["relational"][2]: ids_by_role["relational"][3],
        ids_by_role["relational"][3]: ids_by_role["relational"][2],
    }
    phase_markers = {
        evidence_id: ("inverted" if index % 2 == 0 else "aligned")
        for index, evidence_id in enumerate(ids_by_role["relational"])
    }

    costs_by_role = {
        "direct": (3, 3, 8, 3, 8, 1, 3, 1),
        "relational": (3, 3, 3, 3),
        "redundant": (1, 3, 8),
        "misleading": (1, 1, 3),
        "irrelevant": (1, 8),
    }
    evidence: list[EvidenceItem] = []
    compatible_candidates: dict[str, tuple[str, ...]] = {}
    for catalogue_index, evidence_id in enumerate(ids):
        role = role_by_id[evidence_id]
        role_index = ids_by_role[role].index(evidence_id)
        region = regions[(catalogue_index + role_index) % len(regions)]
        if evidence_id in sufficient:
            region = regions[sufficient.index(evidence_id) % len(regions)]
        elif evidence_id in verification:
            region = regions[(verification.index(evidence_id) + 1) % len(regions)]
        cost = costs_by_role[role][role_index]
        description = {
            "direct": "Controlled operating-point measurement",
            "relational": "Phase-tagged trace requiring its paired context",
            "redundant": "Independent repeat of an operating indicator",
            "misleading": "Low-cost historical or proxy indicator",
            "irrelevant": "Ancillary environmental reading",
        }[role]

        if role == "direct":
            alternative = wrong[(role_index + 1) % len(wrong)]
            compatible_candidates[evidence_id] = tuple(
                dict.fromkeys((correct, trap_fault, alternative))
            )
            result = (
                f"The controlled pattern remains compatible with {correct}, {trap_fault}, "
                f"or {alternative}; this observation alone does not distinguish them."
            )
        elif role == "relational":
            pair = relational_pairs[evidence_id]
            compatible_candidates[evidence_id] = (correct, trap_fault)
            if phase_markers[evidence_id] == "inverted":
                result = (
                    f"The primary phase marker is inverted. Both {correct} and {trap_fault} "
                    f"predict this marker; {pair} is required to distinguish them."
                )
            else:
                result = (
                    f"The paired phase trace is aligned. Interpret only with {pair}: an "
                    f"inverted/aligned pair maps to {correct}, while inverted/inverted maps "
                    f"to {trap_fault}."
                )
        elif role == "redundant":
            compatible_candidates[evidence_id] = (correct, trap_fault)
            result = (
                f"A repeat channel remains compatible with {correct} or {trap_fault}, "
                "but shares a dependency with the primary measurements and cannot separate them."
            )
        elif role == "misleading":
            compatible_candidates[evidence_id] = tuple(_FAULTS)
            if task_class == "coordination_trap" or role_index == 0:
                result = (
                    f"The proxy initially favours {trap_fault}; its timestamp or operating "
                    "condition is not matched to the incident."
                )
            else:
                result = f"A historical association weakly favours {trap_fault} but is confounded."
        else:
            compatible_candidates[evidence_id] = tuple(_FAULTS)
            result = "The ancillary value is within its broad normal range and does not discriminate candidates."

        evidence.append(
            EvidenceItem(
                evidence_id=evidence_id,
                region=region,
                cost=cost,
                description=description,
                result=result,
            )
        )

    task = FaultTask(
        task_id=f"gen-{task_class}-{seed}",
        task_class=task_class,
        difficulty=difficulty,
        briefing=(
            f"The fictional {system} shows a repeatable {symptom}. Identify the single "
            "root fault. Catalogue entries disclose source and price but not their result."
        ),
        candidates=candidates,
        correct_candidate=correct,
        evidence=tuple(evidence),
        generator_version=GENERATOR_VERSION,
    )
    case = GeneratedCase(
        task=task,
        seed=seed,
        role_by_evidence=role_by_id,
        sufficient_set=sufficient,
        verification_set=verification,
        relational_pairs=relational_pairs,
        phase_marker_by_evidence=phase_markers,
        compatible_candidates=compatible_candidates,
    )
    validate_generated_case(case)
    return case


def validate_generated_case(case: GeneratedCase) -> None:
    task = case.task
    evidence_map = task.evidence_map()
    observed_counts = {role: 0 for role in _ROLE_COUNTS}
    for role in case.role_by_evidence.values():
        if role not in observed_counts:
            raise ValueError("GENERATOR_ROLE_UNKNOWN")
        observed_counts[role] += 1
    if observed_counts != _ROLE_COUNTS:
        raise ValueError("GENERATOR_COMPOSITION_INVALID")
    if set(case.role_by_evidence) != set(evidence_map):
        raise ValueError("GENERATOR_METADATA_IDS_INVALID")
    if set(case.compatible_candidates) != set(evidence_map):
        raise ValueError("GENERATOR_COMPATIBILITY_IDS_INVALID")
    if any(
        task.correct_candidate not in candidates or len(set(candidates)) < 2
        for candidates in case.compatible_candidates.values()
    ):
        raise ValueError("GENERATOR_SINGLE_CLUE_IDENTIFIES_TRUTH")
    relational_ids = {
        evidence_id
        for evidence_id, role in case.role_by_evidence.items()
        if role == "relational"
    }
    if set(case.relational_pairs) != relational_ids:
        raise ValueError("GENERATOR_RELATIONAL_PAIR_IDS_INVALID")
    for evidence_id, pair_id in case.relational_pairs.items():
        if evidence_id == pair_id or case.relational_pairs.get(pair_id) != evidence_id:
            raise ValueError("GENERATOR_RELATIONAL_PAIR_INVALID")
        if {
            case.phase_marker_by_evidence.get(evidence_id),
            case.phase_marker_by_evidence.get(pair_id),
        } != {"inverted", "aligned"}:
            raise ValueError("GENERATOR_RELATIONAL_PHASE_INVALID")
    if len(case.sufficient_set) < 3 or len(set(case.sufficient_set)) != len(case.sufficient_set):
        raise ValueError("GENERATOR_SUFFICIENT_SET_INVALID")
    relevant_ids = [
        evidence_id
        for evidence_id, role in case.role_by_evidence.items()
        if role in {"direct", "relational", "redundant"}
    ]
    for left_index, left_id in enumerate(relevant_ids):
        for right_id in relevant_ids[left_index + 1 :]:
            overlap = set(case.compatible_candidates[left_id]) & set(
                case.compatible_candidates[right_id]
            )
            if overlap == {task.correct_candidate}:
                raise ValueError("GENERATOR_TWO_CLUES_IDENTIFY_TRUTH")
    if len({evidence_map[item].region for item in case.sufficient_set}) < 2:
        raise ValueError("GENERATOR_SUFFICIENT_REGIONS_INVALID")
    if sum(evidence_map[item].cost for item in case.sufficient_set) > 60:
        raise ValueError("GENERATOR_SUFFICIENT_COST_INVALID")
    if all(evidence_map[item].cost == 1 for item in case.sufficient_set):
        raise ValueError("GENERATOR_CHEAP_ONLY_SOLUTION")
    if all(evidence_map[item].cost == 8 for item in case.sufficient_set):
        raise ValueError("GENERATOR_EXPENSIVE_ONLY_SOLUTION")
    if task.task_class == "coordination_trap":
        if sum(evidence_map[item].cost for item in case.verification_set) > 20:
            raise ValueError("GENERATOR_TRAP_VERIFICATION_TOO_EXPENSIVE")
        if len({evidence_map[item].region for item in case.verification_set}) < 2:
            raise ValueError("GENERATOR_TRAP_VERIFICATION_REGIONS_INVALID")
