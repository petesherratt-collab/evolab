"""Code-only condition: a scripted client in place of the model.

``ScriptedClient`` has the same ``complete`` interface as ``OpenRouterClient``
and goes through the same harness, budget and scoring, but makes no provider
call. It stands for a programmer who has read the task templates and writes an
ordinary program for them:

* it sees only what an agent sees: the public briefing, the catalogue
  descriptions and the results of evidence it buys;
* it never reads hidden worlds, the correct candidate or the oracle;
* it buys the cheapest decisive route the descriptions name (the direct
  channel for each signature bit; each reference and trace pair; the physical
  measurements plus the polarity calibration) and nothing else;
* it combines the results by set intersection and reports a uniform
  distribution over the candidates that remain.

Its purpose is a floor that costs nothing: a model condition is only worth its
compute where it beats this program. The exact oracle serves as the offline
checker: tests assert that the script's distribution equals the oracle's
posterior on the evidence the script bought.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .core import FaultTask, score_report
from .openrouter import Completion

SCRIPTED_MODEL = "scripted-code-1.0"

_DIRECT = re.compile(r"^Independent diagnostic channel for signature bit (\d+)$")
_REFERENCE = re.compile(r"^Reference member of diagnostic pair (\d+)$")
_TRACE = re.compile(r"^Trace member of diagnostic pair (\d+); XOR with its reference$")
_PHYSICAL = re.compile(r"^Physical measurement for signature bit (\d+), before calibration correction$")
_CALIBRATION = "Read the polarity calibration for physical measurements"
_COMPATIBLE = re.compile(r"compatible candidates are: ([^.]*)\.")
_BIT = re.compile(r": ([01])\.")
_XOR_MAP = re.compile(r"XOR 0 maps to \[([^\]]*)\]; XOR 1 maps to \[([^\]]*)\]")


def _names(text: str) -> set[str]:
    return {name.strip() for name in text.split(",") if name.strip()}


def plan_purchases(task: dict[str, Any], budget: int) -> list[str]:
    """Evidence ids to buy, from catalogue descriptions only."""
    catalogue = task["evidence_catalogue"]
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in catalogue:
        description = item["description"]
        for kind, pattern in (("direct", _DIRECT), ("reference", _REFERENCE),
                              ("trace", _TRACE), ("physical", _PHYSICAL)):
            match = pattern.match(description)
            if match:
                groups.setdefault((kind, match.group(1)), []).append(item)
        if description == _CALIBRATION:
            groups.setdefault(("calibration", ""), []).append(item)

    def cheapest(key: tuple[str, str]) -> dict[str, Any] | None:
        items = groups.get(key)
        return min(items, key=lambda i: (i["cost"], i["evidence_id"])) if items else None

    wanted: list[dict[str, Any]] = []
    directs = sorted(k for k in groups if k[0] == "direct")
    pairs = sorted({k[1] for k in groups if k[0] in ("reference", "trace")}, key=int)
    physicals = sorted(k for k in groups if k[0] == "physical")
    if directs:
        wanted = [cheapest(k) for k in directs]
    elif pairs:
        # The signature has three bits and each pair recovers one, so three
        # pairs suffice: the three cheapest, lowest number first on a tie.
        ranked = sorted(pairs, key=lambda p: (sum(i["cost"] for k in (("reference", p), ("trace", p))
                                                   for i in [cheapest(k)] if i), int(p)))
        for pair in ranked[:3]:
            wanted += [cheapest(("reference", pair)), cheapest(("trace", pair))]
    elif physicals:
        wanted = [cheapest(("calibration", ""))] + [cheapest(k) for k in physicals]
    chosen, spent = [], 0
    for item in wanted:
        if item is not None and spent + item["cost"] <= budget:
            chosen.append(item["evidence_id"])
            spent += item["cost"]
    return chosen


def infer(task: dict[str, Any], results: dict[str, str]) -> tuple[dict[str, float], list[str]]:
    """Uniform distribution over the candidates every bought result allows,
    and the evidence ids that constrained it."""
    candidates = list(task["candidates"])
    by_id = {item["evidence_id"]: item["description"] for item in task["evidence_catalogue"]}
    allowed = set(candidates)
    used: list[str] = []
    inverted = None
    for evidence_id, text in results.items():
        if by_id.get(evidence_id) == _CALIBRATION:
            inverted = "inverted" in text
            used.append(evidence_id)
    references = {}
    for evidence_id, text in results.items():
        match = _REFERENCE.match(by_id.get(evidence_id, ""))
        bit = _BIT.search(text)
        if match and bit:
            references[match.group(1)] = (evidence_id, int(bit.group(1)))
    for evidence_id, text in sorted(results.items()):
        description = by_id.get(evidence_id, "")
        compatible = _COMPATIBLE.search(text)
        if _DIRECT.match(description) and compatible:
            allowed &= _names(compatible.group(1))
            used.append(evidence_id)
        elif _PHYSICAL.match(description) and compatible and inverted is not None:
            group = _names(compatible.group(1))
            allowed &= (set(candidates) - group) if inverted else group
            used.append(evidence_id)
        elif _TRACE.match(description):
            pair = _TRACE.match(description).group(1)
            bit, mapping = _BIT.search(text), _XOR_MAP.search(text)
            if pair in references and bit and mapping:
                xor = references[pair][1] ^ int(bit.group(1))
                allowed &= _names(mapping.group(xor + 1))
                used += [references[pair][0], evidence_id]
    if not allowed:
        allowed = set(candidates)
    share = 1.0 / len(allowed)
    return {c: (share if c in allowed else 0.0) for c in candidates}, sorted(set(used))


def _report(task: dict[str, Any], probabilities: dict[str, float], cited: list[str]) -> dict[str, Any]:
    order = list(task["candidates"])
    ranked = sorted(order, key=lambda c: (-probabilities[c], order.index(c)))
    return {
        "diagnosis": ranked[0],
        "probabilities": probabilities,
        "cited_evidence": cited,
        "rationale": "Scripted: intersection of the candidate sets named by the bought direct, "
                     "paired or polarity-corrected evidence; uniform over what remains.",
        "strongest_alternative": ranked[1],
        "recommended_verification": [],
    }


class ScriptedClient:
    """Drop-in for ``OpenRouterClient``; no network, no tokens, no cost."""

    model = SCRIPTED_MODEL

    def __init__(self) -> None:
        self._calls = 0

    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        max_tokens: int = 1400,
        seed: int | None = None,
    ) -> Completion:
        self._calls += 1
        brief = json.loads(next(m["content"] for m in messages if m["role"] == "user"))
        task, budget = brief["task"], int(brief["evidence_budget"])
        results: dict[str, str] = {}
        for message in messages:
            if message.get("role") == "tool":
                for item in json.loads(message["content"]).get("results", []):
                    if item.get("status") == "acquired":
                        results[item["evidence_id"]] = item["result"]
        bought_before = any(m.get("role") == "tool" for m in messages)
        if tools and not bought_before:
            purchases = plan_purchases(task, budget)
            if purchases:
                message = {
                    "role": "assistant", "content": None,
                    "tool_calls": [{
                        "id": f"scripted-{self._calls}", "type": "function",
                        "function": {"name": "buy_evidence",
                                     "arguments": json.dumps({"evidence_ids": purchases})},
                    }],
                }
                return Completion(f"scripted-{self._calls}", SCRIPTED_MODEL, None, message, {}, "tool_calls")
        probabilities, cited = infer(task, results)
        message = {"role": "assistant", "content": json.dumps(_report(task, probabilities, cited))}
        return Completion(f"scripted-{self._calls}", SCRIPTED_MODEL, None, message, {}, "stop")


def run_scripted_condition(harness: Any, task: FaultTask) -> Any:
    """Run ``scripted_code`` on a harness built with ``ScriptedClient``.

    One episode on the single agent's 100-unit budget, through the harness's
    own evidence tool and scoring; no review calls and no compute matching.
    Kept here rather than in ``runner.py`` so that the frozen harness source,
    whose hash the sealed manifests record, is untouched.
    """
    from .runner import ConditionResult

    if not isinstance(harness.client, ScriptedClient):
        raise ValueError("SCRIPTED_CONDITION_NEEDS_SCRIPTED_CLIENT")
    report, acquired, spent, calls, errors = harness._agent_episode(
        task, role="Scripted code-only condition.", budget=100,
        condition="scripted_code", agent_id="scripted",
    )
    result = ConditionResult(
        condition="scripted_code", report=report, score=score_report(task, report, acquired),
        acquired_evidence=tuple(sorted(acquired)), evidence_spent=spent, api_requests=len(calls),
        usage={}, errors=tuple(errors), valid_constituents=int(report is not None),
        failed_constituents=int(report is None),
    )
    harness.ledger.append({"kind": "condition_complete", "task_id": task.task_id, "result": result.mapping()})
    return result
