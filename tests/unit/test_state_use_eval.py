"""Tests for durable state-use transition detection."""

from hamutay.eval.state_use import CycleStateUse, find_state_use_transitions


def _cycle(
    cycle: int,
    *,
    keys: int,
    tokens: int,
    raw: int,
) -> CycleStateUse:
    return CycleStateUse(
        cycle=cycle,
        durable_key_count=keys,
        durable_token_estimate=tokens,
        raw_update_key_count=raw,
        response_chars=100,
        durable_keys=[f"k{i}" for i in range(keys)],
        raw_update_keys=[f"k{i}" for i in range(raw)],
        response_snippet=f"cycle {cycle}",
    )


def test_find_state_use_transition_detects_sustained_activation():
    cycles = [
        *[_cycle(i, keys=0, tokens=4, raw=0) for i in range(1, 6)],
        *[_cycle(i, keys=5, tokens=400, raw=3) for i in range(6, 11)],
    ]

    transitions = find_state_use_transitions(cycles, window=3)

    assert transitions
    assert transitions[0].cycle == 6
    assert transitions[0].prior_active_rate == 0.0
    assert transitions[0].next_active_rate == 1.0


def test_find_state_use_transition_ignores_response_only_richness():
    cycles = [
        *[_cycle(i, keys=0, tokens=4, raw=0) for i in range(1, 6)],
        *[_cycle(i, keys=5, tokens=400, raw=0) for i in range(6, 11)],
    ]

    assert find_state_use_transitions(cycles, window=3) == []

