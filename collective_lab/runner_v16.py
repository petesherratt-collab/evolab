"""Two separate experiments with explicit evidence and stopping contracts."""
from __future__ import annotations

import hashlib
import json
import math

from .core import parse_report, score_report
from .oracle import ExactOracle
from .protocol_v13 import lens_charter
from .protocol_v16 import (
    ACQUISITION_CONDITIONS, ACQUISITION_CONTRACT, ComputePlanV16, DISCIPLINE,
    MAX_ACQUISITION_DECISIONS, REASONING_CONDITIONS, VERSION,
)
from .runner import _json_from_text, _report_contract, _report_response_format, _usage_totals
from .runner_v11 import HarnessV11
from .runner_v12 import ConditionTokenGate, ComputeBudgetExhausted


def decision_format(task):
    ids = {"type": "array", "items": {"type": "string", "enum": list(task.evidence_map())}}
    properties = {
        "action": {"type": "string", "enum": ["buy", "finish"]},
        "evidence_ids": ids, "remaining_bundle": ids,
        "remaining_uncertainty": {"type": "string"},
        "reason": {"type": "string"}, "accept_early_stop": {"type": "boolean"},
    }
    return {"type": "json_schema", "json_schema": {
        "name": "acquisition_decision", "strict": True, "schema": {
            "type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False,
        },
    }}


