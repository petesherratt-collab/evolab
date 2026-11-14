from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from evolutionary_lab.evidence import EvidenceLedger, verify_ledger

from collective_lab.causal_generator import CAUSAL_TASK_CLASSES, DIFFICULTIES
from collective_lab.causal_generator_v11 import generate_causal_case_v11
from collective_lab.freeze_v12 import derive_v12_task_seed
from collective_lab.openrouter import Completion
from collective_lab.protocol_v12 import (
    ComputePlanV12,
    staged_evidence_allocation,
    v12_evidence_allocation,
)
from collective_lab.runner_v12 import (
    ConditionTokenGate,
    ComputeBudgetExhausted,
    HarnessV12,
    _proposal_response_format,
)


class _ScriptedClient:
    model = "fake/model"

    def __init__(self, messages: list[dict]) -> None:
        self.messages = list(messages)
        self.max_token_caps: list[int] = []

    def complete(
        self, messages, *, tools=None, response_format=None, max_tokens=900, seed=None
    ) -> Completion:
        self.max_token_caps.append(max_tokens)
        return Completion(
            request_id=f"fake-{len(self.max_token_caps)}",
            model=self.model,
            provider="fake",
            message=self.messages.pop(0),
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
                "cost": 0.0,
            },
        )


class ProposalSchemaCompatibilityTests(unittest.TestCase):
    def test_proposal_schema_uses_provider_supported_subset(self) -> None:
        case = generate_causal_case_v11(20261300, "additive", "easy")
        schema = _proposal_response_format(case.task)
        self.assertNotIn("uniqueItems", json.dumps(schema))


def _tool_call(evidence_ids: list[str], call_id: str) -> dict:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": "buy_evidence",
                    "arguments": json.dumps({"evidence_ids": evidence_ids}),
                },
            }
        ],
    }


def _report(task, cited: list[str]) -> dict:
    probabilities = {candidate: 0.0 for candidate in task.candidates}
    probabilities[task.correct_candidate] = 1.0
    alternative = next(
        candidate for candidate in task.candidates
        if candidate != task.correct_candidate
    )
    return {
        "role": "assistant",
        "content": json.dumps(
            {
                "diagnosis": task.correct_candidate,
                "probabilities": probabilities,
                "cited_evidence": cited,
                "rationale": "test",
                "strongest_alternative": alternative,
                "recommended_verification": [],
            }
        ),
    }


def _proposal(task, priority: list[str]) -> dict:
    return {
        "role": "assistant",
        "content": json.dumps(
            {
                "priority_evidence": priority,
                "contingencies": [],
                "avoid_evidence": [],
                "rationale": "test plan",
            }
        ),
    }


