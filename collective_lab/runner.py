from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import platform
import re
import sys
from typing import Any

from evolutionary_lab.evidence import EvidenceLedger

from .core import FaultTask, Report, Score, parse_report, score_report
from .ledger import ExclusiveRunLedger
from .openrouter import Completion, OpenRouterClient


BUY_EVIDENCE_TOOL = {
    "type": "function",
    "function": {
        "name": "buy_evidence",
        "description": "Purchase one or more catalogue evidence items. Costs are charged even if the result is unhelpful.",
        "parameters": {
            "type": "object",
            "properties": {
                "evidence_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                }
            },
            "required": ["evidence_ids"],
            "additionalProperties": False,
        },
    },
}


ROLES = (
    "Hydraulics investigator: prioritize pump and flow explanations while checking alternatives.",
    "Thermal and sensor investigator: prioritize heat-transfer and measurement explanations while checking alternatives.",
    "Controls investigator: prioritize valve, command, and actuator explanations while checking alternatives.",
    "Independent generalist: seek disconfirming evidence and guard against premature consensus.",
)


@dataclass(frozen=True)
class ConditionResult:
    condition: str
    report: Report | None
    score: Score
    acquired_evidence: tuple[str, ...]
    evidence_spent: int
    api_requests: int
    usage: dict[str, float]
    errors: tuple[str, ...]
    valid_constituents: int = 0
    failed_constituents: int = 0

    def mapping(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "report": self.report.mapping() if self.report else None,
            "score": self.score.mapping(),
            "acquired_evidence": list(self.acquired_evidence),
            "evidence_spent": self.evidence_spent,
            "api_requests": self.api_requests,
            "usage": self.usage,
            "errors": list(self.errors),
            "valid_constituents": self.valid_constituents,
            "failed_constituents": self.failed_constituents,
        }


def _json_from_text(text: str) -> Any:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            return json.loads(stripped[start : end + 1])
        raise


def _report_contract(task: FaultTask) -> str:
    candidate_fields = ", ".join(f'"{name}": number' for name in task.candidates)
    return (
        "Return only one JSON object with exactly this semantic structure: "
        '{"diagnosis":"candidate", "probabilities":{'
        + candidate_fields
        + '}, "cited_evidence":["ID"], "rationale":"brief", '
        '"strongest_alternative":"candidate", "recommended_verification":["ID"]}. '
        "Probabilities must cover every candidate and sum to 1. Cite only evidence actually acquired."
    )


def _report_response_format(task: FaultTask) -> dict[str, Any]:
    """Strict Chat Completions schema for every report-producing call."""
    candidates = list(task.candidates)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "fault_isolation_report",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "diagnosis": {"type": "string", "enum": candidates},
                    "probabilities": {
                        "type": "object",
                        "properties": {
                            candidate: {"type": "number", "minimum": 0, "maximum": 1}
                            for candidate in candidates
                        },
                        "required": candidates,
                        "additionalProperties": False,
                    },
                    "cited_evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "rationale": {"type": "string"},
                    "strongest_alternative": {"type": "string", "enum": candidates},
                    "recommended_verification": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "diagnosis",
                    "probabilities",
                    "cited_evidence",
                    "rationale",
                    "strongest_alternative",
                    "recommended_verification",
                ],
                "additionalProperties": False,
            },
        },
    }


