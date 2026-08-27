"""--resume must inherit the substrate (model, provider, tools) from the log.

The 2026-08-26 incident: resuming the elder with a bare ``--resume`` silently
moved it from Haiku-via-OpenRouter with tools to Sonnet-4.6-direct without
tools, because ``_resume_from_log`` restored the state and took everything
else from CLI defaults. The log knew; the tool discarded what it knew.
"""

import json

from hamutay.taste_open import (
    OpenTasteSession,
    infer_launch_from_log,
    resolve_launch,
)

BASH_BLOCK = "### Shell\n\n- bash(command, timeout?): Execute a bash command."


def _write_log(path, records):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _record(cycle, model, system_prompt="", state=None, **extra):
    rec = {
        "cycle": cycle,
        "model": model,
        "system_prompt": system_prompt,
        "state": {"cycle": cycle} if state is None else state,
    }
    rec.update(extra)
    return rec


class TestInferLaunchFromLog:
    def test_legacy_openrouter_record_with_tools(self, tmp_path):
        log = tmp_path / "s.jsonl"
        _write_log(log, [
            _record(1, "anthropic/claude-haiku-4-5", system_prompt=BASH_BLOCK),
        ])
        launch = infer_launch_from_log(str(log))
        assert launch["model"] == "anthropic/claude-haiku-4-5"
        assert launch["provider"] == "openrouter"
        assert launch["tools"] is True
        assert launch["source_cycle"] == 1
        assert launch["inferred"] is True

    def test_legacy_anthropic_record_without_tools(self, tmp_path):
        log = tmp_path / "s.jsonl"
        _write_log(log, [_record(3, "claude-sonnet-4-6", system_prompt="no shell")])
        launch = infer_launch_from_log(str(log))
        assert launch["provider"] == "anthropic"
        assert launch["tools"] is False

    def test_explicit_launch_field_is_authoritative(self, tmp_path):
        log = tmp_path / "s.jsonl"
        recorded = {
            "model": "anthropic/claude-haiku-4-5",
            "provider": "openrouter",
            "tools": True,
            "capabilities_file": "experiments/taste_open/capabilities.json",
            "openrouter_require_parameters": True,
        }
        _write_log(log, [
            # Prompt says no shell, but the launch record says tools were on:
            # the record wins over inference.
            _record(9, "anthropic/claude-haiku-4-5", system_prompt="", launch=recorded),
        ])
        launch = infer_launch_from_log(str(log))
        assert launch["tools"] is True
        assert launch["capabilities_file"] == recorded["capabilities_file"]
        assert launch["openrouter_require_parameters"] is True
        assert launch["inferred"] is False
        assert launch["source_cycle"] == 9

    def test_uses_last_state_bearing_record(self, tmp_path):
        log = tmp_path / "s.jsonl"
        _write_log(log, [
            _record(1, "anthropic/claude-haiku-4-5", system_prompt=BASH_BLOCK),
            # A failure record carries no state and must not be the source.
            {"cycle": 2, "model": "claude-sonnet-4-6", "status": "failed"},
        ])
        launch = infer_launch_from_log(str(log))
        assert launch["model"] == "anthropic/claude-haiku-4-5"
        assert launch["source_cycle"] == 1

    def test_empty_log_returns_none(self, tmp_path):
        log = tmp_path / "s.jsonl"
        log.write_text("")
        assert infer_launch_from_log(str(log)) is None


class TestResolveLaunch:
    def test_unset_flags_inherit_from_log(self):
        inherited = {"model": "anthropic/claude-haiku-4-5", "provider": "openrouter",
                     "tools": True, "source_cycle": 465, "inferred": True}
        resolved, notes = resolve_launch(
            {"model": None, "provider": None, "tools": None}, inherited,
        )
        assert resolved == {"model": "anthropic/claude-haiku-4-5",
                            "provider": "openrouter", "tools": True}
        assert any("inherited" in n.lower() for n in notes)
        assert not any("SUBSTRATE CHANGE" in n for n in notes)

    def test_explicit_differing_flag_warns_loudly(self):
        inherited = {"model": "anthropic/claude-haiku-4-5", "provider": "openrouter",
                     "tools": True, "source_cycle": 465, "inferred": True}
        resolved, notes = resolve_launch(
            {"model": "claude-sonnet-4-6", "provider": None, "tools": None}, inherited,
        )
        assert resolved["model"] == "claude-sonnet-4-6"
        # provider still inherited — the explicit override was only the model
        assert resolved["provider"] == "openrouter"
        warn = [n for n in notes if "SUBSTRATE CHANGE" in n]
        assert warn and "anthropic/claude-haiku-4-5" in warn[0] and "claude-sonnet-4-6" in warn[0]

    def test_explicit_no_tools_warns(self):
        inherited = {"model": "m", "provider": "anthropic", "tools": True,
                     "source_cycle": 7, "inferred": False}
        resolved, notes = resolve_launch(
            {"model": None, "provider": None, "tools": False}, inherited,
        )
        assert resolved["tools"] is False
        assert any("SUBSTRATE CHANGE" in n and "tools" in n for n in notes)

    def test_new_session_uses_defaults(self):
        resolved, notes = resolve_launch(
            {"model": None, "provider": None, "tools": None}, None,
        )
        assert resolved == {"model": "claude-sonnet-4-6", "provider": "anthropic",
                            "tools": False}
        assert not any("SUBSTRATE CHANGE" in n for n in notes)


class TestLaunchIsLogged:
    def test_log_record_carries_launch(self, tmp_path):
        log_path = tmp_path / "session.jsonl"
        launch = {"model": "claude-sonnet-4-6", "provider": "anthropic",
                  "tools": False, "capabilities_file": None,
                  "openrouter_require_parameters": False}
        session = OpenTasteSession(
            model="claude-sonnet-4-6",
            backend=object(),  # never called
            log_path=str(log_path),
            launch_config=launch,
        )
        session._state = {"cycle": 1}  # a state-bearing record, as after an exchange
        session._log_entry(
            user_message="hi",
            system_prompt="sys",
            raw_output={"response": "ok"},
            prior_state=None,
            record_id=__import__("uuid").uuid4(),
            usage={},
        )
        rec = json.loads(log_path.read_text().splitlines()[0])
        assert rec["launch"] == launch
        # And the inference round-trips through the record, not the prompt.
        assert infer_launch_from_log(str(log_path))["inferred"] is False
