from __future__ import annotations

import json
from typing import Any

from .core import FaultTask, Report
from .openrouter import Completion
from .protocol_v13 import ComputePlanV13, PERSPECTIVE_LENSES, lens_charter
from .runner_v12 import (
    AcquisitionProposal,
    ComputeBudgetExhausted,
    HarnessV12,
    SharedEvidencePool,
    v12_condition_plan,
)


def _render_lenses(lenses) -> str:
    return json.dumps([lens.mapping() for lens in lenses], sort_keys=True)


class HarnessV13(HarnessV12):
    """Causal-1.3 harness distributing one public charter across roles."""

    def _complete(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        context: dict[str, Any],
    ) -> Completion:
        try:
            return super()._complete(
                messages,
                tools=tools,
                response_format=response_format,
                context=context,
            )
        except ComputeBudgetExhausted as exc:
            if tools is None or str(exc) != "CAUSAL_V12_COMPUTE_BUDGET_EXHAUSTED":
                raise
            previous_reserve = self._reserve_after
            self._reserve_after = 0
            self.ledger.append(
                {
                    "kind": "causal_v13_terminal_report_fallback",
                    "context": context,
                    "reason": str(exc),
                    "released_reserve": previous_reserve,
                }
            )
            try:
                return super()._complete(
                    messages,
                    tools=None,
                    response_format=response_format,
                    context={**context, "terminal_report_fallback": True},
                )
            finally:
                self._reserve_after = previous_reserve

    def _agent_lenses(self, condition: str, agent_id: str):
        if condition == "single_agent":
            return PERSPECTIVE_LENSES
        if agent_id.startswith("investigator-"):
            try:
                index = int(agent_id.rsplit("-", 1)[1]) - 1
            except (ValueError, IndexError):
                index = 0
            return (PERSPECTIVE_LENSES[index % len(PERSPECTIVE_LENSES)],)
        return PERSPECTIVE_LENSES

    def _agent_episode(
        self,
        task: FaultTask,
        *,
        role: str,
        budget: int,
        condition: str,
        agent_id: str,
        extra_context: str = "",
    ):
        lenses = self._agent_lenses(condition, agent_id)
        charter = (
            "Public perspective charter assigned to this investigator: "
            + _render_lenses(lenses)
        )
        combined = f"{extra_context}\n{charter}" if extra_context else charter
        return super()._agent_episode(
            task,
            role=role,
            budget=budget,
            condition=condition,
            agent_id=agent_id,
            extra_context=combined,
        )

    def _shared_episode(
        self,
        task: FaultTask,
        *,
        pool: SharedEvidencePool,
        stage_ceiling: int,
        role: str,
        agent_id: str,
        extra_context: str = "",
    ):
        charter = "Complete public perspective charter: " + json.dumps(
            lens_charter(), sort_keys=True
        )
        combined = f"{extra_context}\n{charter}" if extra_context else charter
        return super()._shared_episode(
            task,
            pool=pool,
            stage_ceiling=stage_ceiling,
            role=role,
            agent_id=agent_id,
            extra_context=combined,
        )

    def _propose_acquisition(
        self,
        task: FaultTask,
        *,
        role: str,
        agent_id: str,
        pool: SharedEvidencePool,
        scout_report: Report | None,
    ) -> tuple[AcquisitionProposal | None, Completion, list[str]]:
        try:
            index = int(agent_id.rsplit("-", 1)[1]) - 1
        except (ValueError, IndexError):
            index = 0
        lens = PERSPECTIVE_LENSES[index % len(PERSPECTIVE_LENSES)]
        return super()._propose_acquisition(
            task,
            role=(
                role
                + " Your assigned public perspective lens is: "
                + json.dumps(lens.mapping(), sort_keys=True)
            ),
            agent_id=agent_id,
            pool=pool,
            scout_report=scout_report,
        )


def v13_condition_plan(
    task: FaultTask,
    condition: str,
    *,
    evidence_budget: int,
    minimum_path_costs: tuple[int, ...],
    compute_plan: ComputePlanV13 = ComputePlanV13(),
) -> dict[str, Any]:
    plan = v12_condition_plan(
        task,
        condition,
        evidence_budget=evidence_budget,
        minimum_path_costs=minimum_path_costs,
        compute_plan=compute_plan,
    )
    return {
        **plan,
        "protocol_version": "causal-1.3-dev",
        "public_perspective_charter": list(lens_charter()),
    }
