from __future__ import annotations

import json

from .protocol_v15 import ComputePlanV15, EVIDENCE_DISCIPLINE, acquisition_schedule
from .runner_v12 import ComputeBudgetExhausted, HarnessV12
from .runner_v14 import HarnessV14, v14_condition_plan


class HarnessV15(HarnessV14):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._seen_tool_results = set()

    def run_condition(self, *args, **kwargs):
        self._seen_tool_results.clear()
        return super().run_condition(*args, **kwargs)

    def _record_tool_results(self, messages, context):
        for message in messages:
            if message.get("role") != "tool":
                continue
            key = (context.get("condition"), context.get("agent_id"), message.get("tool_call_id"))
            if key in self._seen_tool_results:
                continue
            self._seen_tool_results.add(key)
            try:
                result = json.loads(message.get("content", ""))
            except (ValueError, TypeError):
                result = {"unparsed_tool_content": message.get("content")}
            self.ledger.append({"kind": "causal_v15_tool_result", "context": context,
                                "tool_call_id": message.get("tool_call_id"), "result": result})

    def _dispatch(self, messages, *, tools, response_format, context):
        round_index = context.get("round")
        schedule = acquisition_schedule(
            self.max_tool_rounds, round_index if isinstance(round_index, int) else 0,
            tools is not None,
        )
        prepared = [{"role": "system", "content": EVIDENCE_DISCIPLINE + " " + schedule}, *messages]
        completion = HarnessV12._complete(
            self, prepared, tools=tools, response_format=response_format, context=context,
        )
        tool_calls = completion.message.get("tool_calls") or []
        self.ledger.append({
            "kind": "causal_v15_call_observation", "context": context,
            "request_id": completion.request_id, "tools_offered": tools is not None,
            "requested_tool_calls": tool_calls,
            "stop_reason": (
                "tool_request" if tool_calls else
                "compute_reservation_terminal_fallback" if context.get("terminal_report_fallback") else
                "configured_tool_round_limit" if isinstance(round_index, int) and round_index >= self.max_tool_rounds else
                "model_returned_without_tool_request" if tools is not None else "tool_free_report_or_review"
            ),
        })
        return completion

    def _complete(self, messages, *, tools=None, response_format=None, context):
        # Use the v12 accounting path directly so the superseded blanket v14
        # instruction is never prepended. Recovery and scout handoff are inherited.
        self._record_tool_results(messages, context)
        try:
            return self._dispatch(messages, tools=tools, response_format=response_format, context=context)
        except ComputeBudgetExhausted as exc:
            if tools is None or str(exc) != "CAUSAL_V12_COMPUTE_BUDGET_EXHAUSTED":
                raise
            previous = self._reserve_after
            self._reserve_after = self._future_reserve
            self.ledger.append({"kind": "causal_v15_terminal_report_fallback", "context": context,
                                "preserved_future_reserve": self._future_reserve,
                                "released_reserve": previous-self._future_reserve})
            try:
                return self._dispatch(messages, tools=None, response_format=response_format,
                                      context={**context, "terminal_report_fallback": True})
            finally:
                self._reserve_after = previous


def v15_condition_plan(task, condition, *, compute_plan=ComputePlanV15(), **kwargs):
    return {
        **v14_condition_plan(task, condition, compute_plan=compute_plan, **kwargs),
        "protocol_version": "causal-1.5-dev",
        "evidence_discipline": EVIDENCE_DISCIPLINE,
        "batch_acquisition_schedule_disclosed": True,
        "public_interpretation_registry": True,
        "tool_requests_and_results_recorded": True,
    }
