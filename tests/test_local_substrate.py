"""A local door's address is substrate: a restart must inherit base_url.

Spec: docs/superpowers/specs/2026-09-06-local-substrate-door-design.md §1.
Without this, a heartbeat restarted without --base-url would resolve
provider=openai to api.openai.com and run the resident on a different
model without saying so.
"""

import json


def _write_records(path, records):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


LOCAL = "http://127.0.0.1:8081/v1"


def _local_record(cycle=3):
    return {
        "cycle": cycle, "state": {"cycle": cycle}, "model": "qwen3.8-27b-q4km",
        "launch": {"model": "qwen3.8-27b-q4km", "provider": "openai",
                   "tools": True, "base_url": LOCAL},
        "wake_mode": "natural",
    }


def test_infer_launch_returns_base_url_from_the_record(tmp_path):
    from hamutay.taste_open import infer_launch_from_log

    log = tmp_path / "qwen.jsonl"
    _write_records(log, [_local_record()])
    inherited = infer_launch_from_log(str(log))
    assert inherited["base_url"] == LOCAL
    assert inherited["provider"] == "openai"


def test_infer_launch_old_record_without_base_url_gives_none(tmp_path):
    from hamutay.taste_open import infer_launch_from_log

    log = tmp_path / "old.jsonl"
    _write_records(log, [{
        "cycle": 1, "state": {"cycle": 1}, "model": "anthropic/claude-haiku-4-5",
        "launch": {"model": "anthropic/claude-haiku-4-5", "provider": "openrouter",
                   "tools": True},
        "wake_mode": "natural",
    }])
    inherited = infer_launch_from_log(str(log))
    assert inherited["base_url"] is None


def test_resolve_launch_inherits_base_url_when_flag_unset():
    from hamutay.taste_open import resolve_launch

    resolved, notes = resolve_launch(
        {"model": None, "provider": None, "tools": True, "wake_mode": None,
         "base_url": None},
        {"model": "qwen3.8-27b-q4km", "provider": "openai", "tools": True,
         "wake_mode": "natural", "base_url": LOCAL, "source_cycle": 3},
    )
    assert resolved["base_url"] == LOCAL
    assert not any(n.startswith("SUBSTRATE CHANGE") for n in notes)


def test_resolve_launch_explicit_different_base_url_is_a_loud_substrate_change():
    from hamutay.taste_open import resolve_launch

    resolved, notes = resolve_launch(
        {"model": None, "provider": None, "tools": True, "wake_mode": None,
         "base_url": "http://10.0.0.5:8081/v1"},
        {"model": "qwen3.8-27b-q4km", "provider": "openai", "tools": True,
         "wake_mode": "natural", "base_url": LOCAL, "source_cycle": 3},
    )
    assert resolved["base_url"] == "http://10.0.0.5:8081/v1"
    assert any(n.startswith("SUBSTRATE CHANGE") and "base_url" in n for n in notes)


def test_resolve_launch_new_subject_base_url_defaults_to_none():
    from hamutay.taste_open import resolve_launch

    resolved, _ = resolve_launch(
        {"model": None, "provider": None, "tools": True, "wake_mode": None,
         "base_url": None},
        None,
    )
    assert resolved["base_url"] is None


def test_resolve_launch_without_base_url_key_is_unchanged():
    """Older call sites that do not ask about base_url get no base_url key."""
    from hamutay.taste_open import resolve_launch

    resolved, _ = resolve_launch(
        {"model": None, "provider": None, "tools": True}, None,
    )
    assert "base_url" not in resolved


def test_heartbeat_restart_inherits_the_local_address(tmp_path):
    from hamutay.heartbeat import build_parser, resolve_heartbeat_launch

    log = tmp_path / "qwen.jsonl"
    _write_records(log, [_local_record()])
    args = build_parser().parse_args(["--log-path", str(log)])
    launch, notes = resolve_heartbeat_launch(args)
    assert launch["provider"] == "openai"
    assert launch["base_url"] == LOCAL
    assert not any(n.startswith("SUBSTRATE CHANGE") for n in notes)


def test_heartbeat_fresh_log_has_no_base_url(tmp_path):
    from hamutay.heartbeat import build_parser, resolve_heartbeat_launch

    args = build_parser().parse_args(["--log-path", str(tmp_path / "new.jsonl")])
    launch, _ = resolve_heartbeat_launch(args)
    assert launch["base_url"] is None