class ProtocolV12Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = {
            (task_class, difficulty): generate_causal_case_v11(
                901, task_class, difficulty
            )
            for task_class in CAUSAL_TASK_CLASSES
            for difficulty in DIFFICULTIES
        }

    def test_staged_allocation_preserves_a_decisive_route_after_scouting(self) -> None:
        for identity, case in self.cases.items():
            with self.subTest(identity=identity):
                allocation = staged_evidence_allocation(
                    case.evidence_budget,
                    minimum_path_costs=case.minimum_path_costs,
                )
                minimum_path = sum(case.minimum_path_costs)
                self.assertEqual(allocation.coordinator_guaranteed_budget, minimum_path)
                self.assertEqual(
                    allocation.scout_ceiling + minimum_path,
                    case.evidence_budget,
                )
                self.assertGreater(allocation.scout_ceiling, 0)
                self.assertEqual(
                    allocation.coordinator_budget_after(allocation.scout_ceiling),
                    minimum_path,
                )

    def test_noncommunicating_conditions_keep_v11_conserved_allocations(self) -> None:
        case = self.cases[("relational", "hard")]
        for condition in (
            "single_agent",
            "independent_vote",
            "independent_synthesizer",
        ):
            allocation = v12_evidence_allocation(
                condition,
                case.evidence_budget,
                task_id=case.task.task_id,
                minimum_path_costs=case.minimum_path_costs,
            )
            self.assertEqual(
                sum(allocation.investigator_budgets)
                + allocation.synthesis_budget,
                case.evidence_budget,
            )

    def test_compute_gate_caps_or_rejects_every_request(self) -> None:
        plan = ComputePlanV12(
            target_tokens=2_000,
            tolerance=0.10,
            prompt_token_overhead=0,
            post_call_safety_margin=0,
        )
        gate = ConditionTokenGate(plan)
        messages = [{"role": "user", "content": "short"}]
        cap, estimate = gate.preflight(
            messages,
            tools=None,
            response_format=None,
            reserve_after=500,
            requested_max=1_400,
        )
        self.assertGreater(estimate, 0)
        self.assertLessEqual(cap, plan.max_completion_tokens)
        gate.used_tokens = plan.upper_bound - 50
        with self.assertRaises(ComputeBudgetExhausted):
            gate.preflight(
                messages,
                tools=None,
                response_format=None,
                reserve_after=0,
                requested_max=1_400,
            )
        overflow_gate = ConditionTokenGate(plan)
        with self.assertRaisesRegex(
            ComputeBudgetExhausted, "CAUSAL_V12_COMPUTE_CEILING_EXCEEDED"
        ):
            overflow_gate.record(
                Completion(
                    request_id="overflow",
                    model="fake/model",
                    provider="fake",
                    message={"role": "assistant", "content": "{}"},
                    usage={"total_tokens": plan.upper_bound + 1},
                )
            )

    def test_default_prompt_estimate_retains_calibrated_safety_margin(self) -> None:
        plan = ComputePlanV12()
        estimate = plan.estimate_prompt_tokens(
            [{"role": "user", "content": "x" * 4_000}]
        )
        self.assertEqual(plan.prompt_characters_per_token, 4.0)
        self.assertGreater(estimate, 1_000)
        self.assertLess(estimate, 1_500)

    def test_v12_seed_derivation_is_deterministic_and_split_specific(self) -> None:
        development = derive_v12_task_seed(
            "master",
            split="development",
            task_class="additive",
            difficulty="easy",
            task_index=0,
        )
        repeated = derive_v12_task_seed(
            "master",
            split="development",
            task_class="additive",
            difficulty="easy",
            task_index=0,
        )
        evaluation = derive_v12_task_seed(
            "master",
            split="evaluation",
            task_class="additive",
            difficulty="easy",
            task_index=0,
        )
        self.assertEqual(development, repeated)
        self.assertNotEqual(development, evaluation)

    def test_staged_collective_uses_one_shared_pool(self) -> None:
        case = self.cases[("additive", "easy")]
        task = case.task
        scout_id = case.core_evidence[0]
        coordinator_ids = list(case.core_evidence[1:])
        messages = [
            _tool_call([scout_id], "scout-buy"),
            _report(task, [scout_id]),
            *[_proposal(task, coordinator_ids) for _ in range(4)],
            _tool_call([scout_id, *coordinator_ids], "coordinator-buy"),
            _report(task, list(case.core_evidence)),
        ]
        plan = ComputePlanV12(target_tokens=0)
        client = _ScriptedClient(messages)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "v12.jsonl"
            harness = HarnessV12(
                client,
                EvidenceLedger(path),
                max_tokens=1_400,
                max_tool_rounds=1,
                compute_plan=plan,
            )
            result = harness.run_condition(
                task,
                "communicating_collective",
                evidence_budget=case.evidence_budget,
                minimum_path_costs=case.minimum_path_costs,
                compute_plan=plan,
            )
            records = [
                json.loads(line)["payload"]
                for line in path.read_text(encoding="utf-8").splitlines()
            ]
            verification = verify_ledger(path)

        acquired = [
            record
            for record in records
            if record.get("kind") == "shared_evidence_acquired"
        ]
        proposals = [
            record
            for record in records
            if record.get("kind") == "causal_v12_acquisition_proposal"
        ]
        self.assertTrue(result.score.accurate)
        self.assertLessEqual(result.evidence_spent, case.evidence_budget)
        self.assertEqual(len(acquired), len(set(case.core_evidence)))
        self.assertEqual(len(proposals), 4)
        self.assertEqual(records[0]["kind"], "causal_v12_condition_plan")
        self.assertEqual(records[-1]["kind"], "condition_complete")
        self.assertTrue(verification["valid"])
        self.assertFalse(client.messages)


if __name__ == "__main__":
    unittest.main()
