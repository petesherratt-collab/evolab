from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from evolutionary_lab.evidence import verify_ledger

from .adaptive_v11 import adaptive_choice_metrics
from .causal import CausalTask
from .causal_audit import (
    LeakageProbe,
    _metadata_tokens,
    _text_tokens,
    leakage_probes,
    rename_candidate_labels,
    reorder_evidence,
    rewrite_presentation,
)
from .causal_generator import CAUSAL_TASK_CLASSES, DIFFICULTIES
from .causal_generator_v11 import (
    CAUSAL_GENERATOR_V11_VERSION,
    faithful_regime_probability,
    generate_causal_case_v11,
)
from .ledger import ExclusiveRunLedger
from .oracle import ExactOracle


_EXPECTED_COSTS = {
    "additive": {"easy": 3, "moderate": 9, "hard": 24},
    "relational": {"easy": 6, "moderate": 18, "hard": 48},
    "coordination_trap": {"easy": 4, "moderate": 12, "hard": 17},
}
_EXPECTED_PATH_COSTS = {
    "additive": {"easy": 3, "moderate": 9, "hard": 25},
    "relational": {"easy": 6, "moderate": 18, "hard": 49},
    "coordination_trap": {"easy": 4, "moderate": 12, "hard": 18},
}
_EXPECTED_BUDGETS = {
    "additive": {"easy": 5, "moderate": 12, "hard": 29},
    "relational": {"easy": 8, "moderate": 21, "hard": 53},
    "coordination_trap": {"easy": 6, "moderate": 15, "hard": 22},
}


@dataclass(frozen=True)
class CausalAuditV11Summary:
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
    operating_ranges: dict[str, dict[str, float]]
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


def _posterior_close(
    left: Mapping[str, float], right: Mapping[str, float], *, tolerance: float = 1e-12
) -> bool:
    return set(left) == set(right) and all(
        abs(left[key] - right[key]) <= tolerance for key in left
    )


def causal_v11_property_checks(first_seed: int) -> dict[str, bool]:
    checks = {
        "candidate_renaming_oracle_invariant": True,
        "evidence_order_oracle_invariant": True,
        "wording_oracle_invariant": True,
        "posterior_ceiling_ordered": True,
        "scarce_budget_above_sufficient_cost": True,
        "hard_adaptive_choice_gate": True,
    }
    abstract_labels = tuple(f"candidate_{index}" for index in range(5))
    for task_class in CAUSAL_TASK_CLASSES:
        ceilings: list[float] = []
        for difficulty in DIFFICULTIES:
            case = generate_causal_case_v11(first_seed, task_class, difficulty)
            task = case.causal_task
            evidence_ids = tuple(item.evidence_id for item in task.evidence)
            original_posterior = ExactOracle(task).observed_posterior(evidence_ids)
            ceilings.append(original_posterior[task.correct_candidate])

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

            reordered = reorder_evidence(task, tuple(reversed(range(len(task.evidence)))))
            checks["evidence_order_oracle_invariant"] &= _posterior_close(
                original_posterior,
                ExactOracle(reordered).observed_posterior(evidence_ids),
            )

            rewritten = rewrite_presentation(task)
            checks["wording_oracle_invariant"] &= _posterior_close(
                original_posterior,
                ExactOracle(rewritten).observed_posterior(evidence_ids),
            )
            checks["scarce_budget_above_sufficient_cost"] &= (
                case.metrics.minimum_sufficient_cost < case.evidence_budget
                < sum(item.cost for item in task.evidence)
            )
            if difficulty == "hard":
                checks["hard_adaptive_choice_gate"] &= bool(
                    case.adaptive_branch
                    and adaptive_choice_metrics(
                        case.causal_task, case.adaptive_branch
                    ).passed
                )
        checks["posterior_ceiling_ordered"] &= ceilings[0] > ceilings[1] > ceilings[2]
    return checks


