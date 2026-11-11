from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from math import log
from pathlib import Path
import re
from typing import Iterable, Mapping, Sequence

from evolutionary_lab.evidence import verify_ledger

from .causal_generator import (
    CAUSAL_GENERATOR_VERSION,
    CAUSAL_TASK_CLASSES,
    DIFFICULTIES,
    generate_causal_case,
)
from .causal import CausalEvidence, CausalTask, PossibleWorld
from .ledger import ExclusiveRunLedger
from .oracle import ExactOracle


_TOKEN = re.compile(r"[a-z0-9_]+")
_EXPECTED_COSTS = {
    "additive": {"easy": 3, "moderate": 9, "hard": 24},
    "relational": {"easy": 6, "moderate": 18, "hard": 48},
    "coordination_trap": {"easy": 4, "moderate": 12, "hard": 17},
}


@dataclass(frozen=True)
class LeakageProbe:
    feature_set: str
    target: str
    train_cases: int
    test_cases: int
    baseline_accuracy: float
    accuracy: float
    threshold: float

    @property
    def passed(self) -> bool:
        return self.accuracy <= self.threshold

    def mapping(self) -> dict[str, object]:
        value = asdict(self)
        value["passed"] = self.passed
        return value


@dataclass(frozen=True)
class CausalAuditSummary:
    generator_version: str
    first_seed: int
    seeds_per_cell: int
    attempted: int
    accepted: int
    rejected: int
    unique_causal_fingerprints: int
    unique_public_fingerprints: int
    correct_label_counts: dict[str, int]
    correct_position_counts: dict[int, int]
    cell_counts: dict[str, int]
    rejection_counts: dict[str, int]
    metric_ranges: dict[str, dict[str, float]]
    leakage_probes: tuple[LeakageProbe, ...]
    property_checks: dict[str, bool]
    failures: tuple[str, ...]
    ledger_records: int
    ledger_head: str

    @property
    def passed(self) -> bool:
        return not self.failures

    def mapping(self) -> dict[str, object]:
        value = asdict(self)
        value["leakage_probes"] = [probe.mapping() for probe in self.leakage_probes]
        value["passed"] = self.passed
        return value


