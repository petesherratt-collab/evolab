from collective_lab.acquisition_audit_v14 import stopping_point


def test_terminal_fallback_is_not_misclassified_as_round_exhaustion():
    assert stopping_point([{"context": {"round": 2, "terminal_report_fallback": True}}], 2) == "compute_reservation_terminal_fallback"


def test_normal_terminal_round_and_early_completion_are_distinct():
    assert stopping_point([{"context": {"round": 2}}], 2) == "configured_tool_round_limit"
    assert stopping_point([{"context": {"round": 1}}], 2) == "ended_before_tool_round_limit"
    assert stopping_point([], 2) == "no_episode_completion_record"
