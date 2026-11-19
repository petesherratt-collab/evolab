from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from collective_lab.causal_audit_v16 import audit_case, public_diagnostic_ids, public_signature
from collective_lab.causal_generator_v16 import generate_causal_case_v16, sample_world_index
from collective_lab.openrouter import Completion
from collective_lab.protocol_v16 import ComputePlanV16, REASONING_CONDITIONS
from collective_lab.runner_v12 import ComputeBudgetExhausted
from collective_lab.runner_v16 import HarnessV16, score_diagnostics
from collective_lab.core import parse_report
from collective_lab.development_v16 import prepare
from evolutionary_lab.evidence import EvidenceLedger, verify_ledger


class PublicClient:
    """No access to a case, private answer, oracle, or world table."""
    model = "fake/offline"

    def __init__(self, decisions=None):
        self.decisions = iter(decisions) if decisions is not None else None
        self.calls = []

    def complete(self, messages, **kwargs):
        payload = json.loads(messages[-1]["content"])
        self.calls.append(payload)
        if kwargs["response_format"]["json_schema"]["name"] == "acquisition_decision":
            if self.decisions is not None:
                result = next(self.decisions)
                result = result(payload) if callable(result) else result
            else:
                ids = [eid for eid in public_diagnostic_ids(payload["task"], payload["evidence_packet"])
                       if eid not in payload["evidence_packet"]]
                result = decision("buy" if ids else "finish", ids)
        else:
            candidates = payload["task"]["candidates"]
            result = {"diagnosis": candidates[0], "probabilities": {c: .2 for c in candidates},
                      "cited_evidence": list(payload["evidence_packet"]), "rationale": "Offline test.",
                      "strongest_alternative": candidates[1], "recommended_verification": []}
        return Completion(str(len(self.calls)), self.model, "fake",
                          {"role": "assistant", "content": json.dumps(result)},
                          {"total_tokens": 100, "cost": 0}, "stop")


def decision(action="finish", ids=None, *, remaining=None, accept=False):
    return {"action": action, "evidence_ids": ids or [], "remaining_bundle": remaining or [],
            "remaining_uncertainty": "Shared regime uncertainty remains.",
            "reason": "Exercise the explicit decision contract.", "accept_early_stop": accept}


