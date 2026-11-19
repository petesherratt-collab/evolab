import json
import sys
from unittest.mock import patch

from collective_lab.acquisition_audit_v15 import main, stopping_point
from evolutionary_lab.evidence import EvidenceLedger


def test_partial_and_unstarted_tasks_are_explicitly_excluded(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"payload": {"tasks": [
        {"task_index": i, "task_class": "additive", "difficulty": "easy"}
        for i in range(3)
    ]}}))
    EvidenceLedger(tmp_path / "task-00-complete.jsonl").append({"kind": "run_complete"})
    EvidenceLedger(tmp_path / "task-01-partial.jsonl").append({"kind": "run_failed"})
    output = tmp_path / "output.json"
    args = ["audit", "--manifest", str(manifest), "--directory", str(tmp_path), "--output", str(output)]
    with patch.object(sys, "argv", args), patch(
        "collective_lab.acquisition_audit_v15.audit_task", return_value={"episodes": []}
    ) as audit:
        main()
    assert audit.call_count == 1
    result = json.loads(output.read_text())
    assert len(result["tasks"]) == 1
    assert [(x["task_index"], x["reason"]) for x in result["excluded_tasks"]] == [(1, "incomplete"), (2, "not_started")]
    assert result["excluded_tasks"][0]["verification"]["valid"]


def test_early_return_is_distinct_from_tool_exhaustion_and_compute_fallback():
    assert stopping_point([{"context": {"round": 1}}], 2) == "ended_before_tool_round_limit"
    assert stopping_point([{"context": {"round": 2}}], 2) == "configured_tool_round_limit"
    assert stopping_point([{"context": {"round": 1, "terminal_report_fallback": True}}], 2) == "compute_reservation_terminal_fallback"
