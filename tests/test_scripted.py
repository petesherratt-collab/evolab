import json
from pathlib import Path
import tempfile
import unittest

from evolutionary_lab.evidence import EvidenceLedger

from collective_lab.causal_generator import generate_causal_case
from collective_lab.oracle import ExactOracle
from collective_lab.runner import Harness
from collective_lab.scripted import ScriptedClient, infer, plan_purchases, run_scripted_condition

CLASSES = ("additive", "relational", "coordination_trap")
DIFFICULTIES = ("easy", "moderate", "hard")
MINIMUM_COST = {("additive", "easy"): 3, ("additive", "moderate"): 9, ("additive", "hard"): 24,
                ("relational", "easy"): 6, ("relational", "moderate"): 18, ("relational", "hard"): 48,
                ("coordination_trap", "easy"): 4, ("coordination_trap", "moderate"): 12,
                ("coordination_trap", "hard"): 17}


class ScriptedCheckerTests(unittest.TestCase):
    """The exact oracle is the offline checker for the scripted condition."""

    def test_script_matches_the_oracle_posterior_on_what_it_bought(self):
        for task_class in CLASSES:
            for difficulty in DIFFICULTIES:
                for seed in (101, 202, 303):
                    case = generate_causal_case(seed, task_class, difficulty)
                    task = case.task
                    public = task.public()
                    bought = plan_purchases(public, 100)
                    evidence = task.evidence_map()
                    probabilities, _ = infer(public, {i: evidence[i].result for i in bought})
                    posterior = ExactOracle(case.causal_task).observed_posterior(bought)
                    for candidate in task.candidates:
                        self.assertAlmostEqual(probabilities[candidate], posterior[candidate])
                    self.assertEqual(probabilities[task.correct_candidate], 1.0)
                    self.assertEqual(sum(evidence[i].cost for i in bought),
                                     MINIMUM_COST[(task_class, difficulty)])

    def test_plan_reads_only_the_public_view(self):
        case = generate_causal_case(7, "coordination_trap", "moderate")
        public = json.loads(json.dumps(case.task.public()))
        self.assertNotIn("correct_candidate", json.dumps(public))
        self.assertTrue(plan_purchases(public, 100))

    def test_a_short_budget_leaves_a_uniform_answer(self):
        case = generate_causal_case(11, "relational", "hard")
        public = case.task.public()
        self.assertEqual(plan_purchases(public, 5), [])
        probabilities, cited = infer(public, {})
        self.assertEqual(set(probabilities.values()), {0.2})
        self.assertEqual(cited, [])


class ScriptedHarnessTests(unittest.TestCase):
    def test_condition_runs_through_the_harness_with_no_tokens(self):
        task = generate_causal_case(55, "additive", "hard").task
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(ScriptedClient(), EvidenceLedger(Path(directory) / "run.jsonl"))
            result = run_scripted_condition(harness, task)
        self.assertEqual(result.score.brier_loss, 0.0)
        self.assertTrue(result.score.accurate)
        self.assertEqual(result.evidence_spent, 24)
        self.assertEqual(result.api_requests, 2)
        self.assertEqual(result.usage, {})
        self.assertEqual(result.score.unsupported_citations, ())


if __name__ == "__main__":
    unittest.main()
