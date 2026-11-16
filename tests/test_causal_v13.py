from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from evolutionary_lab.evidence import EvidenceLedger

from collective_lab.causal_generator import CAUSAL_TASK_CLASSES, DIFFICULTIES
from collective_lab.causal_generator_v13 import (
    CAUSAL_GENERATOR_V13_VERSION,
    faithful_regime_probability_v13,
    generate_causal_case_v13,
)
from collective_lab.freeze_v13 import derive_v13_task_seed
from collective_lab.oracle import ExactOracle
from collective_lab.openrouter import Completion
from collective_lab.protocol_v13 import (
    ComputePlanV13,
    PERSPECTIVE_LENSES,
    lens_charter,
)
from collective_lab.runner_v12 import ConditionTokenGate
from collective_lab.runner_v13 import HarnessV13, v13_condition_plan


class _TerminalClient:
    model = "fake/model"

    def __init__(self) -> None:
        self.tools = []

    def complete(
        self, messages, *, tools=None, response_format=None, max_tokens=900, seed=None
    ) -> Completion:
        self.tools.append(tools)
        return Completion(
            request_id="terminal",
            model=self.model,
            provider="fake",
            message={"role": "assistant", "content": "{}"},
            usage={
                "prompt_tokens": 100,
                "completion_tokens": 10,
                "total_tokens": 110,
                "cost": 0.0,
            },
        )


class CausalV13Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = {
            (task_class, difficulty): generate_causal_case_v13(
                500, task_class, difficulty
            )
            for task_class in CAUSAL_TASK_CLASSES
            for difficulty in DIFFICULTIES
        }

    def test_all_cells_have_exact_uncertainty_ceiling(self) -> None:
        for identity, case in self.cases.items():
            with self.subTest(identity=identity):
                self.assertEqual(
                    case.causal_task.generator_version,
                    CAUSAL_GENERATOR_V13_VERSION,
                )
                self.assertAlmostEqual(
                    case.metrics.observed_full_posterior,
                    faithful_regime_probability_v13(identity[1]),
                )
                self.assertGreater(
                    case.metrics.observed_full_posterior,
                    case.sufficiency_threshold,
                )

    def test_moderate_and_hard_lanes_are_cost_and_region_matched(self) -> None:
        for identity, case in self.cases.items():
            if identity[1] == "easy":
                continue
            with self.subTest(identity=identity):
                evidence = case.task.evidence_map()
                self.assertIsNotNone(case.topology_router)
                self.assertEqual(
                    len(case.acquisition_lanes), len(case.core_evidence) - 1
                )
                self.assertGreaterEqual(
                    len({lane.region for lane in case.acquisition_lanes}), 3
                )
                for lane in case.acquisition_lanes:
                    active = evidence[lane.active_option]
                    alternative = evidence[lane.alternative_option]
                    self.assertEqual(active.cost, alternative.cost)
                    self.assertEqual(active.region, alternative.region)

    def test_topology_router_has_zero_fault_information(self) -> None:
        for identity, case in self.cases.items():
            if case.topology_router is None:
                continue
            with self.subTest(identity=identity):
                self.assertAlmostEqual(
                    ExactOracle(case.causal_task).information_gain(
                        (case.topology_router,)
                    ),
                    0.0,
                )

    def test_difficulty_bands_raise_path_cost_and_lower_ceiling(self) -> None:
        for task_class in CAUSAL_TASK_CLASSES:
            easy, moderate, hard = (
                self.cases[(task_class, difficulty)] for difficulty in DIFFICULTIES
            )
            with self.subTest(task_class=task_class):
                self.assertLess(
                    sum(easy.minimum_path_costs),
                    sum(moderate.minimum_path_costs),
                )
                self.assertLess(
                    sum(moderate.minimum_path_costs),
                    sum(hard.minimum_path_costs),
                )
                self.assertGreater(
                    easy.faithful_regime_probability,
                    moderate.faithful_regime_probability,
                )
                self.assertGreater(
                    moderate.faithful_regime_probability,
                    hard.faithful_regime_probability,
                )

    def test_task_classes_keep_distinct_mechanics(self) -> None:
        additive = self.cases[("additive", "moderate")]
        relational = self.cases[("relational", "moderate")]
        trap = self.cases[("coordination_trap", "moderate")]
        self.assertGreater(additive.metrics.maximum_single_information_gain, 0)
        self.assertGreater(relational.metrics.maximum_pair_synergy, 0)
        self.assertGreater(
            trap.metrics.cheap_distractor_posterior,
            trap.metrics.cheap_correct_posterior,
        )

    def test_perspective_charter_is_public_and_task_independent(self) -> None:
        self.assertEqual(len(PERSPECTIVE_LENSES), 4)
        self.assertEqual(len({lens.lens_id for lens in PERSPECTIVE_LENSES}), 4)
        self.assertTrue(
            all(
                set(item) == {"lens_id", "title", "instruction"}
                for item in lens_charter()
            )
        )

    def test_seed_derivation_is_deterministic_and_split_specific(self) -> None:
        arguments = {
            "task_class": "additive",
            "difficulty": "easy",
            "task_index": 0,
        }
        development = derive_v13_task_seed(
            "master", split="development", **arguments
        )
        repeated = derive_v13_task_seed(
            "master", split="development", **arguments
        )
        evaluation = derive_v13_task_seed(
            "master", split="evaluation", **arguments
        )
        self.assertEqual(development, repeated)
        self.assertNotEqual(development, evaluation)

    def test_condition_plan_exposes_complete_public_charter(self) -> None:
        case = self.cases[("additive", "moderate")]
        plan = v13_condition_plan(
            case.task,
            "communicating_collective",
            evidence_budget=case.evidence_budget,
            minimum_path_costs=case.minimum_path_costs,
        )
        self.assertEqual(plan["protocol_version"], "causal-1.3-dev")
        self.assertEqual(len(plan["public_perspective_charter"]), 4)
        self.assertEqual(
            plan["compute_plan"]["mandatory_episode_reserve_tokens"], 3_200
        )
        self.assertEqual(
            plan["compute_plan"]["prompt_characters_per_token"], 5.0
        )
        self.assertEqual(plan["compute_plan"]["lower_bound"], 25_000)
        self.assertEqual(plan["compute_plan"]["upper_bound"], 30_000)

    def test_tool_reservation_can_fall_back_to_terminal_report(self) -> None:
        plan = ComputePlanV13(
            target_tokens=2_000,
            tolerance=0.10,
            prompt_token_overhead=0,
            post_call_safety_margin=0,
        )
        client = _TerminalClient()
        with tempfile.TemporaryDirectory() as directory:
            harness = HarnessV13(
                client,
                EvidenceLedger(Path(directory) / "fallback.jsonl"),
                max_tokens=200,
                max_tool_rounds=1,
                compute_plan=plan,
            )
            harness._token_gate = ConditionTokenGate(plan, used_tokens=1_750)
            harness._reserve_after = 400
            completion = harness._complete(
                [{"role": "user", "content": "finish"}],
                tools=[{"type": "function", "function": {"name": "unused"}}],
                response_format=None,
                context={"condition": "test"},
            )
        self.assertEqual(completion.request_id, "terminal")
        self.assertEqual(client.tools, [None])


if __name__ == "__main__":
    unittest.main()
