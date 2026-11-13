from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from .core import FaultTask, Report, parse_report, score_report
from .openrouter import Completion
from .protocol_v11 import EvidenceAllocation
from .protocol_v12 import (
    ComputePlanV12,
    StagedEvidenceAllocation,
    v12_evidence_allocation,
)
from .runner import (
    BUY_EVIDENCE_TOOL,
    ROLES,
    ConditionResult,
    _json_from_text,
    _report_contract,
    _report_response_format,
    _usage_totals,
)
from .runner_v11 import HarnessV11


class ComputeBudgetExhausted(RuntimeError):
    pass


@dataclass
class ConditionTokenGate:
    plan: ComputePlanV12
    used_tokens: float = 0.0
    requests: int = 0

    def preflight(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None,
        response_format: dict[str, Any] | None,
        reserve_after: int,
        requested_max: int,
    ) -> tuple[int, int]:
        if self.plan.enabled and self.requests >= self.plan.max_condition_requests:
            raise ComputeBudgetExhausted("CAUSAL_V12_REQUEST_LIMIT_REACHED")
        estimate = self.plan.estimate_prompt_tokens(
            messages,
            tools=tools,
            response_format=response_format,
        )
        cap = self.plan.completion_cap(
            used_tokens=self.used_tokens,
            estimated_prompt_tokens=estimate,
            reserve_after=reserve_after,
            requested_max=requested_max,
        )
        if cap <= 0:
            raise ComputeBudgetExhausted("CAUSAL_V12_COMPUTE_BUDGET_EXHAUSTED")
        return cap, estimate

    def record(self, completion: Completion) -> None:
        usage = completion.usage
        total = usage.get("total_tokens")
        if not isinstance(total, (int, float)) or isinstance(total, bool):
            total = float(usage.get("prompt_tokens", 0.0)) + float(
                usage.get("completion_tokens", 0.0)
            )
        self.used_tokens += float(total)
        self.requests += 1
        if self.plan.enabled and self.used_tokens > self.plan.upper_bound:
            raise ComputeBudgetExhausted("CAUSAL_V12_COMPUTE_CEILING_EXCEEDED")


@dataclass
class SharedEvidencePool:
    total_budget: int
    acquired: set[str]
    spent: int = 0

    @property
    def remaining(self) -> int:
        return self.total_budget - self.spent


@dataclass(frozen=True)
class AcquisitionContingency:
    condition: str
    evidence_ids: tuple[str, ...]

    def mapping(self) -> dict[str, object]:
        return {"condition": self.condition, "evidence_ids": list(self.evidence_ids)}


@dataclass(frozen=True)
class AcquisitionProposal:
    priority_evidence: tuple[str, ...]
    contingencies: tuple[AcquisitionContingency, ...]
    avoid_evidence: tuple[str, ...]
    rationale: str

    def mapping(self) -> dict[str, object]:
        return {
            "priority_evidence": list(self.priority_evidence),
            "contingencies": [item.mapping() for item in self.contingencies],
            "avoid_evidence": list(self.avoid_evidence),
            "rationale": self.rationale,
        }


def _proposal_response_format(task: FaultTask) -> dict[str, Any]:
    evidence_ids = [item.evidence_id for item in task.evidence]
    evidence_array = {
        "type": "array",
        "items": {"type": "string", "enum": evidence_ids},
        "uniqueItems": True,
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "acquisition_proposal",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "priority_evidence": evidence_array,
                    "contingencies": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "condition": {"type": "string"},
                                "evidence_ids": evidence_array,
                            },
                            "required": ["condition", "evidence_ids"],
                            "additionalProperties": False,
                        },
                    },
                    "avoid_evidence": evidence_array,
                    "rationale": {"type": "string"},
                },
                "required": [
                    "priority_evidence",
                    "contingencies",
                    "avoid_evidence",
                    "rationale",
                ],
                "additionalProperties": False,
            },
        },
    }


