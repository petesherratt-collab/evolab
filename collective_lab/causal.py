from __future__ import annotations

from dataclasses import dataclass
from dataclasses import asdict
import hashlib
import json
from typing import Any

from .core import EvidenceItem, FaultTask


@dataclass(frozen=True)
class CausalNode:
    node_id: str
    kind: str
    parents: tuple[str, ...] = ()


@dataclass(frozen=True)
class CausalEvidence:
    evidence_id: str
    region: str
    cost: int
    role: str
    description: str
    outcome_text: tuple[str, ...]
    parents: tuple[str, ...]


@dataclass(frozen=True)
class PossibleWorld:
    fault: str
    nuisance: tuple[tuple[str, Any], ...]
    outcomes: tuple[int, ...]
    weight: float = 1.0

    def nuisance_mapping(self) -> dict[str, Any]:
        return dict(self.nuisance)


@dataclass(frozen=True)
class CausalTask:
    task_id: str
    task_class: str
    intended_difficulty: str
    briefing: str
    candidates: tuple[str, ...]
    correct_candidate: str
    nodes: tuple[CausalNode, ...]
    evidence: tuple[CausalEvidence, ...]
    worlds: tuple[PossibleWorld, ...]
    true_world_index: int
    generator_version: str

    def __post_init__(self) -> None:
        if len(self.candidates) != 5 or self.correct_candidate not in self.candidates:
            raise ValueError("CAUSAL_CANDIDATES_INVALID")
        if len(self.evidence) != 20:
            raise ValueError("CAUSAL_EVIDENCE_COUNT_INVALID")
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("CAUSAL_EVIDENCE_IDS_INVALID")
        if not 0 <= self.true_world_index < len(self.worlds):
            raise ValueError("CAUSAL_TRUE_WORLD_INVALID")
        if self.worlds[self.true_world_index].fault != self.correct_candidate:
            raise ValueError("CAUSAL_TRUE_FAULT_INVALID")
        if any(len(world.outcomes) != len(self.evidence) for world in self.worlds):
            raise ValueError("CAUSAL_WORLD_OUTCOMES_INVALID")
        if any(world.weight <= 0 for world in self.worlds):
            raise ValueError("CAUSAL_WORLD_WEIGHT_INVALID")
        if set(world.fault for world in self.worlds) != set(self.candidates):
            raise ValueError("CAUSAL_WORLD_FAULT_COVERAGE_INVALID")
        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("CAUSAL_NODE_IDS_INVALID")
        known_nodes = set(node_ids)
        if any(parent not in known_nodes for node in self.nodes for parent in node.parents):
            raise ValueError("CAUSAL_NODE_PARENT_INVALID")
        for evidence_index, item in enumerate(self.evidence):
            if item.cost not in {1, 3, 8}:
                raise ValueError("CAUSAL_EVIDENCE_COST_INVALID")
            if any(
                not 0 <= world.outcomes[evidence_index] < len(item.outcome_text)
                for world in self.worlds
            ):
                raise ValueError("CAUSAL_OUTCOME_DOMAIN_INVALID")
        masses = {
            candidate: sum(world.weight for world in self.worlds if world.fault == candidate)
            for candidate in self.candidates
        }
        if max(masses.values()) - min(masses.values()) > 1e-9:
            raise ValueError("CAUSAL_PRIOR_NOT_BALANCED")

    def evidence_index(self) -> dict[str, int]:
        return {item.evidence_id: index for index, item in enumerate(self.evidence)}

    def fingerprint(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def observed_outcomes(self) -> dict[str, int]:
        world = self.worlds[self.true_world_index]
        return {
            item.evidence_id: world.outcomes[index]
            for index, item in enumerate(self.evidence)
        }

    def to_fault_task(self) -> FaultTask:
        world = self.worlds[self.true_world_index]
        return FaultTask(
            task_id=self.task_id,
            task_class=self.task_class,
            difficulty=self.intended_difficulty,
            briefing=self.briefing,
            candidates=self.candidates,
            correct_candidate=self.correct_candidate,
            evidence=tuple(
                EvidenceItem(
                    evidence_id=item.evidence_id,
                    region=item.region,
                    cost=item.cost,
                    description=item.description,
                    result=item.outcome_text[world.outcomes[index]],
                )
                for index, item in enumerate(self.evidence)
            ),
            generator_version=self.generator_version,
        )
