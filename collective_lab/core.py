from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    region: str
    cost: int
    description: str
    result: str

    def public(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "region": self.region,
            "cost": self.cost,
            "description": self.description,
        }


@dataclass(frozen=True)
class FaultTask:
    task_id: str
    task_class: str
    difficulty: str
    briefing: str
    candidates: tuple[str, ...]
    correct_candidate: str
    evidence: tuple[EvidenceItem, ...]
    generator_version: str = "engineering-0.1"

    def __post_init__(self) -> None:
        if len(self.candidates) != 5 or self.correct_candidate not in self.candidates:
            raise ValueError("TASK_CANDIDATES_INVALID")
        ids = [item.evidence_id for item in self.evidence]
        if len(self.evidence) != 20 or len(ids) != len(set(ids)):
            raise ValueError("TASK_EVIDENCE_INVALID")
        if any(item.cost not in {1, 3, 8} for item in self.evidence):
            raise ValueError("TASK_EVIDENCE_COST_INVALID")

    def public(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_class": self.task_class,
            "difficulty": self.difficulty,
            "briefing": self.briefing,
            "candidates": list(self.candidates),
            "evidence_catalogue": [item.public() for item in self.evidence],
        }

    def evidence_map(self) -> dict[str, EvidenceItem]:
        return {item.evidence_id: item for item in self.evidence}

    def fingerprint(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Report:
    diagnosis: str
    probabilities: dict[str, float]
    cited_evidence: tuple[str, ...]
    rationale: str
    strongest_alternative: str
    recommended_verification: tuple[str, ...]

    def mapping(self) -> dict[str, Any]:
        return {
            "diagnosis": self.diagnosis,
            "probabilities": dict(self.probabilities),
            "cited_evidence": list(self.cited_evidence),
            "rationale": self.rationale,
            "strongest_alternative": self.strongest_alternative,
            "recommended_verification": list(self.recommended_verification),
        }


@dataclass(frozen=True)
class Score:
    brier_loss: float
    integrity_adjusted_loss: float
    accurate: bool
    malformed: bool
    unsupported_citations: tuple[str, ...]

    def mapping(self) -> dict[str, Any]:
        return asdict(self)


def parse_report(value: Any, task: FaultTask) -> Report:
    if not isinstance(value, dict):
        raise ValueError("REPORT_NOT_OBJECT")
    probabilities = value.get("probabilities")
    if not isinstance(probabilities, dict) or set(probabilities) != set(task.candidates):
        raise ValueError("REPORT_PROBABILITIES_KEYS_INVALID")
    parsed: dict[str, float] = {}
    for candidate, probability in probabilities.items():
        if isinstance(probability, bool) or not isinstance(probability, (int, float)):
            raise ValueError("REPORT_PROBABILITY_INVALID")
        parsed[candidate] = float(probability)
        if not 0.0 <= parsed[candidate] <= 1.0:
            raise ValueError("REPORT_PROBABILITY_INVALID")
    total = sum(parsed.values())
    if not 0.99 <= total <= 1.01:
        raise ValueError("REPORT_PROBABILITY_SUM_INVALID")
    parsed = {key: probability / total for key, probability in parsed.items()}
    diagnosis = str(value.get("diagnosis", ""))
    if diagnosis not in task.candidates:
        raise ValueError("REPORT_DIAGNOSIS_INVALID")

    def string_tuple(field: str) -> tuple[str, ...]:
        raw = value.get(field, [])
        if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
            raise ValueError(f"REPORT_{field.upper()}_INVALID")
        return tuple(raw)

    return Report(
        diagnosis=diagnosis,
        probabilities=parsed,
        cited_evidence=string_tuple("cited_evidence"),
        rationale=str(value.get("rationale", ""))[:4000],
        strongest_alternative=str(value.get("strongest_alternative", "")),
        recommended_verification=string_tuple("recommended_verification"),
    )


def score_report(task: FaultTask, report: Report | None, acquired: set[str]) -> Score:
    if report is None:
        return Score(2.0, 2.0, False, True, ())
    loss = sum(
        (report.probabilities[candidate] - float(candidate == task.correct_candidate)) ** 2
        for candidate in task.candidates
    )
    unsupported = tuple(sorted(set(report.cited_evidence) - acquired))
    return Score(
        brier_loss=loss,
        integrity_adjusted_loss=2.0 if unsupported else loss,
        accurate=report.diagnosis == task.correct_candidate,
        malformed=False,
        unsupported_citations=unsupported,
    )
