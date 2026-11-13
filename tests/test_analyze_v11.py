from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from evolutionary_lab.evidence import EvidenceLedger

from collective_lab.analyze_v11 import summarize_v11


class AnalyzeV11Tests(unittest.TestCase):
    def test_summary_separates_compute_eligible_primary_analysis(self) -> None:
        conditions = (
            "single_agent",
            "independent_vote",
            "independent_synthesizer",
            "communicating_collective",
        )
        losses = (
            {
                "single_agent": 0.1,
                "independent_vote": 0.7,
                "independent_synthesizer": 0.5,
                "communicating_collective": 0.2,
            },
            {
                "single_agent": 0.4,
                "independent_vote": 0.8,
                "independent_synthesizer": 0.6,
                "communicating_collective": 0.3,
            },
        )
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for index, eligible in enumerate((True, False)):
                path = Path(directory) / f"task-{index}.jsonl"
                results = []
                for condition in conditions:
                    results.append(
                        {
                            "condition": condition,
                            "score": {
                                "accurate": condition != "independent_vote",
                                "brier_loss": losses[index][condition],
                                "malformed": False,
                                "unsupported_citations": [],
                            },
                            "usage": {"total_tokens": 25_000, "cost": 0.01},
                            "evidence_spent": 5,
                            "errors": [],
                            "failed_constituents": 0,
                        }
                    )
                EvidenceLedger(path).append(
                    {
                        "kind": "run_complete",
                        "task_id": f"causal-v11-additive-easy-{index}",
                        "compute_assessment": {"eligible": eligible},
                        "results": results,
                    }
                )
                paths.append(path)

            summary = summarize_v11(paths)

        self.assertEqual(summary["integrity"]["compute_eligible_tasks"], 1)
        self.assertEqual(
            summary["integrity"]["compute_ineligible_task_ids"],
            ["causal-v11-additive-easy-1"],
        )
        eligible_collective = summary["eligible_only"]["conditions"][
            "communicating_collective"
        ]
        all_tasks_collective = summary["all_tasks_sensitivity"]["conditions"][
            "communicating_collective"
        ]
        self.assertAlmostEqual(eligible_collective["mean_brier_loss"], 0.2)
        self.assertAlmostEqual(all_tasks_collective["mean_brier_loss"], 0.25)
        contrast = summary["eligible_only"]["contrasts"]["collective_vs_single"]
        self.assertAlmostEqual(contrast["mean_brier_improvement"], -0.1)
        self.assertEqual(contrast["target_higher"], 1)


if __name__ == "__main__":
    unittest.main()