def parse_decision(value, task):
    fields = {"action", "evidence_ids", "remaining_bundle", "remaining_uncertainty",
              "reason", "accept_early_stop"}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("V16_EXPLICIT_DECISION_REQUIRED")
    if value["action"] not in {"buy", "finish"} or type(value["accept_early_stop"]) is not bool:
        raise ValueError("V16_DECISION_INVALID")
    for field in ("reason", "remaining_uncertainty"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise ValueError("V16_DECISION_EXPLANATION_REQUIRED")
    for field in ("evidence_ids", "remaining_bundle"):
        ids = value[field]
        if not isinstance(ids, list) or not all(isinstance(eid, str) for eid in ids):
            raise ValueError("V16_BUNDLE_INVALID")
        if len(set(ids)) != len(ids) or not set(ids) <= set(task.evidence_map()):
            raise ValueError("V16_BUNDLE_INVALID")
    if (value["action"] == "buy") != bool(value["evidence_ids"]):
        raise ValueError("V16_ACTION_BUNDLE_MISMATCH")
    return value


def score_diagnostics(case, report, acquired):
    """Privileged diagnostics run AFTER inference, never used for live decisions."""
    oracle = ExactOracle(case.causal_task)
    q = oracle.observed_posterior(acquired)
    full = oracle.observed_posterior(case.packet_ids)
    score = score_report(case.task, report, set(acquired)).mapping()
    if report is None:
        leaders = []
        expected = 2.0
        regret = None
    else:
        p = report.probabilities
        peak = max(p.values())
        leaders = [c for c, value in p.items() if abs(value - peak) < 1e-12]
        expected = 1 + sum(value * value for value in p.values()) - 2 * sum(p[c] * full[c] for c in p)
        regret = sum((p[c] - q[c]) ** 2 for c in p)
    return {
        **score, "probability_leaders": leaders,
        "unique_correct_leader": leaders == [case.task.correct_candidate],
        "tied_lead": len(leaders) > 1,
        "oracle_given_acquired": q,
        "oracle_uncertainty_given_acquired": 1 - sum(value * value for value in q.values()),
        "squared_distance_from_acquired_oracle": regret,
        "expected_brier_given_reference_packet": expected,
    }


class HarnessV16:
    def __init__(self, client, ledger, *, compute_plan=ComputePlanV16()):
        self.client = client
        self.ledger = ledger
        self.plan = compute_plan

    def _call(self, task, packet, *, phase, instruction, history, response_format,
              reserve_after=0, wallet=None):
        payload = {"task": task.public(), "evidence_packet": packet,
                   "perspective_charter": lens_charter(), "history": history,
                   "instruction": instruction}
        if wallet is not None:
            payload["wallet"] = wallet
        messages = [{"role": "system", "content": DISCIPLINE},
                    {"role": "user", "content": json.dumps(payload, sort_keys=True)}]
        cap, estimate = self.gate.preflight(
            messages, tools=None, response_format=response_format,
            reserve_after=reserve_after, requested_max=self.plan.max_completion_tokens,
        )
        seed = int.from_bytes(hashlib.sha256(f"{task.task_id}|{phase}".encode()).digest()[:4], "big")
        completion = self.client.complete(messages, tools=None, response_format=response_format,
                                          max_tokens=cap, seed=seed)
        self.completions.append(completion)
        self.ledger.append({"kind": "causal_v16_completion", "condition": self.condition,
                            "task_id": task.task_id, "phase": phase,
                            "request_id": completion.request_id, "usage": completion.usage,
                            "message": completion.message, "finish_reason": completion.finish_reason,
                            "prompt_estimate": estimate, "completion_cap": cap,
                            "visible_evidence_ids": sorted(packet)})
        total = completion.usage.get("total_tokens")
        if isinstance(total, bool) or not isinstance(total, (int, float)) or not math.isfinite(total) or total <= 0:
            raise ValueError("V16_USAGE_MISSING_OR_INVALID")
        self.gate.record(completion)
        if completion.finish_reason not in {"stop", "end_turn"}:
            raise ValueError("V16_COMPLETION_NOT_FINISHED")
        if completion.message.get("tool_calls"):
            raise ValueError("V16_UNEXPECTED_TOOL_CALL")
        return _json_from_text(completion.message.get("content") or "")

    def _report(self, task, packet, *, phase, instruction, history, reserve_after=0):
        try:
            value = self._call(task, packet, phase=phase,
                               instruction=instruction + " " + _report_contract(task),
                               history=history, response_format=_report_response_format(task),
                               reserve_after=reserve_after)
            report = parse_report(value, task)
            if not set(report.cited_evidence) <= set(packet):
                raise ValueError("V16_UNSUPPORTED_CITATION")
            return report
        except ComputeBudgetExhausted:
            raise
        except ValueError as exc:
            # Preserve failures, including failed constituents, in eligibility.
            self.errors.append(f"{phase}:{exc}")
            if str(exc) == "V16_USAGE_MISSING_OR_INVALID":
                raise
            return None

    def _reason(self, case):
        task, packet = case.task, case.packet()
        drafts = []
        lenses = list(lens_charter())
        offset = int(hashlib.sha256(task.task_id.encode()).hexdigest()[:8], 16) % 4
        lenses = lenses[offset:] + lenses[:offset]
        for i, lens in enumerate(lenses):
            shared = self.condition in {"single_agent", "communicating_collective"}
            history = [r.mapping() if r else None for r in drafts] if shared else []
            instruction = (
                "Continue your private analysis using all four perspectives."
                if self.condition == "single_agent" else
                f"Act as investigator {i+1}, using perspective {lens['lens_id']}: {lens['instruction']}"
            )
            remaining = 3-i + int(self.condition != "independent_vote")
            drafts.append(self._report(task, packet, phase=f"draft_{i}", instruction=instruction,
                                       history=history, reserve_after=remaining*3200))
        if self.condition == "independent_vote":
            report = HarnessV11._vote_report(task, drafts)
        else:
            report = self._report(task, packet, phase="final",
                                  instruction="Reconcile the four analyses and return the final report.",
                                  history=[r.mapping() if r else None for r in drafts])
        return report, packet, 0, "fixed_evidence_packet"

    def _acquire(self, case):
        task = case.task
        evidence = task.evidence_map()
        packet = {}
        spent = 0
        history = []
        stop = "decision_limit"
        lenses = lens_charter()
        for i in range(MAX_ACQUISITION_DECISIONS):
            actor = "single" if self.condition == "acquisition_single" else f"participant_{i%4}"
            perspective = "Use all four perspectives." if actor == "single" else lenses[i%4]["instruction"]
            remaining = case.acquisition_budget - spent
            try:
                raw = self._call(task, packet, phase=f"decision_{i}",
                                 instruction=f"{ACQUISITION_CONTRACT} Actor: {actor}. {perspective}",
                                 history=history, response_format=decision_format(task), reserve_after=3200,
                                 wallet={"total": case.acquisition_budget, "remaining": remaining,
                                         "decisions_remaining_including_this": MAX_ACQUISITION_DECISIONS-i})
                decision = parse_decision(raw, task)
            except ComputeBudgetExhausted:
                stop = "compute_limit"
                break
            except ValueError as exc:
                if str(exc) == "V16_USAGE_MISSING_OR_INVALID":
                    raise
                self.errors.append(f"decision_{i}:{exc}")
                event = {"actor": actor, "status": "invalid_decision", "error": str(exc)}
            else:
                new_ids = [eid for eid in decision["evidence_ids"] if eid not in packet]
                cost = sum(evidence[eid].cost for eid in new_ids)
                pending = [eid for eid in decision["remaining_bundle"] if eid not in packet]
                pending_cost = sum(evidence[eid].cost for eid in pending)
                event = {"actor": actor, "decision": decision, "new_bundle_cost": cost,
                         "declared_remaining_bundle_cost": pending_cost,
                         "remaining_before": remaining}
                if decision["action"] == "buy":
                    if cost > remaining:
                        event["status"] = "over_budget_no_purchase"
                    else:
                        packet.update({eid: evidence[eid].result for eid in new_ids})
                        spent += cost
                        event["status"] = "purchased" if new_ids else "already_owned_no_charge"
                elif pending and pending_cost <= remaining and not decision["accept_early_stop"]:
                    event["status"] = "affordable_bundle_requires_buy_or_explicit_stop"
                else:
                    event["status"] = "explicit_finish"
                    stop = "explicit_early_stop" if pending and pending_cost <= remaining else "explicit_finish"
                event["remaining_after"] = case.acquisition_budget - spent
            history.append(event)
            self.ledger.append({"kind": "causal_v16_acquisition_decision", "condition": self.condition,
                                "task_id": task.task_id, "round": i, **event})
            if event["status"] == "explicit_finish":
                break
        self.ledger.append({"kind": "causal_v16_acquisition_stopped", "condition": self.condition,
                            "task_id": task.task_id, "reason": stop, "spent": spent,
                            "acquired": sorted(packet)})
        report = self._report(task, packet, phase="final",
                              instruction="Acquisition is closed. Diagnose using only acquired evidence.",
                              history=history)
        return report, packet, spent, stop

    def run_condition(self, case, condition):
        if condition not in (*REASONING_CONDITIONS, *ACQUISITION_CONDITIONS):
            raise ValueError("V16_CONDITION_UNKNOWN")
        self.condition = condition
        self.gate = ConditionTokenGate(self.plan)
        self.errors = []
        self.completions = []
        self.ledger.append({"kind": "causal_v16_condition_started", "protocol_version": VERSION,
                            "task_id": case.task.task_id, "condition": condition,
                            "task_fingerprint": case.causal_task.fingerprint(),
                            "compute_plan": self.plan.mapping(),
                            "evidence_contract": "shared_wallet" if condition in ACQUISITION_CONDITIONS
                            else "identical_fixed_packet"})
        try:
            report, packet, spent, stop = (
                self._reason(case) if condition in REASONING_CONDITIONS else self._acquire(case)
            )
        except Exception as exc:
            self.ledger.append({"kind": "causal_v16_condition_failed", "condition": condition,
                                "task_id": case.task.task_id, "error": str(exc),
                                "usage": _usage_totals(self.completions)})
            raise  # No silent exclusions, reruns or automatic paid retries.
        result = {"condition": condition, "report": report.mapping() if report else None,
                  "score": score_diagnostics(case, report, packet), "evidence_ids": sorted(packet),
                  "evidence_spent": spent, "stop_reason": stop, "errors": self.errors,
                  "api_requests": len(self.completions), "usage": _usage_totals(self.completions),
                  "eligible": report is not None and not self.errors}
        self.ledger.append({"kind": "causal_v16_condition_complete", "task_id": case.task.task_id, **result})
        return result
