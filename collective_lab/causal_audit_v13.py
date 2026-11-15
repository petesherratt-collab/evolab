from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from evolutionary_lab.evidence import verify_ledger

from .causal_generator import CAUSAL_TASK_CLASSES, DIFFICULTIES
from .causal_generator_v13 import (
    CAUSAL_GENERATOR_V13_VERSION,
    faithful_regime_probability_v13,
    generate_causal_case_v13,
)
from .ledger import ExclusiveRunLedger
from .oracle import ExactOracle
from .protocol_v13 import (
    CAUSAL_V13_PROTOCOL_VERSION,
    PERSPECTIVE_LENSES,
    lens_charter,
)


_BANNED_CATALOG_LEAKAGE = (
    "signature",
    "cached",
    "stale",
    "polarity",
    "calibration",
    "xor",
    "reference phase",
    "trace member",
    "correlated repeat",
    "noisy repeat",
    "physical measurement",
    "misleading",
)


@dataclass(frozen=True)
class AuditSummaryV13:
    protocol_version: str
    generator_version: str
    seeds: tuple[int, ...]
    attempted: int
    accepted: int
    rejected: int
    cells_attempted: int
    cells_passed: int
    class_structure_checks: dict[str, bool]
    difficulty_band_checks: dict[str, bool]
    perspective_checks: dict[str, bool]
    failures: tuple[str, ...]
    ledger_records: int
    ledger_head: str

    @property
    def passed(self) -> bool:
        return (
            self.attempted == self.accepted
            and self.rejected == 0
            and self.cells_attempted == self.cells_passed
            and all(self.class_structure_checks.values())
            and all(self.difficulty_band_checks.values())
            and all(self.perspective_checks.values())
            and not self.failures
        )

    def mapping(self) -> dict[str, object]:
        return {**asdict(self), "passed": self.passed}


def _candidate_checks(case) -> dict[str, bool]:
    task = case.causal_task
    oracle = ExactOracle(task)
    evidence = {item.evidence_id: item for item in task.evidence}
    path_cost = sum(case.minimum_path_costs)
    catalog_cost = sum(item.cost for item in task.evidence)
    checks = {
        "generator_tagged": task.generator_version == CAUSAL_GENERATOR_V13_VERSION,
        "posterior_ceiling_exact": abs(
            case.metrics.observed_full_posterior
            - faithful_regime_probability_v13(task.intended_difficulty)
        )
        < 1e-12,
        "threshold_reachable": (
            case.metrics.observed_full_posterior > case.sufficiency_threshold
        ),
        "planned_route_sufficient": case.metrics.minimum_sufficient_cost <= path_cost,
        "verification_reserve_positive": case.evidence_budget > path_cost,
        "budget_scarce": case.evidence_budget < catalog_cost,
        "minimum_three_clues": case.metrics.minimum_sufficient_clues >= 3,
    }
    if task.intended_difficulty in {"moderate", "hard"}:
        lane_ids = {
            item
            for lane in case.acquisition_lanes
            for item in (lane.active_option, lane.alternative_option)
        }
        descriptions = " ".join(item.description.lower() for item in task.evidence)
        checks.update(
            {
                "router_present": case.topology_router is not None,
                "router_zero_information": (
                    oracle.information_gain((case.topology_router,)) < 1e-12
                    if case.topology_router
                    else False
                ),
                "lane_count_matches_route": (
                    len(case.acquisition_lanes) == len(case.core_evidence) - 1
                ),
                "lane_options_unique": len(lane_ids)
                == 2 * len(case.acquisition_lanes),
                "lane_costs_matched": all(
                    evidence[lane.active_option].cost
                    == evidence[lane.alternative_option].cost
                    for lane in case.acquisition_lanes
                ),
                "lane_regions_matched": all(
                    evidence[lane.active_option].region
                    == evidence[lane.alternative_option].region
                    for lane in case.acquisition_lanes
                ),
                "at_least_three_regions": len(
                    {lane.region for lane in case.acquisition_lanes}
                )
                >= 3,
                "catalog_role_leakage_removed": not any(
                    term in descriptions for term in _BANNED_CATALOG_LEAKAGE
                ),
            }
        )
    else:
        checks.update(
            {
                "easy_has_no_router": case.topology_router is None,
                "easy_has_no_ambiguous_lanes": not case.acquisition_lanes,
            }
        )
    if task.task_class == "additive":
        checks["additive_has_marginal_gain"] = (
            case.metrics.maximum_single_information_gain > 0
        )
    elif task.task_class == "relational":
        checks["relational_has_pair_synergy"] = (
            case.metrics.maximum_pair_synergy > 0
        )
    else:
        checks["trap_misleads_before_verification"] = (
            case.metrics.cheap_distractor_posterior
            > case.metrics.cheap_correct_posterior
        )
    return checks


