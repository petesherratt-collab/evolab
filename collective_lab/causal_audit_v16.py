"""Offline population, public interpretation and resource-feasibility checks."""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import defaultdict
import json
from pathlib import Path
import re

from .causal_audit_v15 import disclosed_candidates
from .causal_generator import CAUSAL_TASK_CLASSES, DIFFICULTIES
from .causal_generator_v16 import VERSION, generate_causal_case_v16, sample_world_index, world_weight_boundaries
from .oracle import ExactOracle
from .protocol_v16 import source_hashes


def public_diagnostic_ids(public_task, acquired):
    """Reference planner for OFFLINE checks, using only public catalogue/results."""
    catalogue = public_task["evidence_catalogue"]
    routers = [e["evidence_id"] for e in catalogue if "Routing check selecting" in e["description"]]
    if routers and routers[0] not in acquired:
        return routers
    branch = None
    if routers:
        match = re.search(r"branch ([AB]) is active", acquired[routers[0]])
        if not match:
            raise ValueError("V16_PUBLIC_BRANCH_MISSING")
        branch = match[1]
    ids = []
    for item in catalogue:
        description = item["description"]
        if branch and f"Branch {'B' if branch == 'A' else 'A'} probe" in description:
            continue
        if ("Independent diagnostic channel" in description or
                re.search(r"(?:Reference|Trace) member of diagnostic pair [123](?:\D|$)", description) or
                "Physical measurement for signature bit" in description or
                "Read the polarity calibration" in description):
            ids.append(item["evidence_id"])
    return ids


def public_signature(public_task, packet):
    ids = public_diagnostic_ids(public_task, packet)
    catalogue = {e["evidence_id"]: e for e in public_task["evidence_catalogue"]}
    purchased = {eid: f"Interpretation: {catalogue[eid]['description']}. {packet[eid]}" for eid in ids}
    inferred = disclosed_candidates(public_task["candidates"], public_task["task_class"], purchased)
    if len(inferred) != 1:
        raise ValueError("V16_PUBLIC_SIGNATURE_UNRESOLVED")
    return next(iter(inferred))


def audit_case(case, *, draws=2000):
    task = case.causal_task
    public = case.task.public()
    indexes = task.evidence_index()
    packet_indexes = [indexes[eid] for eid in case.packet_ids]
    groups = defaultdict(list)
    boundaries = world_weight_boundaries(task)
    previous = 0
    for i, world in enumerate(task.worlds):
        # Check both ends of every interval, including all off-by-one boundaries.
        if bisect_right(boundaries, previous) != i or bisect_right(boundaries, boundaries[i]-1) != i:
            raise ValueError("V16_SAMPLER_BOUNDARY_INVALID")
        previous = boundaries[i]
        groups[tuple(world.outcomes[j] for j in packet_indexes)].append(world)
    all_decodable = True
    all_calibrated = True
    all_affordable = True
    for outcomes, worlds in groups.items():
        packet = {eid: task.evidence[indexes[eid]].outcome_text[outcome]
                  for eid, outcome in zip(case.packet_ids, outcomes)}
        signature = public_signature(public, packet)
        all_decodable &= all(w.nuisance_mapping()["observation_regime"] == signature for w in worlds)
        total = sum(w.weight for w in worlds)
        posterior = {c: sum(w.weight for w in worlds if w.fault == c)/total for c in task.candidates}
        all_calibrated &= all(abs(posterior[c] - (case.faithful_probability if c == signature else
                                                (1-case.faithful_probability)/4)) < 1e-12
                              for c in task.candidates)
        route = set(public_diagnostic_ids(public, packet))
        route.update(e["evidence_id"] for e in public["evidence_catalogue"]
                     if "Routing check selecting" in e["description"])
        all_affordable &= sum(task.evidence[indexes[eid]].cost for eid in route) <= case.acquisition_budget
    population_faithful = sum(w.weight for w in task.worlds
                              if w.fault == w.nuisance_mapping()["observation_regime"])/boundaries[-1]
    draws_faithful = sum(
        task.worlds[i].fault == task.worlds[i].nuisance_mapping()["observation_regime"]
        for i in (sample_world_index(task, seed) for seed in range(draws))
    )/draws
    oracle = ExactOracle(task)
    actual_signature = public_signature(public, case.packet())
    checks = {
        "every_possible_packet_publicly_decodable": bool(all_decodable),
        "every_packet_posterior_matches_disclosed_reliability": bool(all_calibrated),
        "every_branch_has_affordable_complete_route": bool(all_affordable),
        "full_world_population_has_declared_faithful_mass": abs(population_faithful-case.faithful_probability)<1e-12,
        "sampler_smoke_frequency_within_004": abs(draws_faithful-population_faithful)<.04,
        "reference_packet_equals_full_catalogue_posterior": all(
            abs(oracle.observed_posterior(case.packet_ids)[c]-oracle.observed_posterior(indexes)[c])<1e-12
            for c in task.candidates),
        "budget_does_not_buy_catalogue": case.acquisition_budget < sum(e.cost for e in task.evidence),
        "truth_matches_selected_world": task.correct_candidate == task.worlds[task.true_world_index].fault,
    }
    if task.task_class == "additive":
        diagnostic = [e.evidence_id for e in task.evidence if "Independent diagnostic channel" in e.description]
        checks["additive_marginal_information"] = max(oracle.information_gain((eid,)) for eid in diagnostic)>0
    if task.task_class == "relational":
        pair = [e.evidence_id for e in task.evidence if "member of diagnostic pair 1" in e.description]
        checks["relational_zero_marginals_positive_joint"] = (
            all(abs(oracle.information_gain((eid,)))<1e-12 for eid in pair) and oracle.information_gain(pair)>0)
    if task.task_class == "coordination_trap":
        checks["trap_population_includes_current_and_stale"] = {
            w.nuisance_mapping()["source_stale"] for w in task.worlds} == {False, True}
    return {"task_id": task.task_id, "task_class": task.task_class, "difficulty": task.intended_difficulty,
            "fingerprint": task.fingerprint(), "worlds": len(task.worlds), "distinct_packets": len(groups),
            "population_faithful_probability": population_faithful, "sampled_faithful_fraction": draws_faithful,
            "selected_world_faithful": task.correct_candidate == actual_signature,
            "packet_ids": list(case.packet_ids), "acquisition_budget": case.acquisition_budget,
            "checks": checks, "passed": all(checks.values())}


def run_audit(seeds=(1600, 1601)):
    cases = []
    for seed in seeds:
        for task_class in CAUSAL_TASK_CLASSES:
            for difficulty in DIFFICULTIES:
                case = generate_causal_case_v16(seed, task_class, difficulty, world_seed=seed+10000)
                cases.append(audit_case(case))
    return {"protocol_version": VERSION, "scope": "offline_population_and_public_contract",
            "paid_requests": 0, "seeds": list(seeds), "cases": cases,
            "source_sha256": source_hashes(),
            "passed": bool(cases) and all(row["passed"] for row in cases)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = run_audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    print(json.dumps({"passed": result["passed"], "cases": len(result["cases"]), "paid_requests": 0}))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
