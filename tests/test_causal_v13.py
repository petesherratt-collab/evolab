from __future__ import annotations

import unittest

from collective_lab.causal_generator import CAUSAL_TASK_CLASSES, DIFFICULTIES
from collective_lab.causal_generator_v13 import (
    CAUSAL_GENERATOR_V13_VERSION,
    faithful_regime_probability_v13,
    generate_causal_case_v13,
)
from collective_lab.freeze_v13 import derive_v13_task_seed
from collective_lab.oracle import ExactOracle
from collective_lab.protocol_v13 import PERSPECTIVE_LENSES, lens_charter
from collective_lab.runner_v13 import v13_condition_plan


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


if __name__ == "__main__":
    unittest.main()