def _canonical_hash(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def rename_candidate_labels(
    task: CausalTask, mapping: Mapping[str, str]
) -> CausalTask:
    if set(mapping) != set(task.candidates) or len(set(mapping.values())) != len(mapping):
        raise ValueError("CAUSAL_RENAME_MAPPING_INVALID")
    if set(mapping) & set(mapping.values()):
        raise ValueError("CAUSAL_RENAME_TARGET_COLLISION")

    def rename_text(value: str) -> str:
        for source, target in mapping.items():
            value = value.replace(source, target)
        return value

    evidence = tuple(
        replace(
            item,
            description=rename_text(item.description),
            outcome_text=tuple(rename_text(text) for text in item.outcome_text),
        )
        for item in task.evidence
    )
    worlds = tuple(
        replace(
            world,
            fault=mapping[world.fault],
            nuisance=tuple(
                (key, mapping.get(value, value) if isinstance(value, str) else value)
                for key, value in world.nuisance
            ),
        )
        for world in task.worlds
    )
    return replace(
        task,
        briefing=rename_text(task.briefing),
        candidates=tuple(mapping[candidate] for candidate in task.candidates),
        correct_candidate=mapping[task.correct_candidate],
        evidence=evidence,
        worlds=worlds,
    )


def reorder_evidence(task: CausalTask, order: Sequence[int]) -> CausalTask:
    if sorted(order) != list(range(len(task.evidence))):
        raise ValueError("CAUSAL_EVIDENCE_ORDER_INVALID")
    return replace(
        task,
        evidence=tuple(task.evidence[index] for index in order),
        worlds=tuple(
            replace(world, outcomes=tuple(world.outcomes[index] for index in order))
            for world in task.worlds
        ),
    )


def rewrite_presentation(task: CausalTask) -> CausalTask:
    """Change only agent-visible prose, never graph or outcome semantics."""

    return replace(
        task,
        briefing=f"Presentation variant. {task.briefing}",
        evidence=tuple(
            replace(
                item,
                description=f"Reworded: {item.description}",
                outcome_text=tuple(f"Rendered result: {text}" for text in item.outcome_text),
            )
            for item in task.evidence
        ),
    )


def _posterior_close(
    left: Mapping[str, float], right: Mapping[str, float], *, tolerance: float = 1e-12
) -> bool:
    return set(left) == set(right) and all(
        abs(left[key] - right[key]) <= tolerance for key in left
    )


def causal_property_checks(first_seed: int) -> dict[str, bool]:
    checks = {
        "candidate_renaming_oracle_invariant": True,
        "candidate_renaming_renderer_invariant": True,
        "evidence_order_oracle_invariant": True,
        "evidence_order_renderer_invariant": True,
        "wording_oracle_invariant": True,
    }
    abstract_labels = tuple(f"candidate_{index}" for index in range(5))
    for task_class in CAUSAL_TASK_CLASSES:
        for difficulty in DIFFICULTIES:
            case = generate_causal_case(first_seed, task_class, difficulty)
            task = case.causal_task
            evidence_ids = tuple(item.evidence_id for item in task.evidence)
            original_posterior = ExactOracle(task).observed_posterior(evidence_ids)

            mapping = dict(zip(task.candidates, abstract_labels, strict=True))
            renamed = rename_candidate_labels(task, mapping)
            renamed_posterior = ExactOracle(renamed).observed_posterior(evidence_ids)
            expected_renamed = {
                mapping[candidate]: probability
                for candidate, probability in original_posterior.items()
            }
            checks["candidate_renaming_oracle_invariant"] &= _posterior_close(
                expected_renamed, renamed_posterior
            )
            original_render = task.to_fault_task()
            renamed_render = renamed.to_fault_task()
            checks["candidate_renaming_renderer_invariant"] &= (
                tuple(mapping[item] for item in original_render.candidates)
                == renamed_render.candidates
                and mapping[original_render.correct_candidate]
                == renamed_render.correct_candidate
                and tuple(item.evidence_id for item in original_render.evidence)
                == tuple(item.evidence_id for item in renamed_render.evidence)
            )

            order = tuple(reversed(range(len(task.evidence))))
            reordered = reorder_evidence(task, order)
            reordered_posterior = ExactOracle(reordered).observed_posterior(evidence_ids)
            checks["evidence_order_oracle_invariant"] &= _posterior_close(
                original_posterior, reordered_posterior
            )
            original_by_id = {
                item.evidence_id: (item.cost, item.description, item.result)
                for item in original_render.evidence
            }
            reordered_by_id = {
                item.evidence_id: (item.cost, item.description, item.result)
                for item in reordered.to_fault_task().evidence
            }
            checks["evidence_order_renderer_invariant"] &= original_by_id == reordered_by_id

            rewritten = rewrite_presentation(task)
            rewritten_posterior = ExactOracle(rewritten).observed_posterior(evidence_ids)
            checks["wording_oracle_invariant"] &= _posterior_close(
                original_posterior, rewritten_posterior
            )
    return checks


def _metadata_tokens(public: Mapping[str, object]) -> tuple[str, ...]:
    candidates = tuple(str(item) for item in public["candidates"])
    evidence = tuple(public["evidence_catalogue"])
    tokens = [
        f"class={public['task_class']}",
        f"difficulty={public['difficulty']}",
        *(f"candidate_{index}={candidate}" for index, candidate in enumerate(candidates)),
    ]
    for index, raw_item in enumerate(evidence):
        item = dict(raw_item)
        tokens.extend(
            (
                f"slot_{index}_region={item['region']}",
                f"slot_{index}_cost={item['cost']}",
                f"region_cost={item['region']}:{item['cost']}",
            )
        )
    return tuple(tokens)


def _text_tokens(public: Mapping[str, object]) -> tuple[str, ...]:
    parts = [str(public["briefing"]), *map(str, public["candidates"])]
    parts.extend(
        str(dict(item)["description"])
        for item in public["evidence_catalogue"]
    )
    return tuple(_TOKEN.findall(" ".join(parts).lower()))


def _audit_one(arguments: tuple[int, str, str]) -> dict[str, object]:
    seed, task_class, difficulty = arguments
    identity = {
        "seed": seed,
        "task_class": task_class,
        "difficulty": difficulty,
    }
    try:
        case = generate_causal_case(seed, task_class, difficulty)
    except Exception as exc:  # retain unexpected failures in the same immutable record
        reason = str(exc).split(":", 1)[0] or type(exc).__name__
        return {
            **identity,
            "accepted": False,
            "rejection_reason": reason,
            "rejection_detail": f"{type(exc).__name__}: {exc}",
        }

    task = case.causal_task
    public = case.task.public()
    return {
        **identity,
        "accepted": True,
        "rejection_reason": None,
        "causal_fingerprint": task.fingerprint(),
        "public_fingerprint": _canonical_hash(public),
        "correct_label": task.correct_candidate,
        "correct_position": task.candidates.index(task.correct_candidate),
        "metrics": case.metrics.mapping(),
        # Probe features are retained only in memory; the ledger stores their hashes.
        "metadata_tokens": _metadata_tokens(public),
        "text_tokens": _text_tokens(public),
        "metadata_probe_fingerprint": _canonical_hash(_metadata_tokens(public)),
        "text_probe_fingerprint": _canonical_hash(_text_tokens(public)),
    }


def _nb_accuracy(
    train: Sequence[dict[str, object]],
    test: Sequence[dict[str, object]],
    *,
    feature_key: str,
    target_key: str,
) -> tuple[float, float]:
    labels = sorted({str(item[target_key]) for item in train})
    if not labels or not test:
        return 1.0, 1.0
    class_counts = Counter(str(item[target_key]) for item in train)
    token_counts: dict[str, Counter[str]] = defaultdict(Counter)
    total_tokens: Counter[str] = Counter()
    vocabulary: set[str] = set()
    for item in train:
        label = str(item[target_key])
        features = tuple(str(token) for token in item[feature_key])
        token_counts[label].update(features)
        total_tokens[label] += len(features)
        vocabulary.update(features)
    vocabulary_size = max(1, len(vocabulary))
    total_train = len(train)

    def predict(item: dict[str, object]) -> str:
        features = tuple(str(token) for token in item[feature_key])
        scores: dict[str, float] = {}
        for label in labels:
            score = log(class_counts[label] / total_train)
            denominator = total_tokens[label] + vocabulary_size
            score += sum(
                log((token_counts[label][token] + 1) / denominator)
                for token in features
            )
            scores[label] = score
        return max(labels, key=lambda label: (scores[label], label))

    accuracy = sum(predict(item) == str(item[target_key]) for item in test) / len(test)
    test_counts = Counter(str(item[target_key]) for item in test)
    baseline = max(test_counts.values()) / len(test)
    return baseline, accuracy


def leakage_probes(
    records: Sequence[dict[str, object]], *, threshold: float = 0.40
) -> tuple[LeakageProbe, ...]:
    """Run deterministic public-view probes without using task IDs or hidden outcomes.

    The split is by seed, never by task, so the nine class/difficulty variants for a
    seed cannot occur on both sides.  Two balanced Latin diagonals are held out when
    a complete 25-seed cycle is present.
    """

    accepted = [item for item in records if item.get("accepted")]
    if not accepted:
        return ()
    candidate_labels = sorted({str(item["correct_label"]) for item in accepted})
    label_index = {label: index for index, label in enumerate(candidate_labels)}
    test_seeds = {
        int(item["seed"])
        for item in accepted
        if (label_index[str(item["correct_label"])] + int(item["correct_position"])) % 5
        in {0, 2}
    }
    train = [item for item in accepted if int(item["seed"]) not in test_seeds]
    test = [item for item in accepted if int(item["seed"]) in test_seeds]
    if not train or not test:
        return ()

    probes: list[LeakageProbe] = []
    for feature_set, feature_key in (
        ("metadata_only", "metadata_tokens"),
        ("text_only", "text_tokens"),
    ):
        for target, target_key in (
            ("correct_label", "correct_label"),
            ("correct_position", "correct_position"),
        ):
            baseline, accuracy = _nb_accuracy(
                train, test, feature_key=feature_key, target_key=target_key
            )
            probes.append(
                LeakageProbe(
                    feature_set=feature_set,
                    target=target,
                    train_cases=len(train),
                    test_cases=len(test),
                    baseline_accuracy=baseline,
                    accuracy=accuracy,
                    threshold=min(1.0, max(threshold, baseline + 0.15)),
                )
            )
    return tuple(probes)


def _metric_ranges(records: Iterable[dict[str, object]]) -> dict[str, dict[str, float]]:
    values: dict[str, list[float]] = defaultdict(list)
    for record in records:
        if not record.get("accepted"):
            continue
        for key, value in dict(record["metrics"]).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                values[key].append(float(value))
    return {
        key: {"minimum": min(items), "maximum": max(items)}
        for key, items in sorted(values.items())
        if items
    }


def audit_causal_generator(
    *,
    first_seed: int,
    seeds_per_cell: int,
    ledger_path: str | Path,
    workers: int = 1,
    probe_threshold: float = 0.40,
) -> CausalAuditSummary:
    if seeds_per_cell <= 0:
        raise ValueError("CAUSAL_AUDIT_SEED_COUNT_INVALID")
    if workers <= 0:
        raise ValueError("CAUSAL_AUDIT_WORKER_COUNT_INVALID")
    path = Path(ledger_path)
    if path.exists():
        raise FileExistsError(f"CAUSAL_AUDIT_LEDGER_EXISTS: {path}")

    arguments = [
        (seed, task_class, difficulty)
        for seed in range(first_seed, first_seed + seeds_per_cell)
        for task_class in CAUSAL_TASK_CLASSES
        for difficulty in DIFFICULTIES
    ]
    if workers == 1:
        records = [_audit_one(item) for item in arguments]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            records = list(pool.map(_audit_one, arguments, chunksize=1))

    labels: Counter[str] = Counter()
    positions: Counter[int] = Counter()
    cells: Counter[str] = Counter()
    rejections: Counter[str] = Counter()
    causal_fingerprints: set[str] = set()
    public_fingerprints: set[str] = set()
    failures: list[str] = []
    accepted = [record for record in records if record.get("accepted")]
    for record in records:
        cell = f"{record['task_class']}:{record['difficulty']}"
        if not record.get("accepted"):
            rejections[str(record["rejection_reason"])] += 1
            continue
        cells[cell] += 1
        labels[str(record["correct_label"])] += 1
        positions[int(record["correct_position"])] += 1
        causal_fingerprints.add(str(record["causal_fingerprint"]))
        public_fingerprints.add(str(record["public_fingerprint"]))
        expected_cost = _EXPECTED_COSTS[str(record["task_class"])][str(record["difficulty"])]
        actual_cost = int(dict(record["metrics"])["minimum_sufficient_cost"])
        if actual_cost != expected_cost:
            failures.append(
                f"CAUSAL_COST_BAND_INVALID:{cell}:{record['seed']}:{actual_cost}"
            )

    attempted = len(arguments)
    if len(accepted) != attempted:
        failures.append("CAUSAL_AUDIT_REJECTIONS_PRESENT")
    if len(causal_fingerprints) != len(accepted):
        failures.append("CAUSAL_FINGERPRINT_COLLISION")
    if len(public_fingerprints) != len(accepted):
        failures.append("CAUSAL_PUBLIC_FINGERPRINT_COLLISION")
    if cells and any(cells[cell] != seeds_per_cell for cell in cells):
        failures.append("CAUSAL_CELL_BALANCE_INVALID")
    if labels and max(labels.values()) != min(labels.values()):
        failures.append("CAUSAL_CORRECT_LABEL_BALANCE_INVALID")
    if len(labels) != 5:
        failures.append("CAUSAL_CORRECT_LABEL_COVERAGE_INVALID")
    if positions and max(positions.values()) != min(positions.values()):
        failures.append("CAUSAL_CORRECT_POSITION_BALANCE_INVALID")
    if set(positions) != set(range(5)):
        failures.append("CAUSAL_CORRECT_POSITION_COVERAGE_INVALID")

    probes = leakage_probes(records, threshold=probe_threshold)
    if len(probes) != 4:
        failures.append("CAUSAL_LEAKAGE_PROBES_INCOMPLETE")
    failures.extend(
        f"CAUSAL_LEAKAGE_PROBE_FAILED:{probe.feature_set}:{probe.target}"
        for probe in probes
        if not probe.passed
    )
    property_checks = causal_property_checks(first_seed)
    failures.extend(
        f"CAUSAL_PROPERTY_CHECK_FAILED:{name}"
        for name, passed in property_checks.items()
        if not passed
    )

    with ExclusiveRunLedger(path) as ledger:
        ledger.append(
            {
                "kind": "causal_audit_started",
                "generator_version": CAUSAL_GENERATOR_VERSION,
                "first_seed": first_seed,
                "seeds_per_cell": seeds_per_cell,
                "attempted": attempted,
                "workers": workers,
            }
        )
        for record in records:
            payload = {
                key: value
                for key, value in record.items()
                if key not in {"metadata_tokens", "text_tokens"}
            }
            payload["kind"] = "causal_candidate_audited"
            ledger.append(payload)

        # The final summary is added after the chain state is known; ledger metadata
        # below therefore describes the complete chain after this record is appended.
        provisional_records = attempted + 2
        ledger.append(
            {
                "kind": "causal_audit_completed",
                "accepted": len(accepted),
                "rejected": attempted - len(accepted),
                "failures": sorted(set(failures)),
                "leakage_probes": [probe.mapping() for probe in probes],
                "property_checks": property_checks,
                "expected_ledger_records": provisional_records,
            }
        )

    verification = verify_ledger(path)
    return CausalAuditSummary(
        generator_version=CAUSAL_GENERATOR_VERSION,
        first_seed=first_seed,
        seeds_per_cell=seeds_per_cell,
        attempted=attempted,
        accepted=len(accepted),
        rejected=attempted - len(accepted),
        unique_causal_fingerprints=len(causal_fingerprints),
        unique_public_fingerprints=len(public_fingerprints),
        correct_label_counts=dict(sorted(labels.items())),
        correct_position_counts=dict(sorted(positions.items())),
        cell_counts=dict(sorted(cells.items())),
        rejection_counts=dict(sorted(rejections.items())),
        metric_ranges=_metric_ranges(records),
        leakage_probes=probes,
        property_checks=property_checks,
        failures=tuple(sorted(set(failures))),
        ledger_records=int(verification["records"]),
        ledger_head=str(verification["head"]),
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the offline causal-generator audit")
    parser.add_argument("--first-seed", type=int, default=500)
    parser.add_argument("--seeds-per-cell", type=int, default=25)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--probe-threshold", type=float, default=0.40)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    summary = audit_causal_generator(
        first_seed=args.first_seed,
        seeds_per_cell=args.seeds_per_cell,
        ledger_path=args.ledger,
        workers=args.workers,
        probe_threshold=args.probe_threshold,
    )
    rendered = json.dumps(summary.mapping(), indent=2, sort_keys=True)
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
