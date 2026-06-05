"""Tests for long-horizon durable-state stasis analysis."""

from hamutay.eval.state_stasis import (
    StateStasisCycle,
    _stable_state_signature,
    find_stasis_runs,
)


def test_stable_state_signature_ignores_volatile_cycle():
    left = {"cycle": 1, "claim": "same", "_activity_log": [{"tool": "x"}]}
    right = {"cycle": 2, "claim": "same", "_activity_log": [{"tool": "y"}]}

    assert _stable_state_signature(left) == _stable_state_signature(right)


def test_find_stasis_runs_marks_post_activation_runs():
    cycles = [
        StateStasisCycle(1, False, 1, 10, False),
        StateStasisCycle(2, True, 1, 10, False),
        StateStasisCycle(3, False, 3, 150, True),
        StateStasisCycle(4, True, 3, 150, True),
        StateStasisCycle(5, True, 3, 150, True),
        StateStasisCycle(6, False, 4, 200, True),
    ]

    runs = find_stasis_runs(cycles, first_active_cycle=3)

    assert [(run.start_cycle, run.end_cycle, run.length) for run in runs] == [
        (2, 2, 1),
        (4, 5, 2),
    ]
    assert [run.post_activation for run in runs] == [False, True]
