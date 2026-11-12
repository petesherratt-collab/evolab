from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from evolutionary_lab.evidence import EvidenceLedger, verify_ledger

from collective_lab.adaptive_v11 import adaptive_choice_metrics
from collective_lab.causal_generator import CAUSAL_TASK_CLASSES, DIFFICULTIES
from collective_lab.causal_generator_v11 import (
    CAUSAL_GENERATOR_V11_VERSION,
    faithful_regime_probability,
    generate_causal_case_v11,
)
from collective_lab.freeze_v11 import derive_v11_task_seed
from collective_lab.oracle import ExactOracle
from collective_lab.openrouter import Completion
from collective_lab.protocol_v11 import (
    ComputePlan,
    collective_revision_order,
    evidence_allocation,
    permitted_collective_revisions,
)
from collective_lab.runner_v11 import HarnessV11, v11_condition_plan


EXPECTED_COSTS = {
    "additive": {"easy": 3, "moderate": 9, "hard": 25},
    "relational": {"easy": 6, "moderate": 18, "hard": 49},
    "coordination_trap": {"easy": 4, "moderate": 12, "hard": 18},
}
EXPECTED_BUDGETS = {
    "additive": {"easy": 5, "moderate": 12, "hard": 29},
    "relational": {"easy": 8, "moderate": 21, "hard": 53},
    "coordination_trap": {"easy": 6, "moderate": 15, "hard": 22},
}