def _cross_checks(cases: dict[tuple[int, str, str], Any]) -> tuple[
    dict[str, bool], dict[str, bool]
]:
    class_checks: dict[str, bool] = {}
    band_checks: dict[str, bool] = {}
    seeds = sorted({key[0] for key in cases})
    for seed in seeds:
        for difficulty in DIFFICULTIES:
            selected = [cases[(seed, task_class, difficulty)] for task_class in CAUSAL_TASK_CLASSES]
            class_checks[f"seed_{seed}_{difficulty}_distinct_fingerprints"] = (
                len({case.causal_task.fingerprint() for case in selected}) == 3
            )
            class_checks[f"seed_{seed}_{difficulty}_distinct_clue_signatures"] = (
                len(
                    {
                        (
                            case.metrics.minimum_sufficient_clues,
                            round(case.metrics.maximum_single_information_gain, 9),
                            round(case.metrics.maximum_pair_synergy, 9),
                        )
                        for case in selected
                    }
                )
                >= 2
            )
        for task_class in CAUSAL_TASK_CLASSES:
            easy, moderate, hard = (
                cases[(seed, task_class, difficulty)] for difficulty in DIFFICULTIES
            )
            band_checks[f"seed_{seed}_{task_class}_path_cost_ordered"] = (
                sum(easy.minimum_path_costs)
                < sum(moderate.minimum_path_costs)
                < sum(hard.minimum_path_costs)
            )
            band_checks[f"seed_{seed}_{task_class}_posterior_ordered"] = (
                easy.faithful_regime_probability
                > moderate.faithful_regime_probability
                > hard.faithful_regime_probability
            )
            band_checks[f"seed_{seed}_{task_class}_reserve_tightens"] = (
                easy.evidence_budget - sum(easy.minimum_path_costs) == 2
                and moderate.evidence_budget - sum(moderate.minimum_path_costs) == 1
                and hard.evidence_budget - sum(hard.minimum_path_costs) == 2
            )
    return class_checks, band_checks


def audit_v13(
    *,
    seeds: tuple[int, ...],
    output_ledger: str | Path,
    summary_output: str | Path,
) -> AuditSummaryV13:
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("CAUSAL_V13_AUDIT_SEEDS_INVALID")
    output = Path(output_ledger).resolve()
    summary_path = Path(summary_output).resolve()
    failures: list[str] = []
    cases: dict[tuple[int, str, str], Any] = {}
    accepted = 0
    rejected = 0

    with ExclusiveRunLedger(output) as ledger:
        ledger.append(
            {
                "kind": "causal_v13_audit_started",
                "protocol_version": CAUSAL_V13_PROTOCOL_VERSION,
                "generator_version": CAUSAL_GENERATOR_V13_VERSION,
                "seeds": list(seeds),
            }
        )
        for seed in seeds:
            for task_class in CAUSAL_TASK_CLASSES:
                for difficulty in DIFFICULTIES:
                    identity = f"{seed}:{task_class}:{difficulty}"
                    try:
                        case = generate_causal_case_v13(seed, task_class, difficulty)
                        checks = _candidate_checks(case)
                        candidate_accepted = all(checks.values())
                        reason = None
                        cases[(seed, task_class, difficulty)] = case
                    except Exception as exc:
                        checks = {}
                        candidate_accepted = False
                        reason = f"{type(exc).__name__}: {exc}"
                    if candidate_accepted:
                        accepted += 1
                    else:
                        rejected += 1
                        failures.append(f"{identity}: {reason or checks}")
                    ledger.append(
                        {
                            "kind": "causal_v13_candidate_audited",
                            "identity": identity,
                            "seed": seed,
                            "task_class": task_class,
                            "difficulty": difficulty,
                            "accepted": candidate_accepted,
                            "checks": checks,
                            "reason": reason,
                        }
                    )

        class_checks, band_checks = _cross_checks(cases) if not rejected else ({}, {})
        perspective_checks = {
            "four_unique_lenses": len(PERSPECTIVE_LENSES) == 4
            and len({lens.lens_id for lens in PERSPECTIVE_LENSES}) == 4,
            "charter_is_public_and_complete": len(lens_charter()) == 4,
            "no_task_private_metadata_in_charter": all(
                set(item) == {"lens_id", "title", "instruction"}
                for item in lens_charter()
            ),
        }
        ledger.append(
            {
                "kind": "causal_v13_audit_completed",
                "accepted": accepted,
                "rejected": rejected,
                "class_structure_checks": class_checks,
                "difficulty_band_checks": band_checks,
                "perspective_checks": perspective_checks,
                "failures": failures,
            }
        )

    verification = verify_ledger(output)
    summary = AuditSummaryV13(
        protocol_version=CAUSAL_V13_PROTOCOL_VERSION,
        generator_version=CAUSAL_GENERATOR_V13_VERSION,
        seeds=seeds,
        attempted=len(seeds) * len(CAUSAL_TASK_CLASSES) * len(DIFFICULTIES),
        accepted=accepted,
        rejected=rejected,
        cells_attempted=len(CAUSAL_TASK_CLASSES) * len(DIFFICULTIES),
        cells_passed=(
            len(CAUSAL_TASK_CLASSES) * len(DIFFICULTIES) if not rejected else 0
        ),
        class_structure_checks=class_checks,
        difficulty_band_checks=band_checks,
        perspective_checks=perspective_checks,
        failures=tuple(failures),
        ledger_records=int(verification["records"]),
        ledger_head=str(verification["head"]),
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary.mapping(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Audit causal-1.3 mechanics")
    parser.add_argument("--first-seed", type=int, default=700)
    parser.add_argument("--seed-count", type=int, default=5)
    parser.add_argument("--output-ledger", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()
    summary = audit_v13(
        seeds=tuple(range(args.first_seed, args.first_seed + args.seed_count)),
        output_ledger=args.output_ledger,
        summary_output=args.summary_output,
    )
    print(json.dumps(summary.mapping(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
