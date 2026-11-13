from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from evolutionary_lab.evidence import verify_ledger

from .causal_generator import CAUSAL_TASK_CLASSES, DIFFICULTIES
from .causal_generator_v11 import (
    CAUSAL_GENERATOR_V11_VERSION,
    generate_causal_case_v11,
)
from .ledger import ExclusiveRunLedger
from .protocol_v12 import (
    CAUSAL_V12_PROTOCOL_VERSION,
    ComputePlanV12,
    staged_evidence_allocation,
)


@dataclass(frozen=True)
class PolicyAuditSummaryV12:
    protocol_version: str
    generator_lineage: str
    source_audit_path: str
    source_audit_sha256: str
    source_audit_head: str
    attempted: int
    accepted: int
    rejected: int
    hard_adaptive_source_passes: int
    representative_cells_passed: int
    representative_cells_attempted: int
    compute_gate_checks: dict[str, bool]
    failures: tuple[str, ...]
    ledger_head: str
    ledger_records: int

    @property
    def passed(self) -> bool:
        return (
            self.accepted == self.attempted
            and self.rejected == 0
            and self.hard_adaptive_source_passes == 75
            and self.representative_cells_passed
            == self.representative_cells_attempted
            and all(self.compute_gate_checks.values())
            and not self.failures
        )

    def mapping(self) -> dict[str, object]:
        return {**asdict(self), "passed": self.passed}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _payloads(path: Path) -> list[dict[str, Any]]:
    verification = verify_ledger(path)
    if not verification["valid"]:
        raise ValueError("CAUSAL_V12_SOURCE_AUDIT_CHAIN_INVALID")
    return [
        json.loads(line)["payload"]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _compute_gate_checks() -> dict[str, bool]:
    plan = ComputePlanV12()
    short_prompt = [{"role": "user", "content": "diagnose"}]
    estimate = plan.estimate_prompt_tokens(short_prompt)
    initial_cap = plan.completion_cap(
        used_tokens=0,
        estimated_prompt_tokens=estimate,
        reserve_after=plan.reserve_for_mandatory_episodes(5),
        requested_max=1_400,
    )
    exhausted_cap = plan.completion_cap(
        used_tokens=plan.upper_bound - plan.minimum_completion_tokens,
        estimated_prompt_tokens=estimate,
        reserve_after=0,
        requested_max=1_400,
    )
    return {
        "upper_bound_is_frozen": plan.upper_bound == 27_500,
        "lower_bound_is_frozen": plan.lower_bound == 22_500,
        "initial_staged_call_fits_with_five_reserves": initial_cap
        >= plan.minimum_completion_tokens,
        "completion_cap_never_exceeds_frozen_maximum": initial_cap
        <= plan.max_completion_tokens,
        "near_ceiling_call_is_rejected": exhausted_cap == 0,
        "optional_call_respects_ceiling": not plan.permits_optional_call(
            plan.upper_bound - plan.optional_call_reserve_tokens + 1
        ),
        "request_count_is_bounded": plan.max_condition_requests == 18,
    }


def _representative_contract_checks(first_seed: int) -> tuple[int, int, list[str]]:
    attempted = 0
    passed = 0
    failures: list[str] = []
    for task_class in CAUSAL_TASK_CLASSES:
        for difficulty in DIFFICULTIES:
            attempted += 1
            identity = f"{task_class}:{difficulty}"
            try:
                case = generate_causal_case_v11(first_seed, task_class, difficulty)
                allocation = staged_evidence_allocation(
                    case.evidence_budget,
                    minimum_path_costs=case.minimum_path_costs,
                )
                path_cost = sum(case.minimum_path_costs)
                checks = [
                    allocation.coordinator_guaranteed_budget == path_cost,
                    allocation.scout_ceiling + path_cost == case.evidence_budget,
                    allocation.coordinator_budget_after(allocation.scout_ceiling)
                    == path_cost,
                ]
                if case.adaptive_branch is not None:
                    evidence = case.task.evidence_map()
                    router_cost = evidence[
                        case.adaptive_branch.router_evidence
                    ].cost
                    active_probe = case.adaptive_branch.branch_evidence[
                        case.adaptive_branch.true_branch
                    ]
                    remaining_route = sum(
                        evidence[evidence_id].cost
                        for evidence_id in case.adaptive_branch.baseline_evidence
                    ) + evidence[active_probe].cost
                    checks.extend(
                        [
                            router_cost <= allocation.scout_ceiling,
                            case.evidence_budget - router_cost >= remaining_route,
                        ]
                    )
                if not all(checks):
                    raise ValueError("STAGED_CONTRACT_CHECK_FAILED")
                passed += 1
            except Exception as exc:
                failures.append(f"{identity}: {type(exc).__name__}: {exc}")
    return attempted, passed, failures


def audit_v12_policy(
    *,
    source_audit: str | Path,
    output_ledger: str | Path,
    summary_output: str | Path,
    representative_seed: int = 500,
) -> PolicyAuditSummaryV12:
    source_path = Path(source_audit).resolve()
    output_path = Path(output_ledger).resolve()
    summary_path = Path(summary_output).resolve()
    source_verification = verify_ledger(source_path)
    records = _payloads(source_path)
    candidates = [
        record
        for record in records
        if record.get("kind") == "causal_v11_candidate_audited"
    ]
    if len(candidates) != 225:
        raise ValueError("CAUSAL_V12_SOURCE_AUDIT_SIZE_INVALID")

    accepted = 0
    rejected = 0
    hard_adaptive_source_passes = 0
    failures: list[str] = []
    with ExclusiveRunLedger(output_path) as ledger:
        ledger.append(
            {
                "kind": "causal_v12_policy_audit_started",
                "protocol_version": CAUSAL_V12_PROTOCOL_VERSION,
                "generator_lineage": CAUSAL_GENERATOR_V11_VERSION,
                "source_audit": str(source_path),
                "source_audit_sha256": _sha256(source_path),
                "source_audit_head": source_verification["head"],
                "candidates": len(candidates),
            }
        )
        for record in candidates:
            identity = (
                f"{record['seed']}:{record['task_class']}:{record['difficulty']}"
            )
            path_cost = int(record["planned_path_cost"])
            evidence_budget = int(record["evidence_budget"])
            source_accepted = bool(record["accepted"])
            adaptive_passed = (
                record["difficulty"] != "hard"
                or bool(record.get("adaptive_metrics", {}).get("passed"))
            )
            try:
                allocation = staged_evidence_allocation(
                    evidence_budget,
                    minimum_path_costs=(path_cost,),
                )
                checks = {
                    "source_candidate_accepted": source_accepted,
                    "positive_scout_ceiling": allocation.scout_ceiling > 0,
                    "coordinator_route_guaranteed": (
                        allocation.coordinator_guaranteed_budget == path_cost
                    ),
                    "budget_conserved_after_full_scout": (
                        allocation.coordinator_budget_after(
                            allocation.scout_ceiling
                        )
                        == path_cost
                    ),
                    "hard_adaptive_source_passed": adaptive_passed,
                }
                candidate_accepted = all(checks.values())
                reason = None
            except Exception as exc:
                checks = {}
                candidate_accepted = False
                reason = f"{type(exc).__name__}: {exc}"
            if candidate_accepted:
                accepted += 1
            else:
                rejected += 1
                failures.append(f"{identity}: {reason or checks}")
            if record["difficulty"] == "hard" and adaptive_passed:
                hard_adaptive_source_passes += 1
            ledger.append(
                {
                    "kind": "causal_v12_policy_candidate_audited",
                    "identity": identity,
                    "task_class": record["task_class"],
                    "difficulty": record["difficulty"],
                    "evidence_budget": evidence_budget,
                    "planned_path_cost": path_cost,
                    "scout_ceiling": evidence_budget - path_cost,
                    "accepted": candidate_accepted,
                    "checks": checks,
                    "rejection_reason": reason,
                }
            )

        representative_attempted, representative_passed, representative_failures = (
            _representative_contract_checks(representative_seed)
        )
        failures.extend(representative_failures)
        compute_checks = _compute_gate_checks()
        ledger.append(
            {
                "kind": "causal_v12_policy_audit_completed",
                "accepted": accepted,
                "rejected": rejected,
                "hard_adaptive_source_passes": hard_adaptive_source_passes,
                "representative_cells_passed": representative_passed,
                "representative_cells_attempted": representative_attempted,
                "compute_gate_checks": compute_checks,
                "failures": failures,
            }
        )

    verification = verify_ledger(output_path)
    summary = PolicyAuditSummaryV12(
        protocol_version=CAUSAL_V12_PROTOCOL_VERSION,
        generator_lineage=CAUSAL_GENERATOR_V11_VERSION,
        source_audit_path=str(source_path),
        source_audit_sha256=_sha256(source_path),
        source_audit_head=str(source_verification["head"]),
        attempted=len(candidates),
        accepted=accepted,
        rejected=rejected,
        hard_adaptive_source_passes=hard_adaptive_source_passes,
        representative_cells_passed=representative_passed,
        representative_cells_attempted=representative_attempted,
        compute_gate_checks=compute_checks,
        failures=tuple(failures),
        ledger_head=str(verification["head"]),
        ledger_records=int(verification["records"]),
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary.mapping(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Audit the causal-1.2 policy")
    parser.add_argument("--source-audit", type=Path, required=True)
    parser.add_argument("--output-ledger", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--representative-seed", type=int, default=500)
    args = parser.parse_args()
    summary = audit_v12_policy(
        source_audit=args.source_audit,
        output_ledger=args.output_ledger,
        summary_output=args.summary_output,
        representative_seed=args.representative_seed,
    )
    print(json.dumps(summary.mapping(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
