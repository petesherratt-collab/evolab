from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json

from .generator import GENERATOR_VERSION, TASK_CLASSES, generate_case


@dataclass(frozen=True)
class GeneratorAudit:
    generator_version: str
    first_seed: int
    seeds_per_class: int
    cases: int
    unique_fingerprints: int
    correct_label_counts: dict[str, int]
    correct_position_counts: dict[int, int]
    class_counts: dict[str, int]
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures

    def mapping(self) -> dict[str, object]:
        value = asdict(self)
        value["passed"] = self.passed
        return value


def audit_generator(*, first_seed: int = 0, seeds_per_class: int = 1000) -> GeneratorAudit:
    fingerprints: set[str] = set()
    labels: Counter[str] = Counter()
    positions: Counter[int] = Counter()
    classes: Counter[str] = Counter()
    failures: list[str] = []
    for task_class in TASK_CLASSES:
        for seed in range(first_seed, first_seed + seeds_per_class):
            try:
                case = generate_case(seed, task_class)
            except ValueError as exc:
                failures.append(f"{task_class}:{seed}:{exc}")
                continue
            task = case.task
            fingerprint = task.fingerprint()
            if fingerprint in fingerprints:
                failures.append(f"{task_class}:{seed}:DUPLICATE_FINGERPRINT")
            fingerprints.add(fingerprint)
            labels[task.correct_candidate] += 1
            positions[task.candidates.index(task.correct_candidate)] += 1
            classes[task.task_class] += 1

    expected_cases = seeds_per_class * len(TASK_CLASSES)
    if len(fingerprints) != expected_cases:
        failures.append("FINGERPRINT_COUNT_INVALID")
    expected_label_count = expected_cases // 5
    if set(labels.values()) != {expected_label_count}:
        failures.append("CORRECT_LABEL_BALANCE_INVALID")
    if set(positions.values()) != {expected_label_count}:
        failures.append("CORRECT_POSITION_BALANCE_INVALID")
    if any(classes[name] != seeds_per_class for name in TASK_CLASSES):
        failures.append("TASK_CLASS_BALANCE_INVALID")

    return GeneratorAudit(
        generator_version=GENERATOR_VERSION,
        first_seed=first_seed,
        seeds_per_class=seeds_per_class,
        cases=expected_cases,
        unique_fingerprints=len(fingerprints),
        correct_label_counts=dict(sorted(labels.items())),
        correct_position_counts=dict(sorted(positions.items())),
        class_counts=dict(sorted(classes.items())),
        failures=tuple(failures),
    )


if __name__ == "__main__":
    print(json.dumps(audit_generator().mapping(), indent=2, sort_keys=True))