def _parse_proposal(value: Any, task: FaultTask) -> AcquisitionProposal:
    if not isinstance(value, dict):
        raise ValueError("CAUSAL_V12_PROPOSAL_NOT_OBJECT")
    known = set(task.evidence_map())

    def evidence_tuple(field: str, source: dict[str, Any] = value) -> tuple[str, ...]:
        raw = source.get(field)
        if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
            raise ValueError(f"CAUSAL_V12_PROPOSAL_{field.upper()}_INVALID")
        if len(raw) != len(set(raw)) or not set(raw).issubset(known):
            raise ValueError(f"CAUSAL_V12_PROPOSAL_{field.upper()}_INVALID")
        return tuple(raw)

    raw_contingencies = value.get("contingencies")
    if not isinstance(raw_contingencies, list):
        raise ValueError("CAUSAL_V12_PROPOSAL_CONTINGENCIES_INVALID")
    contingencies = []
    for item in raw_contingencies:
        if not isinstance(item, dict) or not isinstance(item.get("condition"), str):
            raise ValueError("CAUSAL_V12_PROPOSAL_CONTINGENCY_INVALID")
        contingencies.append(
            AcquisitionContingency(
                condition=item["condition"][:1000],
                evidence_ids=evidence_tuple("evidence_ids", item),
            )
        )
    return AcquisitionProposal(
        priority_evidence=evidence_tuple("priority_evidence"),
        contingencies=tuple(contingencies),
        avoid_evidence=evidence_tuple("avoid_evidence"),
        rationale=str(value.get("rationale", ""))[:4000],
    )


