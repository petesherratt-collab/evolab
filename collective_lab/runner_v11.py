from __future__ import annotations

import json
from typing import Any

from .core import FaultTask, Report, score_report
from .openrouter import Completion
from .protocol_v11 import (
    ComputePlan,
    EvidenceAllocation,
    collective_revision_order,
    evidence_allocation,
)
from .runner import ConditionResult, Harness, ROLES, _usage_totals


class HarnessV11(Harness):
    """Prospective causal-1.1 harness with conserved evidence and token reserves."""

    def _synthesize_v11(
        self,
        task: FaultTask,
        reports: list[Report | None],
        *,
        condition: str,
        budget: int,
    ) -> tuple[Report | None, set[str], int, list[Completion], list[str]]:
        return self._agent_episode(
            task,
            role=(
                "You are the synthesizer. Reconcile the supplied reports and use "
                "the reserve only to resolve decisive uncertainty."
            ),
            budget=budget,
            condition=condition,
            agent_id="synthesizer",
            extra_context=json.dumps(
                [report.mapping() if report else None for report in reports],
                sort_keys=True,
            ),
        )

    @staticmethod
    def _vote_report(
        task: FaultTask, reports: list[Report | None]
    ) -> Report:
        uniform = 1.0 / len(task.candidates)
        probabilities = {
            candidate: sum(
                report.probabilities[candidate] if report else uniform
                for report in reports
            )
            / len(reports)
            for candidate in task.candidates
        }
        diagnosis = max(
            task.candidates,
            key=lambda item: (probabilities[item], -task.candidates.index(item)),
        )
        valid = [report for report in reports if report]
        return Report(
            diagnosis=diagnosis,
            probabilities=probabilities,
            cited_evidence=tuple(
                sorted({item for report in valid for item in report.cited_evidence})
            ),
            rationale=(
                "Deterministic arithmetic mean; failed constituents contribute "
                "a preregistered uniform distribution."
            ),
            strongest_alternative=max(
                (item for item in task.candidates if item != diagnosis),
                key=probabilities.get,
            ),
            recommended_verification=(),
        )

    def run_condition(
        self,
        task: FaultTask,
        condition: str,
        *,
        evidence_budget: int,
        minimum_path_costs: tuple[int, ...],
        target_tokens: int = 25_000,
        tolerance: float = 0.10,
        compute_plan: ComputePlan | None = None,
    ) -> ConditionResult:
        plan = compute_plan or ComputePlan(
            target_tokens=target_tokens,
            tolerance=tolerance,
        )
        if plan.target_tokens != target_tokens or plan.tolerance != tolerance:
            raise ValueError("CAUSAL_V11_COMPUTE_PLAN_MISMATCH")
        allocation = evidence_allocation(
            condition,
            evidence_budget,
            task_id=task.task_id,
            minimum_path_costs=minimum_path_costs,
        )
        revision_order = (
            collective_revision_order(task.task_id)
            if condition == "communicating_collective"
            else ()
        )
        self.ledger.append(
            {
                "kind": "causal_v11_condition_plan",
                "task_id": task.task_id,
                "condition": condition,
                "evidence_allocation": allocation.mapping(),
                "compute_plan": plan.mapping(),
                "collective_revision_order": list(revision_order),
            }
        )

        reports: list[Report | None] = []
        acquired_sets: list[set[str]] = []
        total_spent = 0
        completions: list[Completion] = []
        errors: list[str] = []

        if condition == "single_agent":
            report, acquired, spent, calls, episode_errors = self._agent_episode(
                task,
                role=(
                    "Act as a strong generalist. Seek both supporting and "
                    "disconfirming evidence before answering."
                ),
                budget=allocation.investigator_budgets[0],
                condition=condition,
                agent_id="single",
            )
            reports = [report]
            acquired_sets = [acquired]
            total_spent = spent
            completions.extend(calls)
            errors.extend(episode_errors)
            final_report = report
            review_index = 0
            while (
                _usage_totals(completions).get("total_tokens", 0.0) < plan.lower_bound
                and review_index < 14
                and plan.permits_private_review(
                    _usage_totals(completions).get("total_tokens", 0.0)
                )
            ):
                review_index += 1
                final_report, completion, review_errors = self._private_review(
                    task,
                    final_report,
                    acquired,
                    condition=condition,
                    agent_id="single",
                    review_index=review_index,
                )
                completions.append(completion)
                errors.extend(review_errors)
            valid_constituents = int(final_report is not None)
            failed_constituents = int(final_report is None)
        else:
            for index, (role, budget) in enumerate(
                zip(ROLES, allocation.investigator_budgets, strict=True)
            ):
                report, acquired, spent, calls, episode_errors = self._agent_episode(
                    task,
                    role=role,
                    budget=budget,
                    condition=condition,
                    agent_id=f"investigator-{index + 1}",
                )
                reports.append(report)
                acquired_sets.append(acquired)
                total_spent += spent
                completions.extend(calls)
                errors.extend(episode_errors)

            if condition == "independent_vote":
                review_index = 0
                while (
                    _usage_totals(completions).get("total_tokens", 0.0)
                    < plan.lower_bound
                    and review_index < 14
                    and plan.permits_private_review(
                        _usage_totals(completions).get("total_tokens", 0.0)
                    )
                ):
                    agent_index = review_index % len(reports)
                    round_index = review_index // len(reports) + 1
                    reports[agent_index], completion, review_errors = self._private_review(
                        task,
                        reports[agent_index],
                        acquired_sets[agent_index],
                        condition=condition,
                        agent_id=f"investigator-{agent_index + 1}",
                        review_index=round_index,
                    )
                    completions.append(completion)
                    errors.extend(review_errors)
                    review_index += 1
                final_report = self._vote_report(task, reports)
            elif condition in {
                "independent_synthesizer",
                "communicating_collective",
            }:
                synthesis_reports = reports
                if condition == "communicating_collective":
                    revised = list(reports)
                    revisions_used = 0
                    for agent_index in revision_order:
                        used_tokens = _usage_totals(completions).get(
                            "total_tokens", 0.0
                        )
                        if revisions_used >= plan.collective_revision_limit:
                            break
                        if not plan.permits_collective_revision(used_tokens):
                            break
                        revision, completion, revision_errors = self._revise(
                            task,
                            reports[agent_index],
                            [
                                report
                                for peer_index, report in enumerate(reports)
                                if peer_index != agent_index
                            ],
                            agent_id=f"investigator-{agent_index + 1}",
                        )
                        revised[agent_index] = revision or reports[agent_index]
                        completions.append(completion)
                        errors.extend(revision_errors)
                        revisions_used += 1
                    synthesis_reports = revised

                (
                    final_report,
                    reserve_acquired,
                    reserve_spent,
                    calls,
                    synthesis_errors,
                ) = self._synthesize_v11(
                    task,
                    synthesis_reports,
                    condition=condition,
                    budget=allocation.synthesis_budget,
                )
                acquired_sets.append(reserve_acquired)
                total_spent += reserve_spent
                completions.extend(calls)
                errors.extend(synthesis_errors)

                review_index = 0
                acquired_for_synthesis = set().union(*acquired_sets)
                while (
                    _usage_totals(completions).get("total_tokens", 0.0)
                    < plan.lower_bound
                    and review_index < 10
                    and plan.permits_private_review(
                        _usage_totals(completions).get("total_tokens", 0.0)
                    )
                ):
                    review_index += 1
                    final_report, completion, review_errors = self._private_review(
                        task,
                        final_report,
                        acquired_for_synthesis,
                        condition=condition,
                        agent_id="synthesizer",
                        review_index=review_index,
                    )
                    completions.append(completion)
                    errors.extend(review_errors)
            else:
                raise ValueError(f"CAUSAL_V11_CONDITION_UNKNOWN: {condition}")

            valid_constituents = sum(report is not None for report in reports)
            failed_constituents = len(reports) - valid_constituents

        acquired_union = set().union(*acquired_sets) if acquired_sets else set()
        score = score_report(task, final_report, acquired_union)
        result = ConditionResult(
            condition=condition,
            report=final_report,
            score=score,
            acquired_evidence=tuple(sorted(acquired_union)),
            evidence_spent=total_spent,
            api_requests=len(completions),
            usage=_usage_totals(completions),
            errors=tuple(errors),
            valid_constituents=valid_constituents,
            failed_constituents=failed_constituents,
        )
        if total_spent > allocation.total_budget:
            raise ValueError("CAUSAL_V11_EVIDENCE_BUDGET_EXCEEDED")
        self.ledger.append(
            {
                "kind": "condition_complete",
                "task_id": task.task_id,
                "result": result.mapping(),
            }
        )
        return result


def v11_condition_plan(
    task: FaultTask,
    condition: str,
    *,
    evidence_budget: int,
    minimum_path_costs: tuple[int, ...],
    compute_plan: ComputePlan = ComputePlan(),
) -> dict[str, Any]:
    allocation: EvidenceAllocation = evidence_allocation(
        condition,
        evidence_budget,
        task_id=task.task_id,
        minimum_path_costs=minimum_path_costs,
    )
    return {
        "task_id": task.task_id,
        "condition": condition,
        "evidence_allocation": allocation.mapping(),
        "compute_plan": compute_plan.mapping(),
        "collective_revision_order": (
            list(collective_revision_order(task.task_id))
            if condition == "communicating_collective"
            else []
        ),
    }
