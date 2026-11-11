from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import product
import random
from typing import Callable

from .causal import CausalEvidence, CausalNode, CausalTask, PossibleWorld
from .oracle import ExactOracle, OracleMetrics


CAUSAL_GENERATOR_VERSION = "causal-1.0"
CAUSAL_TASK_CLASSES = ("additive", "relational", "coordination_trap")
DIFFICULTIES = ("easy", "moderate", "hard")
_CANDIDATES = (
    "actuator_stiction",
    "circulation_loss",
    "sensor_bias",
    "controller_timing_fault",
    "none_of_the_above",
)
_REGIONS = ("source", "process", "controls", "instrumentation")


@dataclass(frozen=True)
class CausalGeneratedCase:
    causal_task: CausalTask
    metrics: OracleMetrics
    core_evidence: tuple[str, ...]
    verification_evidence: tuple[str, ...]
    distractor: str

    @property
    def task(self):
        return self.causal_task.to_fault_task()


@dataclass(frozen=True)
class _EvidenceDefinition:
    key: str
    role: str
    cost: int
    description: str
    outcome_text: tuple[str, ...]
    parents: tuple[str, ...]
    outcome: Callable[[str, dict[str, object]], int]


def _candidate_layout(seed: int) -> tuple[tuple[str, ...], str, str, dict[str, tuple[int, int, int]]]:
    correct = _CANDIDATES[(seed // 5) % len(_CANDIDATES)]
    distractors = [candidate for candidate in _CANDIDATES if candidate != correct]
    rng = random.Random(seed ^ 0xCA05A1)
    rng.shuffle(distractors)
    distractor = distractors[0]
    signatures = {
        correct: (0, 0, 0),
        distractors[0]: (0, 0, 1),
        distractors[1]: (0, 1, 0),
        distractors[2]: (1, 0, 0),
        distractors[3]: (1, 1, 1),
    }
    displayed = list(_CANDIDATES)
    rng.shuffle(displayed)
    displayed.remove(correct)
    displayed.insert(seed % 5, correct)
    return tuple(displayed), correct, distractor, signatures


def _tier(difficulty: str) -> int:
    return {"easy": 1, "moderate": 3, "hard": 8}[difficulty]


def _mapped_bit_text(
    prefix: str,
    signatures: dict[str, tuple[int, int, int]],
    bit: int,
) -> tuple[str, str]:
    groups = {
        value: ", ".join(
            sorted(candidate for candidate, signature in signatures.items() if signature[bit] == value)
        )
        for value in (0, 1)
    }
    return tuple(
        f"{prefix}: {value}. Under this channel's mapping, compatible candidates are: {groups[value]}."
        for value in (0, 1)
    )


def _relational_trace_text(
    signatures: dict[str, tuple[int, int, int]], bit: int
) -> tuple[str, str]:
    groups = {
        value: ", ".join(
            sorted(candidate for candidate, signature in signatures.items() if signature[bit] == value)
        )
        for value in (0, 1)
    }
    mapping = f"XOR 0 maps to [{groups[0]}]; XOR 1 maps to [{groups[1]}]."
    return (
        f"Trace phase: 0. Combine with this pair's reference. {mapping}",
        f"Trace phase: 1. Combine with this pair's reference. {mapping}",
    )


def _make_additive(
    signatures: dict[str, tuple[int, int, int]], difficulty: str
) -> tuple[list[_EvidenceDefinition], list[tuple[str, dict[str, object], float]], tuple[str, ...], tuple[str, ...]]:
    tier = _tier(difficulty)
    definitions: list[_EvidenceDefinition] = []
    core: list[str] = []
    for bit in range(3):
        key = f"core_{bit}"
        core.append(key)
        definitions.append(
            _EvidenceDefinition(
                key, "independent_direct", tier,
                f"Independent diagnostic channel for signature bit {bit + 1}",
                _mapped_bit_text("Observed channel bit", signatures, bit),
                ("fault", f"signature_{bit}"),
                lambda fault, nuisance, bit=bit: signatures[fault][bit],
            )
        )
    for index in range(5):
        bit = index % 3
        noise = f"noise_{bit}"
        weak_cost = 1 if difficulty == "easy" else 8
        definitions.append(
            _EvidenceDefinition(
                f"weak_{index}", "independent_weak", weak_cost,
                f"Noisy independent repeat for signature bit {bit + 1}",
                _mapped_bit_text("Noisy repeat bit", signatures, bit),
                ("fault", f"signature_{bit}", noise),
                (
                    (lambda fault, nuisance, noise=noise: int(nuisance[noise]))
                    if difficulty == "hard"
                    else (lambda fault, nuisance, bit=bit, noise=noise: signatures[fault][bit] ^ int(nuisance[noise]))
                ),
            )
        )
    for index in range(3):
        bit = index
        redundant_cost = 1 if difficulty == "easy" else 8
        definitions.append(
            _EvidenceDefinition(
                f"redundant_{index}", "redundant", redundant_cost,
                f"Correlated repeat of signature bit {bit + 1}",
                _mapped_bit_text("Correlated repeat bit", signatures, bit),
                ("fault", f"signature_{bit}"),
                (
                    (lambda fault, nuisance, bit=bit: bit % 2)
                    if difficulty == "hard"
                    else (lambda fault, nuisance, bit=bit: signatures[fault][bit])
                ),
            )
        )
    for index in range(3):
        definitions.append(
            _EvidenceDefinition(
                f"misleading_{index}", "misleading_proxy", 1,
                "Historical proxy with an independent nuisance source",
                ("Historical proxy bit: 0.", "Historical proxy bit: 1."),
                (f"noise_{index}",),
                lambda fault, nuisance, index=index: int(nuisance[f"noise_{index}"]),
            )
        )
    for index in range(6):
        definitions.append(
            _EvidenceDefinition(
                f"irrelevant_{index}", "irrelevant", 1 if index < 4 else 3,
                "Ancillary reading outside the diagnostic path",
                ("Ancillary state: nominal.", "Ancillary state: elevated."),
                (),
                lambda fault, nuisance, index=index: index % 2,
            )
        )
    worlds = []
    for fault in signatures:
        for noise_values in product((0, 1), repeat=3):
            nuisance = {f"noise_{index}": value for index, value in enumerate(noise_values)}
            weight = float(3 ** sum(value == 0 for value in noise_values))
            worlds.append((fault, nuisance, weight))
    return definitions, worlds, tuple(core), ()


def _make_relational(
    signatures: dict[str, tuple[int, int, int]], difficulty: str
) -> tuple[list[_EvidenceDefinition], list[tuple[str, dict[str, object], float]], tuple[str, ...], tuple[str, ...]]:
    tier = _tier(difficulty)
    definitions: list[_EvidenceDefinition] = []
    core: list[str] = []
    for pair in range(4):
        bit = pair if pair < 3 else 0
        context = f"context_{pair}"
        left_key = f"pair_{pair}_reference"
        right_key = f"pair_{pair}_trace"
        if pair < 3:
            core.extend((left_key, right_key))
        pair_cost = tier if pair < 3 else 8
        definitions.extend(
            (
                _EvidenceDefinition(
                    left_key, "relational_reference", pair_cost,
                    f"Reference member of diagnostic pair {pair + 1}",
                    ("Reference phase: 0.", "Reference phase: 1."),
                    (context,),
                    lambda fault, nuisance, context=context: int(nuisance[context]),
                ),
                _EvidenceDefinition(
                    right_key, "relational_trace", pair_cost,
                    f"Trace member of diagnostic pair {pair + 1}; XOR with its reference",
                    _relational_trace_text(signatures, bit),
                    ("fault", f"signature_{bit}", context),
                    (
                        (lambda fault, nuisance, context=context: int(nuisance[context]))
                        if difficulty == "hard" and pair == 3
                        else (lambda fault, nuisance, bit=bit, context=context: int(nuisance[context]) ^ signatures[fault][bit])
                    ),
                ),
            )
        )
    for index in range(4):
        source = f"pair_{index}_reference" if index % 2 == 0 else f"pair_{index}_trace"
        source_pair = index
        bit = source_pair if source_pair < 3 else 0
        context = f"context_{source_pair}"
        redundant_cost = 1 if difficulty == "easy" else 8
        definitions.append(
            _EvidenceDefinition(
                f"redundant_{index}", "redundant_pair_member", redundant_cost,
                "Correlated duplicate of one relational pair member",
                ("Duplicate phase: 0.", "Duplicate phase: 1."),
                (source,),
                (
                    (lambda fault, nuisance, index=index: index % 2)
                    if difficulty == "hard"
                    else (
                        (lambda fault, nuisance, context=context: int(nuisance[context]))
                        if index % 2 == 0
                        else (lambda fault, nuisance, bit=bit, context=context: int(nuisance[context]) ^ signatures[fault][bit])
                    )
                ),
            )
        )
    for index in range(4):
        definitions.append(
            _EvidenceDefinition(
                f"misleading_{index}", "misleading_unpaired", 1,
                "Unpaired phase snapshot from an uncontrolled cycle",
                ("Unpaired phase: 0.", "Unpaired phase: 1."),
                (),
                lambda fault, nuisance, index=index: index % 2,
            )
        )
    for index in range(4):
        definitions.append(
            _EvidenceDefinition(
                f"irrelevant_{index}", "irrelevant", 1 if index < 2 else 3,
                "Ancillary reading outside the paired diagnostic channels",
                ("Ancillary state: nominal.", "Ancillary state: elevated."),
                (),
                lambda fault, nuisance, index=index: index % 2,
            )
        )
    worlds = []
    for fault in signatures:
        for context_values in product((0, 1), repeat=4):
            nuisance = {f"context_{index}": value for index, value in enumerate(context_values)}
            worlds.append((fault, nuisance, 1.0))
    return definitions, worlds, tuple(core), ()


def _make_trap(
    signatures: dict[str, tuple[int, int, int]], difficulty: str, distractor: str
) -> tuple[list[_EvidenceDefinition], list[tuple[str, dict[str, object], float]], tuple[str, ...], tuple[str, ...]]:
    physical_cost = {"easy": 1, "moderate": 3, "hard": 3}[difficulty]
    calibration_cost = {"easy": 1, "moderate": 3, "hard": 8}[difficulty]
    provenance_cost = {"easy": 1, "moderate": 1, "hard": 3}[difficulty]
    definitions: list[_EvidenceDefinition] = []
    cheap: list[str] = []
    for index in range(6):
        bit = index % 3
        key = f"cheap_proxy_{index}"
        cheap.append(key)
        definitions.append(
            _EvidenceDefinition(
                key, "cheap_correlated_proxy", 1,
                f"Cached estimator output for signature bit {bit + 1}",
                _mapped_bit_text("Cached estimator bit", signatures, bit),
                ("fault", "source_stale", "proxy_fault"),
                lambda fault, nuisance, bit=bit: signatures[
                    str(nuisance["proxy_fault"]) if nuisance["source_stale"] else fault
                ][bit],
            )
        )
    definitions.extend(
        (
            _EvidenceDefinition(
                "source_provenance", "verification", provenance_cost,
                "Check whether the cached estimator is current",
                ("Estimator source: current.", "Estimator source: stale."),
                ("source_stale",),
                lambda fault, nuisance: int(bool(nuisance["source_stale"])),
            ),
            _EvidenceDefinition(
                "source_repeat", "redundant_verification", 8,
                "Independent provenance audit of the cached estimator",
                ("Independent audit: current.", "Independent audit: stale."),
                ("source_stale",),
                lambda fault, nuisance: int(bool(nuisance["source_stale"])),
            ),
        )
    )
    physical: list[str] = []
    for bit in range(3):
        key = f"physical_{bit}"
        physical.append(key)
        definitions.append(
            _EvidenceDefinition(
                key, "physical_direct", physical_cost,
                f"Physical measurement for signature bit {bit + 1}, before calibration correction",
                _mapped_bit_text("Physical bit before polarity correction", signatures, bit),
                ("fault", f"signature_{bit}", "calibration_inverted"),
                lambda fault, nuisance, bit=bit: signatures[fault][bit] ^ int(bool(nuisance["calibration_inverted"])),
            )
        )
    definitions.append(
        _EvidenceDefinition(
            "calibration", "verification", calibration_cost,
            "Read the polarity calibration for physical measurements",
            ("Calibration polarity: normal.", "Calibration polarity: inverted."),
            ("calibration_inverted",),
            lambda fault, nuisance: int(bool(nuisance["calibration_inverted"])),
        )
    )
    for index in range(3):
        bit = index
        repeat_cost = 1 if difficulty == "easy" else 8
        definitions.append(
            _EvidenceDefinition(
                f"physical_repeat_{index}", "redundant_physical", repeat_cost,
                f"Correlated repeat of physical signature bit {bit + 1}",
                _mapped_bit_text("Repeated physical bit before polarity correction", signatures, bit),
                ("fault", f"signature_{bit}", "calibration_inverted"),
                (
                    (lambda fault, nuisance, bit=bit: bit % 2)
                    if difficulty == "hard"
                    else (lambda fault, nuisance, bit=bit: signatures[fault][bit] ^ int(bool(nuisance["calibration_inverted"])))
                ),
            )
        )
    for index in range(3):
        definitions.append(
            _EvidenceDefinition(
                f"proxy_summary_{index}", "misleading_summary", 1,
                "Summary derived from the same cached estimator",
                _mapped_bit_text("Proxy summary bit", signatures, index),
                ("proxy_fault",),
                lambda fault, nuisance, index=index: signatures[str(nuisance["proxy_fault"])][index],
            )
        )
    for index in range(2):
        definitions.append(
            _EvidenceDefinition(
                f"irrelevant_{index}", "irrelevant", 1,
                "Ancillary environmental reading",
                ("Ancillary state: nominal.", "Ancillary state: elevated."),
                (),
                lambda fault, nuisance, index=index: index,
            )
        )
    worlds = []
    for fault in signatures:
        for source_stale, proxy_fault, calibration in product((False, True), signatures, (False, True)):
            nuisance = {
                "source_stale": source_stale,
                "proxy_fault": proxy_fault,
                "calibration_inverted": calibration,
            }
            worlds.append((fault, nuisance, 1.0))
    core = tuple(physical + ["calibration"])
    verification = tuple(["source_provenance"] + physical + ["calibration"])
    return definitions, worlds, core, verification


def _difficulty_from_cost(task_class: str, minimum_cost: int) -> str:
    thresholds = {
        "additive": (5, 15),
        "relational": (10, 30),
        "coordination_trap": (7, 15),
    }[task_class]
    if minimum_cost <= thresholds[0]:
        return "easy"
    if minimum_cost <= thresholds[1]:
        return "moderate"
    return "hard"


def generate_causal_case(seed: int, task_class: str, difficulty: str) -> CausalGeneratedCase:
    if task_class not in CAUSAL_TASK_CLASSES:
        raise ValueError(f"CAUSAL_TASK_CLASS_UNKNOWN: {task_class}")
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"CAUSAL_DIFFICULTY_UNKNOWN: {difficulty}")
    candidates, correct, distractor, signatures = _candidate_layout(seed)
    if task_class == "additive":
        definitions, world_specs, core_keys, verification_keys = _make_additive(signatures, difficulty)
        class_instruction = "Independent channels each report one candidate-signature bit. Accumulate them."
    elif task_class == "relational":
        definitions, world_specs, core_keys, verification_keys = _make_relational(signatures, difficulty)
        class_instruction = "For each numbered pair, XOR its reference and trace to recover one signature bit."
    else:
        definitions, world_specs, core_keys, verification_keys = _make_trap(signatures, difficulty, distractor)
        class_instruction = "Cached estimator bits may be stale. Physical bits require the polarity calibration."

    seed_material = f"{CAUSAL_GENERATOR_VERSION}|{task_class}|{difficulty}|{seed}".encode("utf-8")
    layout_seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "big")
    rng = random.Random(layout_seed)
    numeric_ids = list(range(1, 21))
    rng.shuffle(numeric_ids)
    rng.shuffle(definitions)
    key_to_id = {
        definition.key: f"E{numeric_ids[index]:02d}"
        for index, definition in enumerate(definitions)
    }
    evidence = tuple(
        CausalEvidence(
            evidence_id=key_to_id[definition.key],
            region=_REGIONS[index % len(_REGIONS)],
            cost=definition.cost,
            role=definition.role,
            description=definition.description,
            outcome_text=definition.outcome_text,
            parents=tuple(key_to_id.get(parent, parent) for parent in definition.parents),
        )
        for index, definition in enumerate(definitions)
    )
    nodes = [CausalNode("fault", "fault")]
    definition_keys = {definition.key for definition in definitions}
    parent_names = sorted(
        {
            parent
            for definition in definitions
            for parent in definition.parents
            if parent != "fault" and parent not in definition_keys
        }
    )
    nodes.extend(
        CausalNode(
            parent,
            "latent" if parent.startswith("signature_") else "nuisance",
            ("fault",) if parent.startswith("signature_") else (),
        )
        for parent in parent_names
    )
    nodes.extend(
        CausalNode(
            key_to_id[definition.key],
            "observation",
            tuple(key_to_id.get(parent, parent) for parent in definition.parents),
        )
        for definition in definitions
    )
    worlds: list[PossibleWorld] = []
    true_world_index = -1
    context_rng = random.Random(seed ^ 0xC07E57)
    target_context = tuple(context_rng.randrange(2) for _ in range(4))
    for fault, nuisance, weight in world_specs:
        outcomes = tuple(definition.outcome(fault, nuisance) for definition in definitions)
        world = PossibleWorld(
            fault=fault,
            nuisance=tuple(sorted(nuisance.items())),
            outcomes=outcomes,
            weight=weight,
        )
        worlds.append(world)
        is_true = fault == correct
        if task_class == "additive":
            is_true = is_true and all(not nuisance[f"noise_{index}"] for index in range(3))
        elif task_class == "relational":
            is_true = is_true and tuple(nuisance[f"context_{index}"] for index in range(4)) == target_context
        else:
            is_true = (
                is_true
                and nuisance["source_stale"] is True
                and nuisance["proxy_fault"] == distractor
                and nuisance["calibration_inverted"] is False
            )
        if is_true and true_world_index < 0:
            true_world_index = len(worlds) - 1
    if true_world_index < 0:
        raise ValueError("CAUSAL_TRUE_WORLD_NOT_FOUND")

    causal_task = CausalTask(
        task_id=f"causal-{task_class}-{difficulty}-{seed}",
        task_class=task_class,
        intended_difficulty=difficulty,
        briefing=(
            "Fictional fault isolation. Candidate mappings are disclosed only inside purchased "
            f"diagnostic evidence. {class_instruction}"
        ),
        candidates=candidates,
        correct_candidate=correct,
        nodes=tuple(nodes),
        evidence=evidence,
        worlds=tuple(worlds),
        true_world_index=true_world_index,
        generator_version=CAUSAL_GENERATOR_VERSION,
    )
    oracle = ExactOracle(causal_task)
    proxy_ids = [
        item.evidence_id
        for item in evidence
        if item.role in {"cheap_correlated_proxy", "misleading_summary"}
    ]
    metrics = oracle.metrics(
        max_size=6,
        cheap_ids=proxy_ids if task_class == "coordination_trap" else None,
    )
    observed_difficulty = _difficulty_from_cost(task_class, metrics.minimum_sufficient_cost)
    if observed_difficulty != difficulty:
        raise ValueError(
            f"CAUSAL_DIFFICULTY_MISMATCH: intended={difficulty} observed={observed_difficulty} "
            f"cost={metrics.minimum_sufficient_cost}"
        )
    if metrics.minimum_sufficient_clues < 3:
        raise ValueError("CAUSAL_TOO_FEW_REQUIRED_CLUES")
    if difficulty == "easy" and metrics.minimum_cost_sufficient_sets < 4:
        raise ValueError("CAUSAL_EASY_PATH_DIVERSITY_MISSING")
    if difficulty in {"moderate", "hard"} and metrics.minimum_cost_sufficient_sets != 1:
        raise ValueError("CAUSAL_DIFFICULTY_PATH_SCARCITY_INVALID")
    if task_class == "additive":
        if metrics.maximum_single_information_gain <= 0:
            raise ValueError("CAUSAL_ADDITIVE_SINGLE_GAIN_MISSING")
    elif task_class == "relational":
        pair_ids = tuple(key_to_id[key] for key in core_keys[:2])
        if any(oracle.information_gain((item,)) > 1e-9 for item in pair_ids):
            raise ValueError("CAUSAL_RELATIONAL_MARGINAL_LEAK")
        if oracle.synergy(pair_ids) <= 0:
            raise ValueError("CAUSAL_RELATIONAL_SYNERGY_MISSING")
    else:
        if metrics.cheap_distractor != distractor:
            raise ValueError("CAUSAL_TRAP_DISTRACTOR_INVALID")
        if metrics.cheap_distractor_posterior <= metrics.cheap_correct_posterior:
            raise ValueError("CAUSAL_TRAP_NOT_MISLEADING")
        verification_ids = tuple(key_to_id[key] for key in verification_keys)
        verified = oracle.observed_posterior(verification_ids)
        if verified[correct] < 0.90:
            raise ValueError("CAUSAL_TRAP_VERIFICATION_INSUFFICIENT")
        verification_cost = sum(
            next(item.cost for item in evidence if item.evidence_id == evidence_id)
            for evidence_id in verification_ids
        )
        if verification_cost > 20:
            raise ValueError("CAUSAL_TRAP_VERIFICATION_OVER_BUDGET")

    return CausalGeneratedCase(
        causal_task=causal_task,
        metrics=metrics,
        core_evidence=tuple(key_to_id[key] for key in core_keys),
        verification_evidence=tuple(key_to_id[key] for key in verification_keys),
        distractor=distractor,
    )