def _audit_one(arguments: tuple[int, str, str]) -> dict[str, object]:
    seed, task_class, difficulty = arguments
    identity = {"seed": seed, "task_class": task_class, "difficulty": difficulty}
    try:
        case = generate_causal_case_v11(seed, task_class, difficulty)
    except Exception as exc:
        reason = str(exc).split(":", 1)[0] or type(exc).__name__
        return {
            **identity,
            "accepted": False,
            "rejection_reason": reason,
            "rejection_detail": f"{type(exc).__name__}: {exc}",
        }

    task = case.causal_task
    public = case.task.public()
    adaptive = (
        adaptive_choice_metrics(task, case.adaptive_branch)
        if case.adaptive_branch
        else None
    )
    return {
        **identity,
        "accepted": True,
        "rejection_reason": None,
        "causal_fingerprint": task.fingerprint(),
        "public_fingerprint": _canonical_hash(public),
        "correct_label": task.correct_candidate,
        "correct_position": task.candidates.index(task.correct_candidate),
        "metrics": case.metrics.mapping(),
        "evidence_budget": case.evidence_budget,
        "sufficiency_threshold": case.sufficiency_threshold,
        "faithful_regime_probability": case.faithful_regime_probability,
        "planned_path_cost": sum(case.minimum_path_costs),
        "adaptive_metrics": adaptive.mapping() if adaptive else None,
        "adaptive_gain_bits": adaptive.adaptive_gain_bits if adaptive else None,
        "metadata_tokens": _metadata_tokens(public),
        "text_tokens": _text_tokens(public),
        "metadata_probe_fingerprint": _canonical_hash(_metadata_tokens(public)),
        "text_probe_fingerprint": _canonical_hash(_text_tokens(public)),
    }


def _ranges(
    records: Iterable[dict[str, object]], keys: Sequence[str], *, nested: str | None = None
) -> dict[str, dict[str, float]]:
    values: dict[str, list[float]] = defaultdict(list)
    for record in records:
        if not record.get("accepted"):
            continue
        source = dict(record[nested]) if nested else record
        for key in keys:
            value = source.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                values[key].append(float(value))
    return {
        key: {"minimum": min(items), "maximum": max(items)}
        for key, items in sorted(values.items())
    }


