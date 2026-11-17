import json
import tempfile
import unittest
from pathlib import Path

from collective_lab.causal_audit_v15 import disclosed_candidates
from collective_lab.causal_generator_v13 import generate_causal_case_v13
from collective_lab.causal_generator_v15 import generate_causal_case_v15
from collective_lab.openrouter import Completion
from collective_lab.protocol_v15 import ComputePlanV15, acquisition_schedule
from collective_lab.runner_v15 import HarnessV15
from evolutionary_lab.evidence import EvidenceLedger, verify_ledger


class BatchClient:
    model = "fake/offline"

    def __init__(self, task, *, denied=False):
        self.task = task
        self.calls = []
        self.denied = denied

    def complete(self, messages, *, tools=None, **kwargs):
        self.calls.append((messages, tools))
        if len(self.calls) == 1:
            public = json.loads(messages[-1]["content"])["task"]
            ids = [e["evidence_id"] for e in public["evidence_catalogue"] if "Topology registry" in e["description"]]
        elif len(self.calls) == 2:
            result = json.loads(messages[-1]["content"])["results"][0]["result"]
            registry = json.loads(result.split("Interpretation registry: ", 1)[1])
            ids = [item["evidence_id"] for item in registry["active_items"]]
            if self.denied:
                ids = ["UNKNOWN", *ids]
        else:
            report = {"diagnosis": self.task.candidates[0],
                      "probabilities": {c: .2 for c in self.task.candidates},
                      "cited_evidence": [], "rationale": "Offline."}
            return Completion("report", self.model, "fake", {"role": "assistant", "content": json.dumps(report)},
                              {"total_tokens": 100, "cost": 0}, "stop")
        message = {"role": "assistant", "content": None, "tool_calls": [{
            "id": f"call-{len(self.calls)}", "type": "function",
            "function": {"name": "buy_evidence", "arguments": json.dumps({"evidence_ids": ids})},
        }]}
        return Completion(f"request-{len(self.calls)}", self.model, "fake", message,
                          {"total_tokens": 100, "cost": 0}, "tool_calls")


class V15Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = generate_causal_case_v15(500, "additive", "moderate")

    def test_generator_preserves_worlds_costs_and_hidden_catalogue(self):
        old = generate_causal_case_v13(500, "additive", "moderate")
        self.assertEqual(self.case.causal_task.worlds, old.causal_task.worlds)
        self.assertEqual(self.case.minimum_path_costs, old.minimum_path_costs)
        self.assertEqual(self.case.evidence_budget, old.evidence_budget)
        self.assertEqual([e.description for e in self.case.task.evidence], [e.description for e in old.task.evidence])
        self.assertNotIn("correct_candidate", self.case.task.public())
        self.assertIn("reliability regime", self.case.task.briefing)

    def test_two_round_public_router_then_batch_completes_route(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"ledger.jsonl"
            client = BatchClient(self.case.task)
            harness = HarnessV15(client, EvidenceLedger(path), max_tokens=1800,
                                max_tool_rounds=2, compute_plan=ComputePlanV15(target_tokens=0))
            # Normal run activates the budget gate and exercises the actual tool executor.
            result = harness.run_condition(self.case.task, "single_agent",
                evidence_budget=self.case.evidence_budget, minimum_path_costs=self.case.minimum_path_costs,
                compute_plan=ComputePlanV15(target_tokens=0))
            self.assertTrue(set(self.case.core_evidence) <= set(result.acquired_evidence))
            self.assertEqual(len(client.calls), 3)
            self.assertEqual(result.evidence_spent, sum(self.case.minimum_path_costs))
            self.assertTrue(verify_ledger(path)["valid"])
            self.assertIn("1 remaining", client.calls[1][0][0]["content"])
            self.assertNotIn("instead of intersecting marginal", client.calls[1][0][0]["content"])
            rows=[json.loads(s)["payload"] for s in path.read_text().splitlines()]
            self.assertEqual(sum(r["kind"]=="causal_v15_tool_result" for r in rows), 2)
            self.assertEqual([r for r in rows if r["kind"]=="causal_v15_call_observation"][-1]["stop_reason"], "configured_tool_round_limit")

    def test_denied_requests_are_recorded_without_charging(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"ledger.jsonl"; client=BatchClient(self.case.task, denied=True)
            plan=ComputePlanV15(target_tokens=0)
            harness=HarnessV15(client,EvidenceLedger(path),max_tool_rounds=2,compute_plan=plan)
            result=harness.run_condition(self.case.task,"single_agent",evidence_budget=1,
                minimum_path_costs=(1,),compute_plan=plan)
            self.assertEqual(result.evidence_spent, 1)
            rows=[json.loads(s)["payload"] for s in path.read_text().splitlines()]
            statuses=[x["status"] for r in rows if r["kind"]=="causal_v15_tool_result" for x in r["result"].get("results",[])]
            self.assertIn("unknown",statuses)
            self.assertIn("over_budget",statuses)

    def test_schedule_does_not_offer_tools_on_reviews(self):
        self.assertIn("0 remaining", acquisition_schedule(2, 0, False))
        self.assertIn("last acquisition round", acquisition_schedule(2, 1, True))
        self.assertEqual((ComputePlanV15().lower_bound,ComputePlanV15().upper_bound),(25000,30000))

    def test_pair_metadata_is_required_by_public_replay(self):
        purchased={}
        for pair in range(1,4):
            purchased[f'r{pair}']=f'Interpretation: Reference member of diagnostic pair {pair}. Reference phase: 1.'
            purchased[f't{pair}']=f'Interpretation: Trace member of diagnostic pair {pair}. Trace phase: 0. XOR 0 maps to [b]; XOR 1 maps to [a].'
        self.assertEqual(disclosed_candidates(('a','b'),'relational',purchased),{'a'})
        with self.assertRaisesRegex(ValueError,'PAIR_IDENTIFIERS'):
            disclosed_candidates(('a','b'),'relational',{'r':'Reference phase: 1.','t':'Trace phase: 0.'})