class HarnessV12(HarnessV11):
    """Causal-1.2 harness with staged shared acquisition and a token gate."""

    def __init__(self, *args, compute_plan: ComputePlanV12, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.compute_plan_v12 = compute_plan
        self._token_gate: ConditionTokenGate | None = None
        self._reserve_after = 0

    def _complete(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        context: dict[str, Any],
    ) -> Completion:
        if self._token_gate is None:
            raise RuntimeError("CAUSAL_V12_TOKEN_GATE_NOT_ACTIVE")
        cap, prompt_estimate = self._token_gate.preflight(
            messages,
            tools=tools,
            response_format=response_format,
            reserve_after=self._reserve_after,
            requested_max=self.max_tokens,
        )
        self._request_index += 1
        completion = self.client.complete(
            messages,
            tools=tools,
            response_format=response_format,
            max_tokens=cap,
            seed=self.seed + self._request_index,
        )
        overflow: ComputeBudgetExhausted | None = None
        try:
            self._token_gate.record(completion)
        except ComputeBudgetExhausted as exc:
            overflow = exc
        self.ledger.append(
            {
                "kind": "model_completion",
                "context": context,
                "request_index": self._request_index,
                "request_id": completion.request_id,
                "requested_model": self.client.model,
                "returned_model": completion.model,
                "provider": completion.provider,
                "finish_reason": completion.finish_reason,
                "usage": completion.usage,
                "compute_gate": {
                    "estimated_prompt_tokens": prompt_estimate,
                    "max_completion_tokens": cap,
                    "reserve_after": self._reserve_after,
                    "condition_used_tokens": self._token_gate.used_tokens,
                },
            }
        )
        if overflow is not None:
            self.ledger.append(
                {
                    "kind": "causal_v12_compute_overflow",
                    "context": context,
                    "condition_used_tokens": self._token_gate.used_tokens,
                    "upper_bound": self.compute_plan_v12.upper_bound,
                }
            )
            raise overflow
        return completion

    def _set_future_episode_reserve(self, count: int) -> None:
        self._reserve_after = self.compute_plan_v12.reserve_for_mandatory_episodes(
            count
        )

    def _acquired_results(
        self, task: FaultTask, acquired: set[str]
    ) -> list[dict[str, str]]:
        evidence_map = task.evidence_map()
        return [
            {
                "evidence_id": evidence_id,
                "result": evidence_map[evidence_id].result,
            }
            for evidence_id in sorted(acquired)
        ]

    def _agent_episode(
        self,
        task: FaultTask,
        *,
        role: str,
        budget: int,
        condition: str,
        agent_id: str,
        extra_context: str = "",
    ) -> tuple[Report | None, set[str], int, list[Completion], list[str]]:
        acquired: set[str] = set()
        spent = 0
        completions: list[Completion] = []
        errors: list[str] = []
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are an isolated investigator in a controlled fictional "
                    "diagnosis experiment. Do not assume unpurchased evidence. "
                    "Use the evidence tool strategically, remain calibrated, and "
                    "then provide the required JSON report. "
                    + role
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": task.public(),
                        "evidence_budget": budget,
                        "additional_context": extra_context,
                        "output_contract": _report_contract(task),
                    },
                    sort_keys=True,
                ),
            },
        ]
        evidence_map = task.evidence_map()
        final_content: str | None = None
        future_reserve = self._reserve_after
        try:
            for round_index in range(self.max_tool_rounds + 1):
                offer_tools = round_index < self.max_tool_rounds
                self._reserve_after = future_reserve + (
                    self.compute_plan_v12.mandatory_episode_reserve_tokens
                    if offer_tools
                    else 0
                )
                completion = self._complete(
                    messages,
                    tools=[BUY_EVIDENCE_TOOL] if offer_tools else None,
                    response_format=_report_response_format(task),
                    context={
                        "condition": condition,
                        "agent_id": agent_id,
                        "round": round_index,
                    },
                )
                completions.append(completion)
                message = dict(completion.message)
                messages.append(message)
                tool_calls = message.get("tool_calls")
                if isinstance(tool_calls, list) and tool_calls:
                    for call in tool_calls:
                        call_id = str(call.get("id", ""))
                        function = (
                            call.get("function")
                            if isinstance(call.get("function"), dict)
                            else {}
                        )
                        try:
                            arguments = json.loads(
                                str(function.get("arguments", "{}"))
                            )
                            requested = arguments.get("evidence_ids", [])
                            if not isinstance(requested, list) or not all(
                                isinstance(item, str) for item in requested
                            ):
                                raise ValueError("EVIDENCE_IDS_INVALID")
                            results = []
                            for evidence_id in requested:
                                if evidence_id in acquired:
                                    results.append(
                                        {
                                            "evidence_id": evidence_id,
                                            "status": "already_acquired",
                                        }
                                    )
                                    continue
                                item = evidence_map.get(evidence_id)
                                if item is None:
                                    results.append(
                                        {
                                            "evidence_id": evidence_id,
                                            "status": "unknown",
                                        }
                                    )
                                    continue
                                if spent + item.cost > budget:
                                    results.append(
                                        {
                                            "evidence_id": evidence_id,
                                            "status": "over_budget",
                                        }
                                    )
                                    continue
                                acquired.add(evidence_id)
                                spent += item.cost
                                results.append(
                                    {
                                        "evidence_id": evidence_id,
                                        "status": "acquired",
                                        "cost": item.cost,
                                        "result": item.result,
                                        "remaining_budget": budget - spent,
                                    }
                                )
                                self.ledger.append(
                                    {
                                        "kind": "evidence_acquired",
                                        "condition": condition,
                                        "agent_id": agent_id,
                                        "task_id": task.task_id,
                                        "evidence_id": evidence_id,
                                        "cost": item.cost,
                                        "spent": spent,
                                        "budget": budget,
                                    }
                                )
                            tool_result = {
                                "results": results,
                                "spent": spent,
                                "remaining_budget": budget - spent,
                            }
                        except (ValueError, json.JSONDecodeError) as exc:
                            tool_result = {
                                "error": str(exc),
                                "spent": spent,
                                "remaining_budget": budget - spent,
                            }
                            errors.append(str(exc))
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call_id,
                                "name": "buy_evidence",
                                "content": json.dumps(tool_result, sort_keys=True),
                            }
                        )
                    continue
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    final_content = content
                    break
        finally:
            self._reserve_after = future_reserve

        report: Report | None = None
        if final_content:
            try:
                report = parse_report(_json_from_text(final_content), task)
            except (ValueError, json.JSONDecodeError) as exc:
                errors.append(str(exc))
                if completions and completions[-1].finish_reason:
                    errors.append(
                        f"FINISH_REASON_{completions[-1].finish_reason.upper()}"
                    )
        else:
            errors.append("REPORT_MISSING")
        self.ledger.append(
            {
                "kind": "agent_episode_complete",
                "condition": condition,
                "agent_id": agent_id,
                "task_id": task.task_id,
                "budget": budget,
                "spent": spent,
                "acquired_evidence": sorted(acquired),
                "report": report.mapping() if report else None,
                "errors": errors,
            }
        )
        return report, acquired, spent, completions, errors

    def _shared_episode(
        self,
        task: FaultTask,
        *,
        pool: SharedEvidencePool,
        stage_ceiling: int,
        role: str,
        agent_id: str,
        extra_context: str = "",
    ) -> tuple[Report | None, list[Completion], list[str]]:
        if not pool.spent <= stage_ceiling <= pool.total_budget:
            raise ValueError("CAUSAL_V12_STAGE_CEILING_INVALID")
        completions: list[Completion] = []
        errors: list[str] = []
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are operating one stage of a shared-budget diagnosis. "
                    "Previously acquired evidence is available without repurchase. "
                    "Buy only evidence that improves the shared plan, remain calibrated, "
                    "and return the required JSON report. "
                    + role
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": task.public(),
                        "shared_total_budget": pool.total_budget,
                        "stage_spending_ceiling": stage_ceiling,
                        "spent_before_stage": pool.spent,
                        "remaining_stage_budget": stage_ceiling - pool.spent,
                        "acquired_evidence": self._acquired_results(
                            task, pool.acquired
                        ),
                        "additional_context": extra_context,
                        "output_contract": _report_contract(task),
                    },
                    sort_keys=True,
                ),
            },
        ]
        evidence_map = task.evidence_map()
        final_content: str | None = None
        future_reserve = self._reserve_after
        try:
            for round_index in range(self.max_tool_rounds + 1):
                offer_tools = round_index < self.max_tool_rounds
                self._reserve_after = future_reserve + (
                    self.compute_plan_v12.mandatory_episode_reserve_tokens
                    if offer_tools
                    else 0
                )
                completion = self._complete(
                    messages,
                    tools=[BUY_EVIDENCE_TOOL] if offer_tools else None,
                    response_format=_report_response_format(task),
                    context={
                        "condition": "communicating_collective",
                        "agent_id": agent_id,
                        "round": round_index,
                        "stage": agent_id,
                    },
                )
                completions.append(completion)
                message = dict(completion.message)
                messages.append(message)
                tool_calls = message.get("tool_calls")
                if isinstance(tool_calls, list) and tool_calls:
                    for call in tool_calls:
                        call_id = str(call.get("id", ""))
                        function = (
                            call.get("function")
                            if isinstance(call.get("function"), dict)
                            else {}
                        )
                        try:
                            arguments = json.loads(
                                str(function.get("arguments", "{}"))
                            )
                            requested = arguments.get("evidence_ids", [])
                            if not isinstance(requested, list) or not all(
                                isinstance(item, str) for item in requested
                            ):
                                raise ValueError("EVIDENCE_IDS_INVALID")
                            results = []
                            for evidence_id in requested:
                                if evidence_id in pool.acquired:
                                    results.append(
                                        {
                                            "evidence_id": evidence_id,
                                            "status": "already_acquired_shared",
                                        }
                                    )
                                    continue
                                item = evidence_map.get(evidence_id)
                                if item is None:
                                    results.append(
                                        {
                                            "evidence_id": evidence_id,
                                            "status": "unknown",
                                        }
                                    )
                                    continue
                                if pool.spent + item.cost > stage_ceiling:
                                    results.append(
                                        {
                                            "evidence_id": evidence_id,
                                            "status": "over_stage_budget",
                                        }
                                    )
                                    continue
                                pool.acquired.add(evidence_id)
                                pool.spent += item.cost
                                results.append(
                                    {
                                        "evidence_id": evidence_id,
                                        "status": "acquired",
                                        "cost": item.cost,
                                        "result": item.result,
                                        "remaining_shared_budget": pool.remaining,
                                        "remaining_stage_budget": (
                                            stage_ceiling - pool.spent
                                        ),
                                    }
                                )
                                self.ledger.append(
                                    {
                                        "kind": "shared_evidence_acquired",
                                        "condition": "communicating_collective",
                                        "agent_id": agent_id,
                                        "task_id": task.task_id,
                                        "evidence_id": evidence_id,
                                        "cost": item.cost,
                                        "shared_spent": pool.spent,
                                        "shared_total_budget": pool.total_budget,
                                        "stage_ceiling": stage_ceiling,
                                    }
                                )
                            tool_result = {
                                "results": results,
                                "shared_spent": pool.spent,
                                "remaining_shared_budget": pool.remaining,
                                "remaining_stage_budget": stage_ceiling
                                - pool.spent,
                            }
                        except (ValueError, json.JSONDecodeError) as exc:
                            tool_result = {
                                "error": str(exc),
                                "shared_spent": pool.spent,
                                "remaining_shared_budget": pool.remaining,
                            }
                            errors.append(str(exc))
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call_id,
                                "name": "buy_evidence",
                                "content": json.dumps(tool_result, sort_keys=True),
                            }
                        )
                    continue
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    final_content = content
                    break
        finally:
            self._reserve_after = future_reserve
        report: Report | None = None
        if final_content:
            try:
                report = parse_report(_json_from_text(final_content), task)
            except (ValueError, json.JSONDecodeError) as exc:
                errors.append(str(exc))
        else:
            errors.append("REPORT_MISSING")
        self.ledger.append(
            {
                "kind": "causal_v12_shared_episode_complete",
                "condition": "communicating_collective",
                "agent_id": agent_id,
                "task_id": task.task_id,
                "stage_ceiling": stage_ceiling,
                "shared_spent": pool.spent,
                "acquired_evidence": sorted(pool.acquired),
                "report": report.mapping() if report else None,
                "errors": errors,
            }
        )
        return report, completions, errors

    def _propose_acquisition(
        self,
        task: FaultTask,
        *,
        role: str,
        agent_id: str,
        pool: SharedEvidencePool,
        scout_report: Report | None,
    ) -> tuple[AcquisitionProposal | None, Completion, list[str]]:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a deliberator in a shared-budget diagnosis. Propose "
                    "a resource-aware acquisition plan; do not claim unobserved results. "
                    + role
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": task.public(),
                        "acquired_evidence": self._acquired_results(task, pool.acquired),
                        "scout_report": scout_report.mapping()
                        if scout_report
                        else None,
                        "remaining_shared_budget": pool.remaining,
                        "proposal_contract": {
                            "priority_evidence": ["ID"],
                            "contingencies": [
                                {"condition": "observation", "evidence_ids": ["ID"]}
                            ],
                            "avoid_evidence": ["ID"],
                            "rationale": "brief",
                        },
                    },
                    sort_keys=True,
                ),
            },
        ]
        completion = self._complete(
            messages,
            response_format=_proposal_response_format(task),
            context={
                "condition": "communicating_collective",
                "agent_id": agent_id,
                "round": "acquisition_proposal",
            },
        )
        errors: list[str] = []
        try:
            proposal = _parse_proposal(
                _json_from_text(str(completion.message.get("content", ""))), task
            )
        except (ValueError, json.JSONDecodeError) as exc:
            proposal = None
            errors.append(str(exc))
        self.ledger.append(
            {
                "kind": "causal_v12_acquisition_proposal",
                "task_id": task.task_id,
                "agent_id": agent_id,
                "proposal": proposal.mapping() if proposal else None,
                "errors": errors,
            }
        )
        return proposal, completion, errors

    def _fill_private_reviews(
        self,
        task: FaultTask,
        report: Report | None,
        acquired: set[str],
        *,
        condition: str,
        agent_id: str,
        completions: list[Completion],
        errors: list[str],
    ) -> Report | None:
        review_index = 0
        self._reserve_after = 0
        while (
            self._token_gate is not None
            and self._token_gate.used_tokens < self.compute_plan_v12.lower_bound
            and review_index < self.compute_plan_v12.max_private_reviews
            and self.compute_plan_v12.permits_optional_call(
                self._token_gate.used_tokens
            )
        ):
            review_index += 1
            try:
                report, completion, review_errors = self._private_review(
                    task,
                    report,
                    acquired,
                    condition=condition,
                    agent_id=agent_id,
                    review_index=review_index,
                )
            except ComputeBudgetExhausted as exc:
                if str(exc) not in {
                    "CAUSAL_V12_COMPUTE_BUDGET_EXHAUSTED",
                    "CAUSAL_V12_REQUEST_LIMIT_REACHED",
                }:
                    raise
                self.ledger.append(
                    {
                        "kind": "causal_v12_optional_review_skipped",
                        "condition": condition,
                        "agent_id": agent_id,
                        "review_index": review_index,
                        "reason": str(exc),
                    }
                )
                break
            completions.append(completion)
            errors.extend(review_errors)
        return report

    def run_condition(
        self,
        task: FaultTask,
        condition: str,
        *,
        evidence_budget: int,
        minimum_path_costs: tuple[int, ...],
        compute_plan: ComputePlanV12 | None = None,
    ) -> ConditionResult:
        plan = compute_plan or self.compute_plan_v12
        if plan != self.compute_plan_v12:
            raise ValueError("CAUSAL_V12_COMPUTE_PLAN_MISMATCH")
        allocation = v12_evidence_allocation(
            condition,
            evidence_budget,
            task_id=task.task_id,
            minimum_path_costs=minimum_path_costs,
        )
        self.ledger.append(
            {
                "kind": "causal_v12_condition_plan",
                "task_id": task.task_id,
                "condition": condition,
                "evidence_allocation": allocation.mapping(),
                "compute_plan": plan.mapping(),
            }
        )
        self._token_gate = ConditionTokenGate(plan)
        self._reserve_after = 0
        reports: list[Report | None] = []
        acquired_sets: list[set[str]] = []
        completions: list[Completion] = []
        errors: list[str] = []
        total_spent = 0

        try:
            if condition == "single_agent":
                assert isinstance(allocation, EvidenceAllocation)
                self._set_future_episode_reserve(0)
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
                final_report = self._fill_private_reviews(
                    task,
                    report,
                    acquired,
                    condition=condition,
                    agent_id="single",
                    completions=completions,
                    errors=errors,
                )
                valid_constituents = int(final_report is not None)
                failed_constituents = int(final_report is None)
            elif condition == "communicating_collective":
                assert isinstance(allocation, StagedEvidenceAllocation)
                pool = SharedEvidencePool(evidence_budget, set())
                self._set_future_episode_reserve(
                    allocation.deliberator_count + 1
                )
                scout_report, calls, scout_errors = self._shared_episode(
                    task,
                    pool=pool,
                    stage_ceiling=allocation.scout_ceiling,
                    role=(
                        "Scout cheaply for routing, provenance, and observations "
                        "that should control later purchases. Preserve expensive "
                        "evidence for the deliberated stage."
                    ),
                    agent_id="shared-scout",
                )
                completions.extend(calls)
                errors.extend(scout_errors)
                proposals: list[AcquisitionProposal | None] = []
                for index, role in enumerate(ROLES):
                    self._set_future_episode_reserve(
                        allocation.deliberator_count - index
                    )
                    proposal, completion, proposal_errors = self._propose_acquisition(
                        task,
                        role=role,
                        agent_id=f"deliberator-{index + 1}",
                        pool=pool,
                        scout_report=scout_report,
                    )
                    proposals.append(proposal)
                    completions.append(completion)
                    errors.extend(proposal_errors)
                self._set_future_episode_reserve(0)
                final_report, calls, coordinator_errors = self._shared_episode(
                    task,
                    pool=pool,
                    stage_ceiling=allocation.total_budget,
                    role=(
                        "You are the shared acquisition coordinator. Reconcile "
                        "the deliberators, condition purchases on scout results, "
                        "and spend from the one remaining common pool."
                    ),
                    agent_id="shared-coordinator",
                    extra_context=json.dumps(
                        [proposal.mapping() if proposal else None for proposal in proposals],
                        sort_keys=True,
                    ),
                )
                completions.extend(calls)
                errors.extend(coordinator_errors)
                reports = [scout_report, final_report]
                acquired_sets = [set(pool.acquired)]
                total_spent = pool.spent
                final_report = self._fill_private_reviews(
                    task,
                    final_report,
                    pool.acquired,
                    condition=condition,
                    agent_id="shared-coordinator",
                    completions=completions,
                    errors=errors,
                )
                valid_constituents = sum(proposal is not None for proposal in proposals)
                failed_constituents = len(proposals) - valid_constituents
            else:
                assert isinstance(allocation, EvidenceAllocation)
                synth_required = int(condition == "independent_synthesizer")
                for index, (role, budget) in enumerate(
                    zip(ROLES, allocation.investigator_budgets, strict=True)
                ):
                    remaining_agents = len(ROLES) - index - 1
                    self._set_future_episode_reserve(
                        remaining_agents + synth_required
                    )
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
                    final_report = self._vote_report(task, reports)
                    acquired_union = set().union(*acquired_sets)
                    final_report = self._fill_private_reviews(
                        task,
                        final_report,
                        acquired_union,
                        condition=condition,
                        agent_id="vote-auditor",
                        completions=completions,
                        errors=errors,
                    )
                elif condition == "independent_synthesizer":
                    self._set_future_episode_reserve(0)
                    (
                        final_report,
                        reserve_acquired,
                        reserve_spent,
                        calls,
                        synthesis_errors,
                    ) = self._synthesize_v11(
                        task,
                        reports,
                        condition=condition,
                        budget=allocation.synthesis_budget,
                    )
                    acquired_sets.append(reserve_acquired)
                    total_spent += reserve_spent
                    completions.extend(calls)
                    errors.extend(synthesis_errors)
                    acquired_union = set().union(*acquired_sets)
                    final_report = self._fill_private_reviews(
                        task,
                        final_report,
                        acquired_union,
                        condition=condition,
                        agent_id="synthesizer",
                        completions=completions,
                        errors=errors,
                    )
                else:
                    raise ValueError(f"CAUSAL_V12_CONDITION_UNKNOWN: {condition}")
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
            if total_spent > evidence_budget:
                raise ValueError("CAUSAL_V12_EVIDENCE_BUDGET_EXCEEDED")
            if plan.enabled and result.usage.get("total_tokens", 0.0) > plan.upper_bound:
                raise ValueError("CAUSAL_V12_COMPUTE_CEILING_EXCEEDED")
            self.ledger.append(
                {
                    "kind": "condition_complete",
                    "task_id": task.task_id,
                    "result": result.mapping(),
                    "compute_gate": {
                        "requests": self._token_gate.requests,
                        "used_tokens": self._token_gate.used_tokens,
                        "upper_bound": plan.upper_bound,
                    },
                }
            )
            return result
        finally:
            self._token_gate = None
            self._reserve_after = 0


def v12_condition_plan(
    task: FaultTask,
    condition: str,
    *,
    evidence_budget: int,
    minimum_path_costs: tuple[int, ...],
    compute_plan: ComputePlanV12 = ComputePlanV12(),
) -> dict[str, Any]:
    allocation = v12_evidence_allocation(
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
    }