class V16Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {kind: generate_causal_case_v16(1600, kind, "hard", world_seed=11600)
                     for kind in ("additive", "relational", "coordination_trap")}

    def run_harness(self, case, condition, client=None, plan=None):
        client = client or PublicClient()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"ledger.jsonl"
            result = HarnessV16(client, EvidenceLedger(path),
                                compute_plan=plan or ComputePlanV16(target_tokens=0)).run_condition(case, condition)
            self.assertTrue(verify_ledger(path)["valid"])
            rows = [json.loads(line)["payload"] for line in path.read_text().splitlines()]
        return result, client.calls, rows

    def test_all_possible_packets_decode_and_have_feasible_routes(self):
        for kind, case in self.cases.items():
            with self.subTest(kind=kind):
                result = audit_case(case)
                self.assertTrue(result["passed"], result["checks"])

    def test_sampler_includes_aliases_and_all_nuisance_states(self):
        task = self.cases["coordination_trap"].causal_task
        sampled = [task.worlds[sample_world_index(task, seed)] for seed in range(2000)]
        self.assertTrue(any(w.fault != w.nuisance_mapping()["observation_regime"] for w in sampled))
        for key in ("source_stale", "calibration_inverted", "adaptive_branch"):
            self.assertEqual({w.nuisance_mapping()[key] for w in sampled}, {0, 1})
        self.assertEqual({w.fault for w in sampled}, set(task.candidates))
        self.assertEqual(sample_world_index(task, 3), sample_world_index(task, 3))

    def test_packet_membership_does_not_depend_on_selected_world(self):
        other = generate_causal_case_v16(1600, "relational", "hard", world_seed=123456)
        case = self.cases["relational"]
        self.assertEqual(case.packet_ids, other.packet_ids)
        self.assertEqual(case.causal_task.worlds, other.causal_task.worlds)
        self.assertEqual(case.task.public()["evidence_catalogue"], other.task.public()["evidence_catalogue"])
        self.assertNotIn("world_seed", json.dumps(other.task.public()))
        self.assertNotIn("correct_candidate", json.dumps(other.task.public()))

    def test_four_reasoning_conditions_have_identical_evidence(self):
        case = self.cases["relational"]
        for condition in REASONING_CONDITIONS:
            with self.subTest(condition=condition):
                result, calls, _ = self.run_harness(case, condition)
                self.assertTrue(result["eligible"])
                self.assertEqual(result["evidence_spent"], 0)
                self.assertTrue(all(c["evidence_packet"] == case.packet() for c in calls))
                self.assertEqual(len(calls), 4 if condition == "independent_vote" else 5)
                if condition in {"independent_vote", "independent_synthesizer"}:
                    self.assertTrue(all(c["history"] == [] for c in calls[:4]))
                else:
                    self.assertEqual([len(c["history"]) for c in calls[:4]], [0, 1, 2, 3])

    def test_shared_wallet_public_planner_completes_every_class(self):
        for kind, case in self.cases.items():
            for condition in ("acquisition_single", "acquisition_collective"):
                with self.subTest(kind=kind, condition=condition):
                    result, calls, rows = self.run_harness(case, condition)
                    self.assertTrue(result["eligible"])
                    packet = calls[-1]["evidence_packet"]
                    self.assertEqual(public_signature(case.task.public(), packet),
                                     case.causal_task.worlds[case.causal_task.true_world_index].nuisance_mapping()["observation_regime"])
                    self.assertLessEqual(result["evidence_spent"], case.acquisition_budget)
                    self.assertEqual(result["stop_reason"], "explicit_finish")
                    self.assertEqual(sum(r["kind"] == "causal_v16_acquisition_decision" for r in rows), 3)

    def test_affordable_unconfirmed_finish_leaves_purchase_opportunity(self):
        case = self.cases["additive"]
        router = public_diagnostic_ids(case.task.public(), {})
        client = PublicClient([decision(remaining=router), decision("buy", router), decision()])
        result, calls, rows = self.run_harness(case, "acquisition_collective", client)
        statuses = [r["status"] for r in rows if r["kind"] == "causal_v16_acquisition_decision"]
        self.assertEqual(statuses, ["affordable_bundle_requires_buy_or_explicit_stop", "purchased", "explicit_finish"])
        self.assertEqual(result["evidence_ids"], router)
        self.assertEqual(len(calls), 4)

    def test_deliberate_early_finish_is_recorded(self):
        case = self.cases["additive"]
        router = public_diagnostic_ids(case.task.public(), {})
        result, _, _ = self.run_harness(case, "acquisition_single",
                                        PublicClient([decision(remaining=router, accept=True)]))
        self.assertEqual(result["stop_reason"], "explicit_early_stop")
        self.assertEqual(result["evidence_spent"], 0)

    def test_invalid_implicit_report_does_not_end_acquisition(self):
        result, calls, rows = self.run_harness(self.cases["additive"], "acquisition_single",
                                              PublicClient([{"diagnosis": "premature"}, decision()]))
        self.assertEqual(len(calls), 3)
        self.assertFalse(result["eligible"])
        self.assertTrue(any(r.get("status") == "invalid_decision" for r in rows))

    def test_overbudget_bundle_is_atomic_and_duplicates_are_free(self):
        case = self.cases["additive"]
        router = public_diagnostic_ids(case.task.public(), {})
        all_ids = list(case.task.evidence_map())
        client = PublicClient([decision("buy", all_ids), decision("buy", router),
                               decision("buy", router), decision()])
        result, _, rows = self.run_harness(case, "acquisition_single", client)
        self.assertEqual(result["evidence_spent"], 1)
        statuses = [r["status"] for r in rows if r["kind"] == "causal_v16_acquisition_decision"]
        self.assertEqual(statuses, ["over_budget_no_purchase", "purchased", "already_owned_no_charge", "explicit_finish"])

    def test_unconfirmed_finish_cannot_loop_indefinitely(self):
        case = self.cases["additive"]
        router = public_diagnostic_ids(case.task.public(), {})
        result, calls, _ = self.run_harness(case, "acquisition_single",
                                           PublicClient([decision(remaining=router)]*6))
        self.assertEqual(result["stop_reason"], "decision_limit")
        self.assertEqual(len(calls), 7)

    def test_tied_correct_label_does_not_count_as_unique_solution(self):
        case = self.cases["additive"]
        report = parse_report({"diagnosis": case.task.correct_candidate,
                               "probabilities": {c: .2 for c in case.task.candidates}}, case.task)
        metrics = score_diagnostics(case, report, case.packet_ids)
        self.assertTrue(metrics["accurate"])
        self.assertTrue(metrics["tied_lead"])
        self.assertFalse(metrics["unique_correct_leader"])

    def test_calibrated_report_beats_overconfidence_in_expected_score(self):
        case = self.cases["additive"]
        signature = public_signature(case.task.public(), case.packet())
        scores = []
        for p in (case.faithful_probability, 1.0):
            report = parse_report({"diagnosis": signature, "probabilities": {
                c: p if c == signature else (1-p)/4 for c in case.task.candidates}}, case.task)
            scores.append(score_diagnostics(case, report, case.packet_ids)["expected_brier_given_reference_packet"])
        self.assertLess(scores[0], scores[1])

    def test_compute_limit_prevents_provider_call(self):
        client = PublicClient()
        with self.assertRaises(ComputeBudgetExhausted):
            self.run_harness(self.cases["additive"], "single_agent", client,
                             ComputePlanV16(target_tokens=100))
        self.assertEqual(client.calls, [])

    def test_missing_usage_aborts_instead_of_treating_call_as_free(self):
        class MissingUsage(PublicClient):
            def complete(self, *args, **kwargs):
                return replace(super().complete(*args, **kwargs), usage={})
        with self.assertRaisesRegex(ValueError, "USAGE_MISSING"):
            self.run_harness(self.cases["additive"], "single_agent", MissingUsage())

    def test_preparation_rejects_incomplete_or_stale_audit_before_signing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"audit.json"
            path.write_text(json.dumps({"protocol_version": "causal-1.6-dev", "passed": True,
                                        "cases": [], "source_sha256": {}}))
            with self.assertRaisesRegex(ValueError, "FRESH_COMPLETE_AUDIT"):
                prepare(audit_path=path, output_dir=Path(directory)/"out",
                        private_key="unused", public_key="unused")
            self.assertFalse((Path(directory)/"out").exists())

    def test_compute_plan_has_a_ceiling_but_no_padding_floor(self):
        self.assertEqual(ComputePlanV16().lower_bound, 0)
        self.assertEqual(ComputePlanV16().upper_bound, 30000)

    def test_unsupported_constituent_makes_vote_ineligible(self):
        class UnsupportedCitation(PublicClient):
            def complete(self, *args, **kwargs):
                completion = super().complete(*args, **kwargs)
                value = json.loads(completion.message["content"])
                if len(self.calls) == 1:
                    value["cited_evidence"] = ["UNSEEN"]
                return replace(completion, message={"role": "assistant", "content": json.dumps(value)})
        result, _, _ = self.run_harness(self.cases["additive"], "independent_vote", UnsupportedCitation())
        self.assertFalse(result["eligible"])
        self.assertTrue(any("UNSUPPORTED_CITATION" in error for error in result["errors"]))
