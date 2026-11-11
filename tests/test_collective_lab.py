from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from evolutionary_lab.evidence import EvidenceLedger, verify_ledger

from collective_lab.core import parse_report, score_report
from collective_lab.audit import audit_generator
from collective_lab.causal_audit import (
    _nb_accuracy,
    causal_property_checks,
    leakage_probes,
    rename_candidate_labels,
    reorder_evidence,
)
from collective_lab.causal_generator import generate_causal_case
from collective_lab.oracle import ExactOracle
from collective_lab.generator import TASK_CLASSES, generate_case
from collective_lab.freeze import derive_task_seed
from collective_lab.analyze import load_completed_run
from collective_lab.ledger import ExclusiveRunLedger
from collective_lab.openrouter import Completion
from collective_lab.runner import ConditionResult, Harness, compute_assessment
from collective_lab.tasks import engineering_tasks


class FakeClient:
    model = "fake/model"

    def __init__(self, messages: list[dict]) -> None:
        self.messages = list(messages)

    def complete(
        self, messages, *, tools=None, response_format=None, max_tokens=900, seed=None
    ):
        if response_format is not None:
            self.assert_response_format = response_format
        message = self.messages.pop(0)
        return Completion(
            request_id=f"fake-{len(self.messages)}",
            model=self.model,
            provider="fake",
            message=message,
            usage={"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.001},
        )


class CollectiveLabTests(unittest.TestCase):
    def test_frozen_seed_derivation_is_deterministic_and_split_specific(self) -> None:
        first = derive_task_seed(
            "development-seed",
            split="development",
            task_class="additive",
            difficulty="easy",
            task_index=0,
        )
        second = derive_task_seed(
            "development-seed",
            split="development",
            task_class="additive",
            difficulty="easy",
            task_index=0,
        )
        evaluation = derive_task_seed(
            "development-seed",
            split="evaluation",
            task_class="additive",
            difficulty="easy",
            task_index=0,
        )
        self.assertEqual(first, second)
        self.assertNotEqual(first, evaluation)

    def test_causal_candidate_rename_rejects_colliding_targets(self) -> None:
        task = generate_causal_case(500, "additive", "easy").causal_task
        mapping = {candidate: task.candidates[0] for candidate in task.candidates}
        with self.assertRaisesRegex(ValueError, "CAUSAL_RENAME_MAPPING_INVALID"):
            rename_candidate_labels(task, mapping)

    def test_causal_evidence_reorder_rejects_bad_permutation(self) -> None:
        task = generate_causal_case(500, "additive", "easy").causal_task
        with self.assertRaisesRegex(ValueError, "CAUSAL_EVIDENCE_ORDER_INVALID"):
            reorder_evidence(task, tuple(range(19)))

    def test_causal_property_checks_pass(self) -> None:
        checks = causal_property_checks(500)
        self.assertTrue(all(checks.values()), checks)

    def test_leakage_probe_split_keeps_seed_variants_together(self) -> None:
        records = []
        labels = ("a", "b", "c", "d", "e")
        for seed in range(25):
            for variant in range(2):
                records.append(
                    {
                        "accepted": True,
                        "seed": seed,
                        "correct_label": labels[(seed // 5) % 5],
                        "correct_position": seed % 5,
                        "metadata_tokens": (f"variant={variant}",),
                        "text_tokens": ("neutral",),
                    }
                )
        probes = leakage_probes(records)
        self.assertEqual(len(probes), 4)
        self.assertTrue(all(probe.train_cases == 30 for probe in probes))
        self.assertTrue(all(probe.test_cases == 20 for probe in probes))
        self.assertTrue(all(probe.baseline_accuracy == 0.2 for probe in probes))

    def test_naive_bayes_probe_detects_direct_target_token(self) -> None:
        train = [
            {"features": (f"label={label}",), "target": label}
            for label in ("a", "b", "c", "d", "e")
            for _ in range(3)
        ]
        test = [
            {"features": (f"label={label}",), "target": label}
            for label in ("a", "b", "c", "d", "e")
        ]
        baseline, accuracy = _nb_accuracy(
            train, test, feature_key="features", target_key="target"
        )
        self.assertEqual(baseline, 0.2)
        self.assertEqual(accuracy, 1.0)

    def test_causal_generator_has_distinct_class_signatures(self) -> None:
        additive = generate_causal_case(500, "additive", "moderate")
        relational = generate_causal_case(500, "relational", "moderate")
        trap = generate_causal_case(500, "coordination_trap", "moderate")

        additive_oracle = ExactOracle(additive.causal_task)
        relational_oracle = ExactOracle(relational.causal_task)
        trap_oracle = ExactOracle(trap.causal_task)

        self.assertGreater(
            additive_oracle.information_gain((additive.core_evidence[0],)), 0
        )
        relational_pair = relational.core_evidence[:2]
        self.assertAlmostEqual(
            relational_oracle.information_gain((relational_pair[0],)), 0.0
        )
        self.assertAlmostEqual(
            relational_oracle.information_gain((relational_pair[1],)), 0.0
        )
        self.assertGreater(relational_oracle.synergy(relational_pair), 0.9)

        proxy_ids = [
            item.evidence_id
            for item in trap.causal_task.evidence
            if item.role in {"cheap_correlated_proxy", "misleading_summary"}
        ]
        proxy_posterior = trap_oracle.observed_posterior(proxy_ids)
        self.assertGreater(
            proxy_posterior[trap.distractor],
            proxy_posterior[trap.causal_task.correct_candidate],
        )
        verified = trap_oracle.observed_posterior(trap.verification_evidence)
        self.assertGreaterEqual(verified[trap.causal_task.correct_candidate], 0.9)

    def test_causal_difficulty_bands_are_mechanical(self) -> None:
        expected_costs = {
            "additive": [3, 9, 24],
            "relational": [6, 18, 48],
            "coordination_trap": [4, 12, 17],
        }
        for task_class, costs in expected_costs.items():
            cases = [
                generate_causal_case(500, task_class, difficulty)
                for difficulty in ("easy", "moderate", "hard")
            ]
            self.assertEqual(
                [case.metrics.minimum_sufficient_cost for case in cases], costs
            )
            self.assertGreaterEqual(cases[0].metrics.minimum_cost_sufficient_sets, 4)
            self.assertEqual(cases[1].metrics.minimum_cost_sufficient_sets, 1)
            self.assertEqual(cases[2].metrics.minimum_cost_sufficient_sets, 1)

    def test_causal_generation_is_deterministic_and_hides_truth(self) -> None:
        first = generate_causal_case(501, "relational", "hard")
        second = generate_causal_case(501, "relational", "hard")
        self.assertEqual(first.causal_task.fingerprint(), second.causal_task.fingerprint())
        public = json.dumps(first.task.public())
        self.assertNotIn("correct_candidate", public)
        self.assertNotIn("signature codebook", public.lower())
        self.assertNotIn("=000", public)
        self.assertNotIn(first.task.evidence[0].result, public)

    def test_generated_cases_are_deterministic_and_mechanically_valid(self) -> None:
        fingerprints = set()
        for task_class in TASK_CLASSES:
            first = generate_case(125, task_class)
            second = generate_case(125, task_class)
            self.assertEqual(first.task.fingerprint(), second.task.fingerprint())
            self.assertEqual(len(first.task.evidence), 20)
            self.assertEqual(len(first.sufficient_set), 3)
            self.assertLessEqual(
                sum(first.task.evidence_map()[item].cost for item in first.sufficient_set),
                60,
            )
            public = json.dumps(first.task.public())
            self.assertNotIn(first.task.correct_candidate, first.task.briefing)
            self.assertNotIn("correct_candidate", public)
            fingerprints.add(first.task.fingerprint())
        self.assertEqual(len(fingerprints), len(TASK_CLASSES))

    def test_generated_candidate_position_rotates_across_five_seeds(self) -> None:
        positions = []
        correct_labels = []
        for seed in range(125, 130):
            task = generate_case(seed, "additive").task
            positions.append(task.candidates.index(task.correct_candidate))
            correct_labels.append(task.correct_candidate)
        self.assertEqual(sorted(positions), list(range(5)))
        self.assertEqual(len(set(correct_labels)), 1)

    def test_generated_seed_changes_task_fingerprint(self) -> None:
        self.assertNotEqual(
            generate_case(125, "relational").task.fingerprint(),
            generate_case(130, "relational").task.fingerprint(),
        )

    def test_generator_audit_balances_labels_and_positions(self) -> None:
        audit = audit_generator(first_seed=0, seeds_per_class=25)
        self.assertTrue(audit.passed, audit.failures)
        self.assertEqual(set(audit.correct_label_counts.values()), {15})
        self.assertEqual(set(audit.correct_position_counts.values()), {15})

    def test_engineering_tasks_are_well_formed_and_public_view_hides_truth(self) -> None:
        tasks = engineering_tasks()
        self.assertEqual(len(tasks), 3)
        self.assertEqual({task.task_class for task in tasks}, {"additive", "relational", "coordination_trap"})
        self.assertEqual(len({task.fingerprint() for task in tasks}), 3)
        for task in tasks:
            self.assertEqual(len(task.evidence), 20)
            public = json.dumps(task.public())
            self.assertNotIn("correct_candidate", public)
            self.assertNotIn(task.evidence[0].result, public)

    def test_report_scoring_and_integrity_adjustment(self) -> None:
        task = engineering_tasks()[0]
        probabilities = {candidate: 0.0 for candidate in task.candidates}
        probabilities[task.correct_candidate] = 1.0
        report = parse_report(
            {
                "diagnosis": task.correct_candidate,
                "probabilities": probabilities,
                "cited_evidence": ["A05", "A99"],
                "rationale": "Controlled test supports the diagnosis.",
                "strongest_alternative": "pump_cavitation",
                "recommended_verification": [],
            },
            task,
        )
        score = score_report(task, report, {"A05"})
        self.assertEqual(score.brier_loss, 0.0)
        self.assertEqual(score.integrity_adjusted_loss, 2.0)
        self.assertEqual(score.unsupported_citations, ("A99",))

    def test_probability_contract_rejects_bad_sum(self) -> None:
        task = engineering_tasks()[0]
        with self.assertRaisesRegex(ValueError, "REPORT_PROBABILITY_SUM_INVALID"):
            parse_report(
                {
                    "diagnosis": task.correct_candidate,
                    "probabilities": {candidate: 0.1 for candidate in task.candidates},
                    "cited_evidence": [],
                    "rationale": "",
                    "strongest_alternative": "pump_cavitation",
                    "recommended_verification": [],
                },
                task,
            )

    def test_evidence_budget_is_enforced_outside_model(self) -> None:
        task = engineering_tasks()[0]
        probabilities = {candidate: 0.0 for candidate in task.candidates}
        probabilities[task.correct_candidate] = 1.0
        fake = FakeClient(
            [
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "buy_evidence",
                                "arguments": json.dumps({"evidence_ids": ["A05", "A12"]}),
                            },
                        }
                    ],
                },
                {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "diagnosis": task.correct_candidate,
                            "probabilities": probabilities,
                            "cited_evidence": ["A05"],
                            "rationale": "A05 is decisive.",
                            "strongest_alternative": "pump_cavitation",
                            "recommended_verification": [],
                        }
                    ),
                },
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            harness = Harness(fake, EvidenceLedger(path), max_tool_rounds=1)
            report, acquired, spent, completions, errors = harness._agent_episode(
                task,
                role="test",
                budget=8,
                condition="test",
                agent_id="agent-1",
            )
            self.assertIsNotNone(report)
            self.assertEqual(acquired, {"A05"})
            self.assertEqual(spent, 8)
            self.assertEqual(len(completions), 2)
            self.assertEqual(errors, [])
            self.assertEqual(
                fake.assert_response_format["type"], "json_schema"
            )
            self.assertGreater(verify_ledger(path)["records"], 1)

    def test_failed_vote_contributes_uniform_distribution(self) -> None:
        task = engineering_tasks()[0]
        probabilities = {candidate: 0.0 for candidate in task.candidates}
        probabilities[task.correct_candidate] = 1.0
        valid_message = {
            "role": "assistant",
            "content": json.dumps(
                {
                    "diagnosis": task.correct_candidate,
                    "probabilities": probabilities,
                    "cited_evidence": [],
                    "rationale": "test",
                    "strongest_alternative": next(
                        item for item in task.candidates if item != task.correct_candidate
                    ),
                    "recommended_verification": [],
                }
            ),
        }
        malformed = {"role": "assistant", "content": "{}"}
        fake = FakeClient([valid_message, valid_message, valid_message, malformed])
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(
                fake,
                EvidenceLedger(Path(directory) / "ledger.jsonl"),
                max_tool_rounds=0,
            )
            result = harness.run_condition(
                task, "independent_vote", target_tokens=0, tolerance=0.10
            )
        self.assertEqual(result.valid_constituents, 3)
        self.assertEqual(result.failed_constituents, 1)
        self.assertAlmostEqual(
            result.report.probabilities[task.correct_candidate], 0.8
        )

    def test_run_ledger_rejects_concurrent_writer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.jsonl"
            with ExclusiveRunLedger(path) as first:
                first.append({"kind": "started"})
                with self.assertRaisesRegex(RuntimeError, "RUN_LEDGER_ALREADY_LOCKED"):
                    ExclusiveRunLedger(path)
            with ExclusiveRunLedger(path) as reopened:
                reopened.append({"kind": "finished"})
            self.assertEqual(verify_ledger(path)["records"], 2)

    def test_compute_assessment_requires_every_condition_in_range(self) -> None:
        task = engineering_tasks()[0]
        report = None
        score = score_report(task, report, set())

        def result(name: str, tokens: float) -> ConditionResult:
            return ConditionResult(name, report, score, (), 0, 0, {"total_tokens": tokens}, ())

        valid = compute_assessment([result("a", 18_000), result("b", 22_000)], 20_000, 0.15)
        invalid = compute_assessment([result("a", 16_000), result("b", 22_000)], 20_000, 0.15)
        self.assertTrue(valid["eligible"])
        self.assertFalse(invalid["eligible"])

    def test_compute_assessment_can_be_disabled_for_smoke(self) -> None:
        task = engineering_tasks()[0]
        score = score_report(task, None, set())
        result = ConditionResult(
            "single_agent", None, score, (), 0, 0, {"total_tokens": 1234}, ()
        )
        assessment = compute_assessment([result], 0, 0.10)
        self.assertIsNone(assessment["eligible"])
        self.assertEqual(assessment["reason"], "COMPUTE_MATCHING_DISABLED")

    def test_analyzer_rejects_incomplete_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "incomplete.jsonl"
            EvidenceLedger(path).append({"kind": "run_started"})
            with self.assertRaisesRegex(ValueError, "RUN_COMPLETE_MISSING"):
                load_completed_run(path)


if __name__ == "__main__":
    unittest.main()
