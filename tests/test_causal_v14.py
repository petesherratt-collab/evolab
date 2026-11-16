import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evolutionary_lab.evidence import EvidenceLedger
from collective_lab.causal_generator_v13 import generate_causal_case_v13
from collective_lab.core import parse_report
from collective_lab.openrouter import Completion
from collective_lab.protocol_v14 import ComputePlanV14
from collective_lab.runner_v12 import ConditionTokenGate, ComputeBudgetExhausted, SharedEvidencePool
from collective_lab.runner_v13 import HarnessV13
from collective_lab.runner_v14 import HarnessV14


class Client:
    model = "fake/model"

    def __init__(self):
        self.calls = []
        self.content = "{}"

    def complete(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return Completion("test", self.model, "fake", {"content": self.content},
                          {"total_tokens": 200, "cost": 0.01}, "stop")


class V14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.task = generate_causal_case_v13(500, "additive", "easy").task

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "ledger.jsonl"
        self.client = Client()
        self.plan = ComputePlanV14(target_tokens=10000, tolerance=0.1)
        self.harness = HarnessV14(self.client, EvidenceLedger(self.path),
                                 max_tokens=1800, compute_plan=self.plan)
        self.harness._token_gate = ConditionTokenGate(self.plan)

    def report(self):
        return parse_report({
            "diagnosis": self.task.candidates[0],
            "probabilities": {c: 0.2 for c in self.task.candidates},
            "cited_evidence": [], "rationale": "Uncertain.",
        }, self.task)

    def test_uniform_envelope(self):
        plan = ComputePlanV14()
        self.assertEqual((plan.lower_bound, plan.upper_bound), (25000, 30000))
        self.assertEqual(plan.minimum_completion_tokens, 512)

    def test_fallback_preserves_later_roles_and_restores_reserve(self):
        self.harness._token_gate.used_tokens = 6000
        self.harness._future_reserve = 2000
        self.harness._reserve_after = 5200
        self.harness._complete([{"role": "user", "content": "finish"}],
                               tools=[{"type": "function"}], context={})
        self.assertEqual(len(self.client.calls), 1)
        self.assertIsNone(self.client.calls[0][1]["tools"])
        rows = [json.loads(line)["payload"] for line in self.path.read_text().splitlines()]
        self.assertEqual(rows[-1]["compute_gate"]["reserve_after"], 2000)
        self.assertEqual(self.harness._reserve_after, 5200)

    def test_request_limit_does_not_trigger_retry(self):
        self.harness._token_gate.requests = self.plan.max_condition_requests
        with self.assertRaisesRegex(ComputeBudgetExhausted, "REQUEST_LIMIT"):
            self.harness._complete([], tools=[{}], context={})
        self.assertEqual(self.client.calls, [])

    def test_recovery_charges_call_and_keeps_original_error(self):
        self.client.content = json.dumps(self.report().mapping())
        calls, errors = [], ["REPORT_MISSING"]
        recovered = self.harness._recover_report(
            self.task, None, set(), calls, errors, condition="single_agent", agent_id="single")
        self.assertIsNotNone(recovered)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].usage["cost"], 0.01)
        self.assertIn("REPORT_MISSING", errors)
        self.assertEqual(self.harness._token_gate.used_tokens, 200)
        payload = json.loads(self.client.calls[0][0][-1]["content"])
        self.assertEqual(payload["acquired_evidence"], [])
        self.assertNotIn("correct_candidate", payload["task"])

    def test_failed_recovery_stops_after_one_call(self):
        calls, errors = [], []
        result = self.harness._recover_report(
            self.task, None, set(), calls, errors, condition="single_agent", agent_id="single")
        self.assertIsNone(result)
        self.assertEqual(len(calls), 1)
        self.assertTrue(errors)

    def test_valid_report_needs_no_recovery(self):
        report = self.report()
        self.assertIs(self.harness._recover_report(
            self.task, report, set(), [], [], condition="single_agent", agent_id="single"), report)
        self.assertEqual(self.client.calls, [])

    def test_coordinator_receives_scout_without_new_evidence(self):
        report = self.report()
        pool = SharedEvidencePool(10, set())
        with patch.object(HarnessV13, "_shared_episode", return_value=(report, [], [])) as episode:
            self.harness._shared_episode(self.task, pool=pool, stage_ceiling=2,
                                        role="scout", agent_id="shared-scout")
            self.harness._shared_episode(self.task, pool=pool, stage_ceiling=10,
                                        role="coordinate", agent_id="shared-coordinator",
                                        extra_context="[]")
            context = json.loads(episode.call_args.kwargs["extra_context"])
            self.assertEqual(context["scout_report"], report.mapping())
            self.assertEqual(pool.acquired, set())

    def test_recovery_cannot_spend_future_reserve(self):
        self.harness._token_gate.used_tokens = 10000
        self.harness._reserve_after = 3200
        result = self.harness._recover_report(
            self.task, None, set(), [], [], condition="single_agent", agent_id="single")
        self.assertIsNone(result)
        self.assertEqual(self.client.calls, [])