class _FakeClient:
    model = "fake/model"

    def __init__(self, messages: list[dict]) -> None:
        self.messages = list(messages)

    def complete(
        self, messages, *, tools=None, response_format=None, max_tokens=900, seed=None
    ) -> Completion:
        return Completion(
            request_id=f"fake-{len(self.messages)}",
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


class CausalGeneratorV11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = {
            (task_class, difficulty): generate_causal_case_v11(
                501, task_class, difficulty
            )
            for task_class in CAUSAL_TASK_CLASSES
            for difficulty in DIFFICULTIES
        }

    def test_mechanical_costs_and_scarce_budgets(self) -> None:
        for (task_class, difficulty), case in self.cases.items():
            with self.subTest(task_class=task_class, difficulty=difficulty):
                self.assertEqual(
                    case.metrics.minimum_sufficient_cost,
                    EXPECTED_COSTS[task_class][difficulty],
                )
                self.assertEqual(
                    case.evidence_budget,
                    EXPECTED_BUDGETS[task_class][difficulty],
                )
                self.assertEqual(
                    sum(case.minimum_path_costs),
                    case.metrics.minimum_sufficient_cost,
                )
                self.assertLess(
                    case.evidence_budget,
                    sum(item.cost for item in case.causal_task.evidence),
                )

    def test_posterior_ceiling_is_calibrated_and_non_degenerate(self) -> None:
        ceilings = []
        for difficulty in DIFFICULTIES:
            case = self.cases[("additive", difficulty)]
            ceilings.append(case.faithful_regime_probability)
            self.assertAlmostEqual(
                case.metrics.observed_full_posterior,
                faithful_regime_probability(difficulty),
            )
            self.assertGreater(
                case.metrics.observed_full_posterior,
                case.sufficiency_threshold,
            )
            self.assertLess(case.metrics.observed_full_posterior, 0.90)
        self.assertGreater(ceilings[0], ceilings[1])
        self.assertGreater(ceilings[1], ceilings[2])

    def test_full_evidence_uniquely_favors_true_fault(self) -> None:
        for identity, case in self.cases.items():
            with self.subTest(identity=identity):
                oracle = ExactOracle(case.causal_task)
                posterior = oracle.observed_posterior(
                    item.evidence_id for item in case.causal_task.evidence
                )
                ordered = sorted(posterior, key=posterior.get, reverse=True)
                self.assertEqual(ordered[0], case.causal_task.correct_candidate)
                self.assertGreater(posterior[ordered[0]], posterior[ordered[1]])

    def test_prior_remains_balanced(self) -> None:
        for identity, case in self.cases.items():
            with self.subTest(identity=identity):
                masses = {
                    candidate: sum(
                        world.weight
                        for world in case.causal_task.worlds
                        if world.fault == candidate
                    )
                    for candidate in case.causal_task.candidates
                }
                self.assertAlmostEqual(max(masses.values()), min(masses.values()))

    def test_class_mechanics_survive_uncertainty_layer(self) -> None:
        additive = self.cases[("additive", "moderate")]
        self.assertGreater(additive.metrics.maximum_single_information_gain, 0.0)

        relational = self.cases[("relational", "moderate")]
        oracle = ExactOracle(relational.causal_task)
        pair = relational.core_evidence[:2]
        self.assertAlmostEqual(oracle.information_gain((pair[0],)), 0.0)
        self.assertAlmostEqual(oracle.information_gain((pair[1],)), 0.0)
        self.assertGreater(oracle.synergy(pair), 0.0)

        trap = self.cases[("coordination_trap", "moderate")]
        self.assertEqual(trap.metrics.cheap_distractor, trap.distractor)
        self.assertGreater(
            trap.metrics.cheap_distractor_posterior,
            trap.metrics.cheap_correct_posterior,
        )

    def test_observation_regime_is_explicit_in_graph(self) -> None:
        for identity, case in self.cases.items():
            with self.subTest(identity=identity):
                task = case.causal_task
                node = next(
                    item for item in task.nodes if item.node_id == "observation_regime"
                )
                self.assertEqual(node.kind, "latent")
                self.assertEqual(node.parents, ("fault",))
                self.assertTrue(
                    all(
                        "observation_regime" in item.parents
                        for item in task.evidence
                    )
                )

    def test_hard_tasks_require_adaptive_branch_choice(self) -> None:
        for task_class in CAUSAL_TASK_CLASSES:
            case = self.cases[(task_class, "hard")]
            with self.subTest(task_class=task_class):
                self.assertIsNotNone(case.adaptive_branch)
                metrics = adaptive_choice_metrics(
                    case.causal_task, case.adaptive_branch
                )
                self.assertTrue(metrics.passed, metrics.mapping())
                self.assertGreaterEqual(metrics.adaptive_gain_bits, 0.01)
                self.assertEqual(len(set(dict(metrics.selected_followups).values())), 2)
        for task_class in CAUSAL_TASK_CLASSES:
            self.assertIsNone(self.cases[(task_class, "easy")].adaptive_branch)
            self.assertIsNone(self.cases[(task_class, "moderate")].adaptive_branch)

    def test_generation_is_deterministic_and_versioned(self) -> None:
        first = generate_causal_case_v11(812, "coordination_trap", "hard")
        second = generate_causal_case_v11(812, "coordination_trap", "hard")
        self.assertEqual(first.causal_task.fingerprint(), second.causal_task.fingerprint())
        self.assertEqual(first.causal_task.generator_version, CAUSAL_GENERATOR_V11_VERSION)
        self.assertTrue(first.causal_task.task_id.startswith("causal-v11-"))

    def test_v11_seed_derivation_is_split_specific(self) -> None:
        development = derive_v11_task_seed(
            "master",
            split="development",
            task_class="additive",
            difficulty="easy",
            task_index=0,
        )
        repeated = derive_v11_task_seed(
            "master",
            split="development",
            task_class="additive",
            difficulty="easy",
            task_index=0,
        )
        evaluation = derive_v11_task_seed(
            "master",
            split="evaluation",
            task_class="additive",
            difficulty="easy",
            task_index=0,
        )
        self.assertEqual(development, repeated)
        self.assertNotEqual(development, evaluation)

    def test_evidence_allocation_conserves_every_condition_budget(self) -> None:
        task_id = "causal-v11-relational-hard-812"
        path_costs = (8, 8, 8, 8, 8, 1, 8)
        for condition in (
            "single_agent",
            "independent_vote",
            "independent_synthesizer",
            "communicating_collective",
        ):
            with self.subTest(condition=condition):
                allocation = evidence_allocation(
                    condition,
                    53,
                    task_id=task_id,
                    minimum_path_costs=path_costs,
                )
                self.assertEqual(
                    sum(allocation.investigator_budgets)
                    + allocation.synthesis_budget,
                    53,
                )
        single = evidence_allocation(
            "single_agent", 53, task_id=task_id, minimum_path_costs=path_costs
        )
        vote = evidence_allocation(
            "independent_vote", 53, task_id=task_id, minimum_path_costs=path_costs
        )
        collective = evidence_allocation(
            "communicating_collective",
            53,
            task_id=task_id,
            minimum_path_costs=path_costs,
        )
        self.assertEqual(single.investigator_budgets, (53,))
        self.assertEqual(len(vote.investigator_budgets), 4)
        self.assertEqual(sorted(vote.investigator_budgets), [9, 10, 17, 17])
        self.assertEqual(sorted(collective.investigator_budgets), [8, 8, 9, 16])
        self.assertEqual(collective.synthesis_budget, 12)

    def test_budget_remainder_rotation_is_deterministic(self) -> None:
        first = evidence_allocation(
            "independent_vote",
            21,
            task_id="causal-v11-trap-hard-1",
            minimum_path_costs=(8, 3, 3, 3),
        )
        second = evidence_allocation(
            "independent_vote",
            21,
            task_id="causal-v11-trap-hard-1",
            minimum_path_costs=(8, 3, 3, 3),
        )
        self.assertEqual(first, second)
        self.assertEqual(sorted(first.investigator_budgets), [4, 4, 4, 9])

    def test_collective_revision_plan_preserves_synthesis_reserve(self) -> None:
        plan = ComputePlan()
        task_id = "causal-v11-relational-hard-3019886420956520846"
        order = collective_revision_order(task_id)
        selected = permitted_collective_revisions(
            task_id,
            (18_754, 20_226, 21_689, 23_153),
            plan=plan,
        )
        self.assertEqual(selected, order[:2])
        self.assertTrue(plan.permits_collective_revision(20_226))
        self.assertFalse(plan.permits_collective_revision(21_689))
        self.assertEqual(plan.upper_bound, 27_500)

    def test_v11_condition_plan_is_path_feasible_and_serializable(self) -> None:
        case = self.cases[("relational", "hard")]
        for condition in (
            "single_agent",
            "independent_vote",
            "independent_synthesizer",
            "communicating_collective",
        ):
            with self.subTest(condition=condition):
                plan = v11_condition_plan(
                    case.task,
                    condition,
                    evidence_budget=case.evidence_budget,
                    minimum_path_costs=case.minimum_path_costs,
                )
                allocation = plan["evidence_allocation"]
                self.assertEqual(
                    sum(allocation["investigator_budgets"])
                    + allocation["synthesis_budget"],
                    case.evidence_budget,
                )
                json.dumps(plan, sort_keys=True)

    def test_v11_harness_records_plan_before_condition(self) -> None:
        case = self.cases[("additive", "easy")]
        task = case.task
        probabilities = {candidate: 0.0 for candidate in task.candidates}
        probabilities[task.correct_candidate] = 1.0
        alternative = next(
            candidate for candidate in task.candidates
            if candidate != task.correct_candidate
        )
        message = {
            "role": "assistant",
            "content": json.dumps(
                {
                    "diagnosis": task.correct_candidate,
                    "probabilities": probabilities,
                    "cited_evidence": [],
                    "rationale": "test",
                    "strongest_alternative": alternative,
                    "recommended_verification": [],
                }
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            harness = HarnessV11(
                _FakeClient([message]),
                EvidenceLedger(path),
                max_tool_rounds=0,
            )
            result = harness.run_condition(
                task,
                "single_agent",
                evidence_budget=case.evidence_budget,
                minimum_path_costs=case.minimum_path_costs,
                target_tokens=0,
                compute_plan=ComputePlan(target_tokens=0),
            )
            records = [json.loads(line)["payload"] for line in path.read_text().splitlines()]
            verification = verify_ledger(path)
        self.assertTrue(result.score.accurate)
        self.assertEqual(records[0]["kind"], "causal_v11_condition_plan")
        self.assertEqual(records[-1]["kind"], "condition_complete")
        self.assertTrue(verification["valid"])


if __name__ == "__main__":
    unittest.main()