def audit_causal_generator_v11(
    *,
    first_seed: int,
    seeds_per_cell: int,
    ledger_path: str | Path,
    workers: int = 1,
    probe_threshold: float = 0.40,
) -> CausalAuditV11Summary:
    if seeds_per_cell <= 0:
        raise ValueError("CAUSAL_V11_AUDIT_SEED_COUNT_INVALID")
    if workers <= 0:
        raise ValueError("CAUSAL_V11_AUDIT_WORKER_COUNT_INVALID")
    path = Path(ledger_path)
    if path.exists():
        raise FileExistsError(f"CAUSAL_V11_AUDIT_LEDGER_EXISTS: {path}")

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
        task_class = str(record["task_class"])
        difficulty = str(record["difficulty"])
        metrics = dict(record["metrics"])
        actual_cost = int(metrics["minimum_sufficient_cost"])
        allowed_costs = {_EXPECTED_COSTS[task_class][difficulty]}
        if difficulty == "hard":
            allowed_costs.add(_EXPECTED_PATH_COSTS[task_class][difficulty])
        if actual_cost not in allowed_costs:
            failures.append(f"CAUSAL_V11_COST_BAND_INVALID:{cell}:{record['seed']}")
        if int(record["planned_path_cost"]) != _EXPECTED_PATH_COSTS[task_class][difficulty]:
            failures.append(f"CAUSAL_V11_PATH_COST_INVALID:{cell}:{record['seed']}")
        if int(record["evidence_budget"]) != _EXPECTED_BUDGETS[task_class][difficulty]:
            failures.append(f"CAUSAL_V11_BUDGET_INVALID:{cell}:{record['seed']}")
        if abs(
            float(record["faithful_regime_probability"])
            - faithful_regime_probability(difficulty)
        ) > 1e-12:
            failures.append(f"CAUSAL_V11_POSTERIOR_INVALID:{cell}:{record['seed']}")
        adaptive = record.get("adaptive_metrics")
        if difficulty == "hard" and not (isinstance(adaptive, dict) and adaptive.get("passed")):
            failures.append(f"CAUSAL_V11_ADAPTIVE_GATE_INVALID:{cell}:{record['seed']}")
        if difficulty != "hard" and adaptive is not None:
            failures.append(f"CAUSAL_V11_ADAPTIVE_GATE_UNEXPECTED:{cell}:{record['seed']}")

    attempted = len(arguments)
    if len(accepted) != attempted:
        failures.append("CAUSAL_V11_AUDIT_REJECTIONS_PRESENT")
    if len(causal_fingerprints) != len(accepted):
        failures.append("CAUSAL_V11_CAUSAL_FINGERPRINT_COLLISION")
    if len(public_fingerprints) != len(accepted):
        failures.append("CAUSAL_V11_PUBLIC_FINGERPRINT_COLLISION")
    if cells and any(cells[cell] != seeds_per_cell for cell in cells):
        failures.append("CAUSAL_V11_CELL_BALANCE_INVALID")
    if labels and (len(labels) != 5 or max(labels.values()) != min(labels.values())):
        failures.append("CAUSAL_V11_CORRECT_LABEL_BALANCE_INVALID")
    if positions and (
        set(positions) != set(range(5)) or max(positions.values()) != min(positions.values())
    ):
        failures.append("CAUSAL_V11_CORRECT_POSITION_BALANCE_INVALID")

    probes = leakage_probes(records, threshold=probe_threshold)
    if len(probes) != 4:
        failures.append("CAUSAL_V11_LEAKAGE_PROBES_INCOMPLETE")
    failures.extend(
        f"CAUSAL_V11_LEAKAGE_PROBE_FAILED:{probe.feature_set}:{probe.target}"
        for probe in probes
        if not probe.passed
    )
    property_checks = causal_v11_property_checks(first_seed)
    failures.extend(
        f"CAUSAL_V11_PROPERTY_CHECK_FAILED:{name}"
        for name, passed in property_checks.items()
        if not passed
    )

    with ExclusiveRunLedger(path) as ledger:
        ledger.append(
            {
                "kind": "causal_v11_audit_started",
                "generator_version": CAUSAL_GENERATOR_V11_VERSION,
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
            payload["kind"] = "causal_v11_candidate_audited"
            ledger.append(payload)
        ledger.append(
            {
                "kind": "causal_v11_audit_completed",
                "accepted": len(accepted),
                "rejected": attempted - len(accepted),
                "failures": sorted(set(failures)),
                "leakage_probes": [probe.mapping() for probe in probes],
                "property_checks": property_checks,
                "expected_ledger_records": attempted + 2,
            }
        )

    verification = verify_ledger(path)
    metric_keys = tuple(next(iter(accepted))["metrics"].keys()) if accepted else ()
    return CausalAuditV11Summary(
        generator_version=CAUSAL_GENERATOR_V11_VERSION,
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
        metric_ranges=_ranges(records, metric_keys, nested="metrics"),
        operating_ranges=_ranges(
            records,
            (
                "evidence_budget",
                "planned_path_cost",
                "sufficiency_threshold",
                "faithful_regime_probability",
                "adaptive_gain_bits",
            ),
        ),
        leakage_probes=probes,
        property_checks=property_checks,
        failures=tuple(sorted(set(failures))),
        ledger_records=int(verification["records"]),
        ledger_head=str(verification["head"]),
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the offline causal-1.1 audit")
    parser.add_argument("--first-seed", type=int, default=500)
    parser.add_argument("--seeds-per-cell", type=int, default=25)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--probe-threshold", type=float, default=0.40)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    summary = audit_causal_generator_v11(
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
