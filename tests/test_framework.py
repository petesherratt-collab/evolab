from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from evolutionary_lab.evidence import EvidenceLedger, verify_ledger
from evolutionary_lab.evolution import EvolutionConfig, EvolutionRunner
from evolutionary_lab.market import chronological_split, market_hash, synthetic_market
from evolutionary_lab.outcomes import FrozenOutcome
from evolutionary_lab.simulator import DeterministicBacktester
from evolutionary_lab.types import StrategySpec, parse_strategy_json


class FrameworkTests(unittest.TestCase):
    @staticmethod
    def _scientific_result(result):
        summary = result.summary()
        summary.pop("evaluation_ms")
        return summary

    def test_strategy_contract_is_exact_and_hashable(self) -> None:
        mapping = {
            "fast_window": 4,
            "slow_window": 20,
            "entry_threshold_bps": 10,
            "exit_threshold_bps": 20,
            "max_position_bps": 5_000,
        }
        parsed = parse_strategy_json(json.dumps(mapping))
        self.assertEqual(parsed.mapping(), mapping)
        self.assertEqual(parsed.strategy_id(), StrategySpec.from_mapping(mapping).strategy_id())
        with self.assertRaisesRegex(ValueError, "STRATEGY_FIELDS_MISMATCH"):
            StrategySpec.from_mapping({**mapping, "unexpected": 1})

    def test_market_generation_and_hash_are_deterministic(self) -> None:
        first = synthetic_market(seed=7, count=90)
        second = synthetic_market(seed=7, count=90)
        self.assertEqual(first, second)
        self.assertEqual(market_hash(first), market_hash(second))
        splits = chronological_split(first)
        self.assertEqual(len(splits.train) + len(splits.validation) + len(splits.test), 90)

    def test_backtest_is_deterministic(self) -> None:
        bars = synthetic_market(seed=8, count=120)
        strategy = StrategySpec(4, 20, 10, 20, 5_000)
        backtester = DeterministicBacktester()
        self.assertEqual(
            self._scientific_result(backtester.run(bars, strategy)),
            self._scientific_result(backtester.run(bars, strategy)),
        )

    def test_evolution_repeats_with_same_seed(self) -> None:
        splits = chronological_split(synthetic_market(seed=9, count=180))
        config = EvolutionConfig(population_size=10, generations=4, seed=99)
        first = EvolutionRunner(splits, config=config).run()
        second = EvolutionRunner(splits, config=config).run()
        self.assertEqual(first.champion, second.champion)
        self.assertEqual(
            self._scientific_result(first.test), self._scientific_result(second.test)
        )

    def test_evidence_ledger_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.jsonl"
            ledger = EvidenceLedger(path)
            ledger.append({"kind": "test", "value": 1})
            ledger.append({"kind": "test", "value": 2})
            self.assertEqual(verify_ledger(path)["records"], 2)
            lines = path.read_text(encoding="utf-8").splitlines()
            record = json.loads(lines[0])
            record["payload"]["value"] = 99
            path.write_text(
                "\n".join([json.dumps(record), lines[1]]) + "\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "EVIDENCE_RECORD_HASH_INVALID"):
                verify_ledger(path)

    def test_frozen_outcome_is_hashable_and_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "outcomes.jsonl"
            ledger = EvidenceLedger(path)
            metrics = {"net_return": 0.125, "bankrupt": False}
            outcome = FrozenOutcome(
                experiment_id="exp-001",
                phase="paper_shadow",
                candidate_id="candidate-001",
                observation_cutoff_ms=123_000,
                observation_hash="market-hash",
                metrics=metrics,
            )
            record = ledger.append_outcome(outcome)
            metrics["net_return"] = 99.0
            self.assertEqual(record["payload"]["kind"], "frozen_outcome")
            self.assertEqual(record["payload"]["metrics"]["net_return"], 0.125)
            self.assertEqual(record["payload"]["outcome_id"], outcome.outcome_id())
            self.assertEqual(verify_ledger(path)["records"], 1)

    def test_frozen_outcome_rejects_invalid_cutoff(self) -> None:
        with self.assertRaisesRegex(ValueError, "OUTCOME_CUTOFF_INVALID"):
            FrozenOutcome(
                experiment_id="exp-001",
                phase="test",
                candidate_id="candidate-001",
                observation_cutoff_ms=-1,
                observation_hash="market-hash",
                metrics={},
            )


if __name__ == "__main__":
    unittest.main()
