from __future__ import annotations

import json

from .protocol_v14 import EVIDENCE_DISCIPLINE, ComputePlanV14
from .runner_v12 import ComputeBudgetExhausted, HarnessV12
from .runner_v13 import HarnessV13, v13_condition_plan


class HarnessV14(HarnessV13):
    """Prospective strategy revision; historical v13 behavior stays frozen."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._future_reserve = 0
        self._scout_report = None

    def run_condition(self, *args, **kwargs):
        self._scout_report = None
        self._future_reserve = 0
        return super().run_condition(*args, **kwargs)

    def _set_future_episode_reserve(self, count):
        super()._set_future_episode_reserve(count)
        self._future_reserve = self._reserve_after

    def _complete(self, messages, *, tools=None, response_format=None, context):
        # Bypass v13's fallback: never release reserves belonging to later roles.
        messages = [dict(message) for message in messages]
        messages.insert(0, {"role": "system", "content": EVIDENCE_DISCIPLINE})
        try:
            return HarnessV12._complete(
                self, messages, tools=tools, response_format=response_format,
                context=context,
            )
        except ComputeBudgetExhausted as exc:
            if tools is None or str(exc) != "CAUSAL_V12_COMPUTE_BUDGET_EXHAUSTED":
                raise
            previous = self._reserve_after
            self._reserve_after = self._future_reserve
            self.ledger.append({
                "kind": "causal_v14_terminal_report_fallback",
                "context": context,
                "preserved_future_reserve": self._future_reserve,
                "released_reserve": previous - self._future_reserve,
            })
            try:
                return HarnessV12._complete(
                    self, messages, tools=None, response_format=response_format,
                    context={**context, "terminal_report_fallback": True},
                )
            finally:
                self._reserve_after = previous

    def _recover_report(self, task, report, acquired, calls, errors, *, condition, agent_id):
        if report is not None:
            return report
        # Exactly one attempt, no new evidence, same request/token gate. Keep all
        # original errors visible even when the final report becomes valid.
        try:
            recovered, completion, recovery_errors = self._private_review(
                task, None, acquired, condition=condition, agent_id=agent_id,
                review_index=0,
            )
        except ComputeBudgetExhausted as exc:
            if str(exc) not in {
                "CAUSAL_V12_COMPUTE_BUDGET_EXHAUSTED",
                "CAUSAL_V12_REQUEST_LIMIT_REACHED",
            }:
                raise
            self.ledger.append({
                "kind": "causal_v14_report_recovery_skipped",
                "condition": condition, "agent_id": agent_id, "reason": str(exc),
            })
            return None
        calls.append(completion)
        errors.extend(recovery_errors)
        self.ledger.append({
            "kind": "causal_v14_report_recovery",
            "condition": condition, "agent_id": agent_id,
            "recovered": recovered is not None,
            "report": recovered.mapping() if recovered else None,
            "acquired_evidence": sorted(acquired),
        })
        return recovered

    def _agent_episode(self, task, **kwargs):
        report, acquired, spent, calls, errors = super()._agent_episode(task, **kwargs)
        report = self._recover_report(
            task, report, acquired, calls, errors,
            condition=kwargs["condition"], agent_id=kwargs["agent_id"],
        )
        return report, acquired, spent, calls, errors

    def _shared_episode(self, task, **kwargs):
        if kwargs["agent_id"] == "shared-coordinator":
            kwargs["extra_context"] = json.dumps({
                "scout_report": self._scout_report.mapping() if self._scout_report else None,
                "acquisition_proposals": kwargs.get("extra_context", ""),
                "instruction": (
                    "Audit the scout diagnosis against purchased evidence. Explain any "
                    "change using specific evidence; confidence alone is not support."
                ),
            }, sort_keys=True)
        report, calls, errors = super()._shared_episode(task, **kwargs)
        report = self._recover_report(
            task, report, kwargs["pool"].acquired, calls, errors,
            condition="communicating_collective", agent_id=kwargs["agent_id"],
        )
        if kwargs["agent_id"] == "shared-scout":
            self._scout_report = report
        return report, calls, errors


def v14_condition_plan(task, condition, *, compute_plan=ComputePlanV14(), **kwargs):
    return {
        **v13_condition_plan(task, condition, compute_plan=compute_plan, **kwargs),
        "protocol_version": "causal-1.4-dev",
        "evidence_discipline": EVIDENCE_DISCIPLINE,
        "report_recovery_attempts": 1,
        "coordinator_receives_scout_report": True,
    }
