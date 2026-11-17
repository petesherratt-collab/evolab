"""Offline, privileged development diagnostics. Never supply this output to agents."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from evolutionary_lab.evidence import verify_ledger
from .causal_generator_v13 import generate_causal_case_v13
from .oracle import ExactOracle


def stopping_point(calls, max_rounds):
    """Classify the recorded terminal call, not unlogged purchase intentions."""
    if not calls:
        return "no_episode_completion_record"
    context = calls[-1]["context"]
    if context.get("terminal_report_fallback"):
        return "compute_reservation_terminal_fallback"
    last_round = context.get("round")
    if isinstance(last_round, int) and last_round >= max_rounds:
        return "configured_tool_round_limit"
    return "ended_before_tool_round_limit"


def audit_task(path, spec):
    verification = verify_ledger(path)
    if not verification["valid"]:
        raise ValueError("INVALID_LEDGER")
    rows = [json.loads(line)["payload"] for line in path.read_text().splitlines()]
    case = generate_causal_case_v13(spec["seed"], spec["task_class"], spec["difficulty"])
    start = rows[0]
    if case.causal_task.fingerprint() != spec["causal_fingerprint"] or start["task_fingerprint"] != spec["causal_fingerprint"]:
        raise ValueError("TASK_FINGERPRINT_MISMATCH")
    completed = [r for r in rows if r["kind"] == "run_complete"]
    if len(completed) != 1:
        raise ValueError("EXPECTED_ONE_COMPLETED_RUN")
    task = case.task
    oracle = ExactOracle(case.causal_task)
    evidence = task.evidence_map()
    route = set(case.core_evidence)
    costs = {eid: item.cost for eid, item in evidence.items()}

    def evidence_assessment(acquired, report):
        acquired = set(acquired)
        posterior = oracle.observed_posterior(acquired)
        missing = sorted(route - acquired)
        probabilities = report["probabilities"] if report else None
        return {
            "acquired": sorted(acquired),
            "router_acquired": case.topology_router in acquired if case.topology_router else None,
            "missing_planned_route": missing,
            "missing_planned_route_cost": sum(costs[eid] for eid in missing),
            "oracle_posterior_given_acquired": posterior,
            "oracle_true_probability": posterior[task.correct_candidate],
            "meets_generator_sufficiency_threshold": posterior[task.correct_candidate] >= case.sufficiency_threshold - 1e-12,
            "report_uniform": probabilities is not None and all(abs(p-.2)<1e-9 for p in probabilities.values()),
            "report_oracle_l1_distance": sum(abs(probabilities[c]-posterior[c]) for c in posterior) if probabilities else None,
        }

    episodes = []
    for index, row in enumerate(rows):
        if row["kind"] not in {"agent_episode_complete", "causal_v12_shared_episode_complete"}:
            continue
        condition, agent = row["condition"], row["agent_id"]
        calls = [r for r in rows[:index] if r["kind"] == "model_completion"
                 and r["context"].get("condition") == condition
                 and r["context"].get("agent_id") == agent
                 and isinstance(r["context"].get("round"), int)]
        shared = row["kind"] == "causal_v12_shared_episode_complete"
        spent = row["shared_spent"] if shared else row["spent"]
        ceiling = row["stage_ceiling"] if shared else row["budget"]
        assessment = evidence_assessment(row["acquired_evidence"], row["report"])
        remaining = ceiling-spent
        episodes.append({
            "agent": agent, "condition": condition,
            "stop": stopping_point(calls, start["config"]["max_tool_rounds"]),
            "rounds": [{"round": r["context"]["round"], "finish_reason": r.get("finish_reason"),
                        "tokens": r["usage"].get("total_tokens"),
                        "cap": r["compute_gate"]["max_completion_tokens"],
                        "reserved_after": r["compute_gate"]["reserve_after"]} for r in calls],
            "spent": spent, "episode_ceiling": ceiling, "remaining_episode_budget": remaining,
            **assessment,
            "remaining_planned_route_affordable": assessment["missing_planned_route_cost"] <= remaining,
            "report": row["report"],
        })

    conditions = []
    for result in completed[0]["results"]:
        condition = result["condition"]
        calls = [r for r in rows if r["kind"] == "model_completion" and r["context"].get("condition") == condition]
        reviews = [r for r in calls if str(r["context"].get("round", "")).startswith("private_review_")]
        assessment = evidence_assessment(result["acquired_evidence"], result["report"])
        remaining = case.evidence_budget-result["evidence_spent"]
        conditions.append({
            "condition": condition, "evidence_budget": case.evidence_budget,
            "spent": result["evidence_spent"], "remaining_budget": remaining,
            **assessment,
            "remaining_planned_route_affordable_from_pooled_remainder": assessment["missing_planned_route_cost"] <= remaining,
            "private_review_calls_including_recovery": len(reviews),
            "private_review_tokens_including_recovery": sum(r["usage"].get("total_tokens", 0) for r in reviews),
            "total_tokens": result["usage"]["total_tokens"],
            "final_report": result["report"],
        })
    return {
        "ledger": str(path), "verification": verification,
        "task_class": spec["task_class"], "difficulty": spec["difficulty"],
        "seed": spec["seed"], "fingerprint_verified": True,
        "planned_route": list(case.core_evidence), "planned_route_cost": sum(case.minimum_path_costs),
        "router": case.topology_router, "threshold": case.sufficiency_threshold,
        "route_posterior": oracle.observed_posterior(case.core_evidence),
        "catalogue": [{"id": e.evidence_id, "cost": e.cost, "description": e.description,
                       "observed_result": e.result} for e in task.evidence],
        "episodes": episodes, "conditions": conditions,
        "proposals": [r for r in rows if r["kind"] == "causal_v12_acquisition_proposal"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())["payload"]
    tasks = []
    for spec in manifest["tasks"]:
        paths = list(args.directory.glob(f'task-{spec["task_index"]:02d}-*.jsonl'))
        if len(paths) != 1:
            raise ValueError("EXPECTED_ONE_LEDGER_PER_TASK")
        tasks.append(audit_task(paths[0], spec))
        print(f'Completed offline audit: {spec["task_class"]}/{spec["difficulty"]}', flush=True)
    output = {
        "scope": "privileged_development_diagnostics_only_never_agent_input",
        "limitations": [
            "Oracle uses the generator joint distribution, which agents were not supplied.",
            "Oracle on pooled independent evidence is an upper bound, not an individual agent information set.",
            "Missing planned route is one sufficient route, not proof all other routes fail.",
            "Ledger omits requested/denied tool IDs and full prompts; purchase intentions cannot be reconstructed.",
            "A tool-round stop does not prove additional rounds would improve outcomes.",
        ],
        "episode_stop_counts": dict(Counter(e["stop"] for t in tasks for e in t["episodes"])),
        "tasks": tasks,
    }
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True)+"\n")


if __name__ == "__main__":
    main()