def _usage_totals(completions: list[Completion]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for completion in completions:
        for key, value in completion.usage.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                totals[key] = totals.get(key, 0.0) + float(value)
    return totals


def compute_assessment(
    results: list[ConditionResult], target_tokens: int, tolerance: float
) -> dict[str, Any]:
    if target_tokens <= 0:
        return {
            "target_tokens": target_tokens,
            "tolerance": tolerance,
            "condition_tokens": {
                result.condition: result.usage.get("total_tokens", 0.0)
                for result in results
            },
            "eligible": None,
            "reason": "COMPUTE_MATCHING_DISABLED",
            "max_to_min_ratio": None,
        }
    lower = target_tokens * (1.0 - tolerance)
    upper = target_tokens * (1.0 + tolerance)
    totals = {
        result.condition: result.usage.get("total_tokens", 0.0) for result in results
    }
    return {
        "target_tokens": target_tokens,
        "tolerance": tolerance,
        "lower_bound": lower,
        "upper_bound": upper,
        "condition_tokens": totals,
        "eligible": bool(results) and all(lower <= value <= upper for value in totals.values()),
        "max_to_min_ratio": (
            max(totals.values()) / min(totals.values())
            if totals and min(totals.values()) > 0
            else None
        ),
    }


class Harness:
    def __init__(
        self,
        client: OpenRouterClient,
        ledger: EvidenceLedger,
        *,
        max_tokens: int = 1400,
        max_tool_rounds: int = 3,
        seed: int = 20261101,
    ) -> None:
        self.client = client
        self.ledger = ledger
        self.max_tokens = max_tokens
        self.max_tool_rounds = max_tool_rounds
        self.seed = seed
        self._request_index = 0

    def _complete(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        context: dict[str, Any],
    ) -> Completion:
        self._request_index += 1
        completion = self.client.complete(
            messages,
            tools=tools,
            response_format=response_format,
            max_tokens=self.max_tokens,
            seed=self.seed + self._request_index,
        )
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
            }
        )
        return completion

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
                    "You are an isolated investigator in a controlled fictional diagnosis experiment. "
                    "Do not assume unpurchased evidence. Use the evidence tool strategically, remain calibrated, "
                    "and then provide the required JSON report. " + role
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
        for round_index in range(self.max_tool_rounds + 1):
            completion = self._complete(
                messages,
                tools=[BUY_EVIDENCE_TOOL] if round_index < self.max_tool_rounds else None,
                response_format=_report_response_format(task),
                context={"condition": condition, "agent_id": agent_id, "round": round_index},
            )
            completions.append(completion)
            message = dict(completion.message)
            messages.append(message)
            tool_calls = message.get("tool_calls")
            if isinstance(tool_calls, list) and tool_calls:
                for call in tool_calls:
                    call_id = str(call.get("id", ""))
                    function = call.get("function") if isinstance(call.get("function"), dict) else {}
                    try:
                        arguments = json.loads(str(function.get("arguments", "{}")))
                        requested = arguments.get("evidence_ids", [])
                        if not isinstance(requested, list) or not all(isinstance(item, str) for item in requested):
                            raise ValueError("EVIDENCE_IDS_INVALID")
                        results = []
                        for evidence_id in requested:
                            if evidence_id in acquired:
                                results.append({"evidence_id": evidence_id, "status": "already_acquired"})
                                continue
                            item = evidence_map.get(evidence_id)
                            if item is None:
                                results.append({"evidence_id": evidence_id, "status": "unknown"})
                                continue
                            if spent + item.cost > budget:
                                results.append({"evidence_id": evidence_id, "status": "over_budget"})
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
                        tool_result = {"results": results, "spent": spent, "remaining_budget": budget - spent}
                    except (ValueError, json.JSONDecodeError) as exc:
                        tool_result = {"error": str(exc), "spent": spent, "remaining_budget": budget - spent}
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
        report: Report | None = None
        if final_content:
            try:
                report = parse_report(_json_from_text(final_content), task)
            except (ValueError, json.JSONDecodeError) as exc:
                errors.append(str(exc))
                if completions[-1].finish_reason:
                    errors.append(f"FINISH_REASON_{completions[-1].finish_reason.upper()}")
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

    def _revise(
        self,
        task: FaultTask,
        own_report: Report | None,
        peer_reports: list[Report | None],
        *,
        agent_id: str,
    ) -> tuple[Report | None, Completion, list[str]]:
        messages = [
            {
                "role": "system",
                "content": "You are revising a diagnosis after structured peer communication. Do not invent evidence. Return only the required JSON report.",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task_candidates": list(task.candidates),
                        "own_report": own_report.mapping() if own_report else None,
                        "peer_reports": [report.mapping() if report else None for report in peer_reports],
                        "output_contract": _report_contract(task),
                    },
                    sort_keys=True,
                ),
            },
        ]
        completion = self._complete(
            messages,
            response_format=_report_response_format(task),
            context={"condition": "communicating_collective", "agent_id": agent_id, "round": "revision"},
        )
        errors: list[str] = []
        try:
            report = parse_report(_json_from_text(str(completion.message.get("content", ""))), task)
        except (ValueError, json.JSONDecodeError) as exc:
            report = None
            errors.append(str(exc))
            if completion.finish_reason:
                errors.append(f"FINISH_REASON_{completion.finish_reason.upper()}")
        return report, completion, errors

    def _private_review(
        self,
        task: FaultTask,
        report: Report | None,
        acquired: set[str],
        *,
        condition: str,
        agent_id: str,
        review_index: int,
    ) -> tuple[Report | None, Completion, list[str]]:
        evidence_map = task.evidence_map()
        acquired_results = [
            {
                "evidence_id": evidence_id,
                "result": evidence_map[evidence_id].result,
            }
            for evidence_id in sorted(acquired)
        ]
        messages = [
            {
                "role": "system",
                "content": (
                    "Perform a rigorous private audit of your current diagnosis. Look for contradictory evidence, "
                    "overconfidence, and a stronger alternative. You cannot communicate or acquire new evidence in "
                    "this review. Return only the required JSON report, revised if warranted."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": task.public(),
                        "acquired_evidence": acquired_results,
                        "current_report": report.mapping() if report else None,
                        "review_index": review_index,
                        "output_contract": _report_contract(task),
                    },
                    sort_keys=True,
                ),
            },
        ]
        completion = self._complete(
            messages,
            response_format=_report_response_format(task),
            context={
                "condition": condition,
                "agent_id": agent_id,
                "round": f"private_review_{review_index}",
            },
        )
        errors: list[str] = []
        try:
            revised = parse_report(
                _json_from_text(str(completion.message.get("content", ""))), task
            )
        except (ValueError, json.JSONDecodeError) as exc:
            revised = None
            errors.append(str(exc))
            if completion.finish_reason:
                errors.append(f"FINISH_REASON_{completion.finish_reason.upper()}")
        return revised or report, completion, errors

    def _synthesize(
        self,
        task: FaultTask,
        reports: list[Report | None],
        *,
        condition: str,
    ) -> tuple[Report | None, set[str], int, list[Completion], list[str]]:
        return self._agent_episode(
            task,
            role="You are the synthesizer. Reconcile the supplied reports and use the reserve only to resolve decisive uncertainty.",
            budget=20,
            condition=condition,
            agent_id="synthesizer",
            extra_context=json.dumps([report.mapping() if report else None for report in reports], sort_keys=True),
        )

    def run_condition(
        self,
        task: FaultTask,
        condition: str,
        *,
        target_tokens: int = 25_000,
        tolerance: float = 0.10,
    ) -> ConditionResult:
        reports: list[Report | None] = []
        acquired_sets: list[set[str]] = []
        total_spent = 0
        completions: list[Completion] = []
        errors: list[str] = []
        valid_constituents = 0
        failed_constituents = 0
        if condition == "single_agent":
            report, acquired, spent, calls, episode_errors = self._agent_episode(
                task,
                role="Act as a strong generalist. Seek both supporting and disconfirming evidence before answering.",
                budget=100,
                condition=condition,
                agent_id="single",
            )
            reports = [report]
            valid_constituents = int(report is not None)
            failed_constituents = int(report is None)
            acquired_sets = [acquired]
            total_spent = spent
            completions.extend(calls)
            errors.extend(episode_errors)
            final_report = report
            review_index = 0
            while (
                _usage_totals(completions).get("total_tokens", 0.0)
                < target_tokens * (1.0 - tolerance)
                and review_index < 14
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
            per_agent_budget = 25 if condition == "independent_vote" else 20
            for index, role in enumerate(ROLES):
                report, acquired, spent, calls, episode_errors = self._agent_episode(
                    task,
                    role=role,
                    budget=per_agent_budget,
                    condition=condition,
                    agent_id=f"investigator-{index + 1}",
                )
                reports.append(report)
                acquired_sets.append(acquired)
                total_spent += spent
                completions.extend(calls)
                errors.extend(episode_errors)
            valid_constituents = sum(report is not None for report in reports)
            failed_constituents = len(reports) - valid_constituents
            if condition == "independent_vote":
                review_index = 0
                while (
                    _usage_totals(completions).get("total_tokens", 0.0)
                    < target_tokens * (1.0 - tolerance)
                    and review_index < 14
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
                valid_constituents = sum(report is not None for report in reports)
                failed_constituents = len(reports) - valid_constituents
            if condition == "independent_vote":
                # A failed member contributes a uniform distribution. Dropping it
                # would reward the condition by silently reducing ensemble size.
                uniform = 1.0 / len(task.candidates)
                probabilities = {
                    candidate: sum(
                        report.probabilities[candidate] if report else uniform
                        for report in reports
                    ) / len(reports)
                    for candidate in task.candidates
                }
                diagnosis = max(
                    task.candidates,
                    key=lambda item: (probabilities[item], -task.candidates.index(item)),
                )
                valid = [report for report in reports if report]
                final_report = Report(
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
            elif condition in {"independent_synthesizer", "communicating_collective"}:
                synthesis_reports = reports
                if condition == "communicating_collective":
                    revised: list[Report | None] = []
                    for index, own_report in enumerate(reports):
                        revision, completion, revision_errors = self._revise(
                            task,
                            own_report,
                            [report for peer_index, report in enumerate(reports) if peer_index != index],
                            agent_id=f"investigator-{index + 1}",
                        )
                        revised.append(revision or own_report)
                        completions.append(completion)
                        errors.extend(revision_errors)
                    synthesis_reports = revised
                final_report, reserve_acquired, reserve_spent, calls, synthesis_errors = self._synthesize(
                    task, synthesis_reports, condition=condition
                )
                acquired_sets.append(reserve_acquired)
                total_spent += reserve_spent
                completions.extend(calls)
                errors.extend(synthesis_errors)
                review_index = 0
                acquired_for_synthesis = set().union(*acquired_sets)
                while (
                    _usage_totals(completions).get("total_tokens", 0.0)
                    < target_tokens * (1.0 - tolerance)
                    and review_index < 10
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
                raise ValueError(f"CONDITION_UNKNOWN: {condition}")
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
        self.ledger.append(
            {"kind": "condition_complete", "task_id": task.task_id, "result": result.mapping()}
        )
        return result


def run_engineering_task(
    task: FaultTask,
    *,
    output: Path,
    model: str = "openai/gpt-6.1-sol",
    conditions: tuple[str, ...] = (
        "single_agent",
        "independent_vote",
        "independent_synthesizer",
        "communicating_collective",
    ),
    max_tokens: int = 1400,
    max_tool_rounds: int = 3,
    seed: int = 20261101,
    target_tokens: int = 25_000,
    compute_tolerance: float = 0.10,
    manifest_reference: dict[str, str] | None = None,
    request_timeout_seconds: int = 300,
) -> list[ConditionResult]:
    if output.exists():
        raise FileExistsError(f"OUTPUT_ALREADY_EXISTS: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "phase": "engineering",
        "model": model,
        "conditions": list(conditions),
        "max_tokens": max_tokens,
        "max_tool_rounds": max_tool_rounds,
        "seed": seed,
        "target_tokens": target_tokens,
        "compute_tolerance": compute_tolerance,
        "manifest_reference": manifest_reference,
        "request_timeout_seconds": request_timeout_seconds,
    }
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()
    results: list[ConditionResult] = []
    with ExclusiveRunLedger(output) as ledger:
        ledger.append(
            {
                "kind": "run_started",
                "config": config,
                "config_hash": config_hash,
                "task_id": task.task_id,
                "task_fingerprint": task.fingerprint(),
                "environment": {"python": sys.version, "platform": platform.platform()},
            }
        )
        harness = Harness(
            OpenRouterClient(model=model, timeout_seconds=request_timeout_seconds),
            ledger,
            max_tokens=max_tokens,
            max_tool_rounds=max_tool_rounds,
            seed=seed,
        )
        try:
            for condition in conditions:
                results.append(
                    harness.run_condition(
                        task,
                        condition,
                        target_tokens=target_tokens,
                        tolerance=compute_tolerance,
                    )
                )
        except Exception as exc:
            ledger.append({"kind": "run_failed", "error_type": type(exc).__name__, "error": str(exc)[:2000]})
            raise
        ledger.append(
            {
                "kind": "run_complete",
                "task_id": task.task_id,
                "results": [result.mapping() for result in results],
                "compute_assessment": compute_assessment(
                    results, target_tokens, compute_tolerance
                ),
            }
        )
    return results
