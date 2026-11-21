"""Black-box validation of the 2026-11-03 function_strict capability spec.

Only the spec, existing tests, and declaration signatures were consulted.
Transport interception follows tests/unit/test_openai_tool_parity.py; the
withdrawal scripts follow tests/test_context_ceiling.py. No production
request builder, payload-options helper, or send-method body was inspected.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

import pytest

import hamutay.taste_open as taste_open
from hamutay.taste_open import CapabilityProfile, OpenAITasteBackend


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "experiments/taste_open/capabilities.json"
LUNA = "openrouter:openai/gpt-6-luna"
PATHS = ("single", "multi", "terminal_surface", "natural", "withdrawn", "context_retry")
MISSING = object()
CONTEXT_ERROR = (
    "OpenAI backend error: {'code': 400, 'message': 'request (68025 tokens) "
    "exceeds the available context size (65536 tokens), try increasing it', "
    "'type': 'exceed_context_size_error', 'n_prompt_tokens': 68025, 'n_ctx': 65536}"
)


def _tool(name):
    return {
        "name": name,
        "description": f"Validation {name} tool.",
        "input_schema": {
            "type": "object",
            "properties": {
                # A schema property named strict must survive unchanged.
                "strict": {"type": "boolean", "description": "An ordinary argument."},
            },
        },
    }


def _surface():
    return {
        "tool_name": "complete_task",
        "description": "Complete the bounded validation task.",
        "input_schema": {
            "type": "object",
            "properties": {"response": {"type": "string"}},
            "required": ["response"],
        },
        "state_update": {"response_field": "response", "copy": {}, "set": {}},
        "tool_choice": "force",
    }


def _call(name, arguments, call_id):
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": arguments if isinstance(arguments, str) else json.dumps(arguments),
        },
    }


def _reply(*, name=None, arguments=None, call_id="call-1", content=None, tokens=100):
    calls = [_call(name, arguments, call_id)] if name else []
    return {
        "choices": [{
            "finish_reason": "tool_calls" if calls else "stop",
            "message": {"role": "assistant", "content": content, "tool_calls": calls},
        }],
        "usage": {"prompt_tokens": tokens, "completion_tokens": 10},
    }


class RecordingExecutor:
    """Deterministic tools keep withdrawal/retry request fixtures reproducible."""

    def __init__(self):
        self.activity_log = []
        self.calls = []
        self._cycle = 1

    @property
    def pending_state_updates(self):
        return {"updates": {}, "deleted_regions": []}

    def execute(self, name, arguments):
        self.calls.append((name, deepcopy(arguments)))
        result = {"ok": True}
        self.activity_log.append({"tool": name, "parameters": arguments, "result": result})
        return result

    def log_event(self, event):
        self.activity_log.append(event)


class ScriptedTransport:
    def __init__(self, script):
        self.script = deepcopy(script)
        self.payloads = []
        self.references = []

    def __call__(self, url, payload, headers):
        # Intercept below _post_chat so actual payload options still run.
        self.references.append(payload)
        self.payloads.append(json.loads(json.dumps(payload)))
        assert self.script, "backend sent more requests than scripted"
        reply = self.script.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def _seeded_backend_class(strict):
    """Model a caller's converter override, as the spec's launcher does.

    The real converter is called without inspecting its implementation.
    Cache its seeded definitions to detect mutation across requests/backends.
    """
    definitions = {}
    originals = {}

    class SeededBackend(OpenAITasteBackend):
        @staticmethod
        def _openai_tool_def(tool):
            name = tool["name"]
            if name not in definitions:
                definition = deepcopy(OpenAITasteBackend._openai_tool_def(tool))
                definition["function"]["strict"] = strict
                definitions[name] = definition
                originals[name] = deepcopy(definition)
            return definitions[name]

    return SeededBackend, definitions, originals


def _seeded_payload_backend_class(strict):
    """Supply pre-existing function keys before the real payload options run.

    Built-in tools bypass the caller's schema converter. Seed at the named
    options boundary instead, delegating to the real method without reading
    its body. All expectations still inspect transport-captured JSON.
    """
    class SeededPayloadBackend(OpenAITasteBackend):
        def _apply_openai_payload_options(self, payload, *args, **kwargs):
            if payload.get("tools"):
                payload["tools"] = deepcopy(payload["tools"])
                for entry in payload["tools"]:
                    entry["function"]["strict"] = strict
            return super()._apply_openai_payload_options(payload, *args, **kwargs)

    return SeededPayloadBackend


def _scenario(path):
    done = _reply(name="think_and_respond", arguments={"response": "done"})
    if path == "single":
        return [
            _reply(name="think_and_respond", arguments="{", call_id="bad"),
            done,
        ]
    if path == "multi":
        return [
            _reply(name="clock", arguments={}, call_id="clock-1"),
            _reply(name="think_and_respond", arguments="{", call_id="bad"),
            done,
        ]
    if path == "terminal_surface":
        return [_reply(name="complete_task", arguments={"response": "done"})]
    if path == "natural":
        return [
            _reply(name="clock", arguments="{", call_id="bad"),
            _reply(name="clock", arguments={}, call_id="clock-1"),
            _reply(content="done"),
        ]
    if path == "withdrawn":
        return [
            _reply(name="clock", arguments={}, tokens=850),
            *[
                _reply(name="update_state", arguments={"updates": {}},
                       call_id=f"state-{i}", tokens=860 + i)
                for i in range(3)
            ],
            _reply(content="done", tokens=870),
        ]
    assert path == "context_retry"
    return [
        _reply(name="clock", arguments={}),
        RuntimeError(CONTEXT_ERROR),
        _reply(content="done", tokens=500),
    ]


def _backend(path, capability, monkeypatch, backend_class=OpenAITasteBackend):
    backend = backend_class(
        api_key="unused",
        base_url="https://example.invalid/v1",
        max_retries=0,
        capability=capability,
        wake_mode="terminal" if path in {"single", "multi", "terminal_surface"} else "natural",
        context_limit={"withdrawn": 1000, "context_retry": 65536}.get(path),
    )
    transport = ScriptedTransport(_scenario(path))
    monkeypatch.setattr(backend, "_post_with_retry", transport)
    return backend, transport


def _drive(backend, path, *, tools=None, surface=None):
    kwargs = {
        "model": "validation-model",
        "system": "validation system",
        "messages": [{"role": "user", "content": "validate strict"}],
        "experiment_label": "function-strict-validation",
    }
    if path == "terminal_surface":
        result = backend.call_terminal_surface(
            **kwargs, terminal_surface=surface if surface is not None else _surface(),
        )
    elif path == "single":
        result = backend.call(**kwargs)
    else:
        result = backend.call(
            **kwargs,
            extra_tools=tools if tools is not None else [_tool("clock"), _tool("update_state")],
            tool_executor=RecordingExecutor(),
        )
    assert result.raw_output["response"] == "done"


def _assert_path(path, transport):
    """Prevent a bypassed loop or withdrawal from vacuously passing strict tests."""
    assert not transport.script
    payloads = transport.payloads
    assert len(payloads) == {
        "single": 2, "multi": 3, "terminal_surface": 1,
        "natural": 3, "withdrawn": 5, "context_retry": 3,
    }[path]
    names = [
        [entry["function"]["name"] for entry in payload.get("tools", [])]
        for payload in payloads
    ]
    if path == "single":
        assert names == [["think_and_respond"]] * 2
    elif path == "terminal_surface":
        assert names == [["complete_task"]]
    elif path == "multi":
        assert names == [["think_and_respond", "clock", "update_state"]] * 3
    elif path == "natural":
        assert names == [["clock", "update_state"]] * 3
    elif path == "withdrawn":
        assert names == [["clock", "update_state"], *[["update_state"]] * 3, []]
        assert "tools" not in payloads[-1]
    else:
        assert names == [["clock", "update_state"], ["clock", "update_state"], ["update_state"]]


@pytest.mark.parametrize("value", [None, False, True])
def test_01_constructor_accepts_function_strict(value):
    assert CapabilityProfile(function_strict=value).function_strict is value


def test_01_constructor_defaults_function_strict_to_none():
    assert CapabilityProfile().function_strict is None


@pytest.mark.parametrize("data,expected", [
    ({}, None), ({"function_strict": None}, None),
    ({"function_strict": False}, False), ({"function_strict": True}, True),
], ids=["absent", "null", "false", "true"])
def test_01_from_dict_preserves_value_class(data, expected):
    before = deepcopy(data)
    profile = CapabilityProfile.from_dict(data)
    assert profile.function_strict is expected
    assert data == before


@pytest.mark.parametrize("value", [
    0, 1, -1, 0.0, 1.0, "true", "false", "", "unset", [], [False], {}, {"value": False},
], ids=["zero", "one", "negative", "float-zero", "float-one", "string-true",
        "string-false", "empty-string", "string-unset", "empty-list", "list",
        "empty-object", "object"])
def test_01_from_dict_rejects_non_boolean_non_null(value):
    with pytest.raises(ValueError, match="function_strict"):
        CapabilityProfile.from_dict({"function_strict": value})


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("strict", [False, True], ids=["false", "true"])
def test_02_capability_sets_every_outgoing_function(path, strict, monkeypatch):
    backend, transport = _backend(
        path, CapabilityProfile.from_dict({"function_strict": strict}), monkeypatch,
    )
    _drive(backend, path)
    _assert_path(path, transport)
    for turn, payload in enumerate(transport.payloads):
        for entry in payload.get("tools", []):
            assert entry["function"].get("strict", MISSING) is strict, (
                path, turn, entry["function"]["name"], entry["function"].get("strict", "MISSING"),
            )
    without_added_keys = deepcopy(transport.payloads)
    for payload in without_added_keys:
        for entry in payload.get("tools", []):
            del entry["function"]["strict"]
    assert _payload_digest(without_added_keys) == UNSET_PAYLOAD_SHA256[path, None]


@pytest.mark.parametrize("empty_tools", ["absent", "empty-list"])
@pytest.mark.parametrize("strict", [False, True])
def test_02_payload_without_functions_is_unchanged(empty_tools, strict, monkeypatch):
    class NoFunctionsBackend(OpenAITasteBackend):
        def _apply_openai_payload_options(self, payload, *args, **kwargs):
            # Supply the two specified payload shapes at the options boundary.
            if empty_tools == "absent":
                payload.pop("tools", None)
            else:
                payload["tools"] = []
            return super()._apply_openai_payload_options(payload, *args, **kwargs)

    outgoing = []
    for value in (None, strict):
        backend, transport = _backend(
            "natural", CapabilityProfile.from_dict({"function_strict": value}),
            monkeypatch, NoFunctionsBackend,
        )
        transport.script = [_reply(content="done")]
        _drive(backend, "natural")
        assert not transport.script
        assert len(transport.payloads) == 1
        payload = transport.payloads[0]
        if empty_tools == "absent":
            assert "tools" not in payload
        else:
            assert payload["tools"] == []
        outgoing.append(json.dumps(payload))
    assert outgoing[0] == outgoing[1]


# Filled from captured outgoing JSON on the pre-feature backend, never source.
# Freeze the entire payload sequence, including schema keys unrelated to strict.
UNSET_PAYLOAD_SHA256 = {
    ('single', None): 'a33977214e1176475c14ad739c8f152347aaec9ff27d38cf86c930e9c0d941a0',
    ('single', False): '256c176cbe7aef1c3fb2d2962c1bc9bf41d7aefbb6701b84f5d31184f33fb473',
    ('single', True): '9576ebd8c004c34ceec370eafb9af6b44855eed9ecacf8ff76cab5ea529a44e8',
    ('multi', None): '05701fd81960fd06c406e446ef5bf2d870e9ec6240fae4191b0d2aa6a0f743f5',
    ('multi', False): '1d898ca81ec0129acc05129fad1f8bafe4e1de486ffeb990fefb67569ce747cc',
    ('multi', True): '7345048931d71b0a1177709b0570857d8c8e9776460db8a48556bdecbd612d3a',
    ('terminal_surface', None): 'a090ccde46c301b2dfd1c47b51564553946a61226867bfccc90827858e1e4b95',
    ('terminal_surface', False): 'bed2ceadb59c41f2c414782c29c7a5c9b0ab5991563a4ad5818261083f0427e4',
    ('terminal_surface', True): 'ee30bcbbb9ec670b5ebef98be812d2be83f3da140011ad6a43374d92fda81db8',
    ('natural', None): 'a9872850b0e7ee6e2ddc1aa00a4d7a68a6d7ec686d2894109bb0a8cb7d281d05',
    ('natural', False): 'cd37879ac686422697e76d6aacb5b807f59bbb93a564407abf6b5081c9cc7306',
    ('natural', True): 'cea8598caefa396e26cd69f83ce83b864d8fb9cbaef0b597c21fd7d94120be05',
    ('withdrawn', None): '557a054a7286a82fb9b82fbf6264b14231364413dea631ca72b6f88d911dfb93',
    ('withdrawn', False): 'df91953847cf586d75fb8d6fa3e0b11ba0af4af470591a9bceefccac090b82e9',
    ('withdrawn', True): 'fca05f97088bcb6a760f71c85d5630e3dc65877a15f5108f30782e9c051f7848',
    ('context_retry', None): 'f48b0dd99553eef632894ea4a4fd47fe63211668d325a1cb4de433c8a7c55f1d',
    ('context_retry', False): '5fe65dcc4063c7620a7e030656ac93bee4caec2ab82ca5f6565de02deb510f7d',
    ('context_retry', True): 'aaa5364cb8a07ce026895c118f555229668220e92b8db68bb22508ad2002016f',
}


def _payload_digest(payloads):
    return hashlib.sha256(json.dumps(payloads, ensure_ascii=False).encode()).hexdigest()


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("seed", [None, False, True], ids=["no-existing-key", "existing-false", "existing-true"])
@pytest.mark.parametrize("unset", ["default", "absent", "null"])
def test_03_unset_preserves_complete_payload_bytes(path, seed, unset, monkeypatch):
    capability = {
        "default": None,
        "absent": CapabilityProfile.from_dict({}),
        "null": CapabilityProfile.from_dict({"function_strict": None}),
    }[unset]
    cls = OpenAITasteBackend if seed is None else _seeded_payload_backend_class(seed)
    backend, transport = _backend(path, capability, monkeypatch, cls)
    _drive(backend, path)
    _assert_path(path, transport)
    for payload in transport.payloads:
        for entry in payload.get("tools", []):
            function = entry["function"]
            if seed is None:
                assert "strict" not in function
            else:
                assert function["strict"] is seed
    assert _payload_digest(transport.payloads) == UNSET_PAYLOAD_SHA256[path, seed]


@pytest.mark.parametrize("path", PATHS)
def test_04_caller_definitions_survive_repeated_calls_and_other_backends(path, monkeypatch):
    cls, definitions, originals = _seeded_backend_class(True)
    tools, surface = [_tool("clock"), _tool("update_state")], _surface()
    before = deepcopy((tools, surface))
    backend, transport = _backend(
        path, CapabilityProfile.from_dict({"function_strict": False}), monkeypatch, cls,
    )
    for iteration in range(2):
        if iteration:
            transport.script.extend(_scenario(path))
        _drive(backend, path, tools=tools, surface=surface)
        assert (tools, surface) == before
        assert definitions == originals
        assert [payload.get("tools") for payload in transport.references] == [
            payload.get("tools") for payload in transport.payloads
        ]
    first_payloads = deepcopy(transport.payloads)
    for strict in (True, None):
        other, other_transport = _backend(
            path, CapabilityProfile.from_dict({"function_strict": strict}), monkeypatch, cls,
        )
        _drive(other, path, tools=tools, surface=surface)
        _assert_path(path, other_transport)
        assert (tools, surface) == before
        assert definitions == originals
        assert [payload.get("tools") for payload in transport.references] == [
            payload.get("tools") for payload in first_payloads
        ]


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("strict", [False, True], ids=["false-over-true", "true-over-false"])
def test_05_capability_overrides_existing_function_strict(path, strict, monkeypatch):
    cls = _seeded_payload_backend_class(not strict)
    backend, transport = _backend(
        path, CapabilityProfile.from_dict({"function_strict": strict}), monkeypatch, cls,
    )
    _drive(backend, path)
    _assert_path(path, transport)
    for turn, payload in enumerate(transport.payloads):
        for entry in payload.get("tools", []):
            assert entry["function"].get("strict", MISSING) is strict, (
                path, turn, entry["function"]["name"],
            )


@pytest.mark.parametrize("strict", [None, False, True], ids=["unset", "false", "true"])
def test_06_launch_capabilities_line_includes_strict(strict, tmp_path, monkeypatch, capsys):
    registry = tmp_path / "capabilities.json"
    registry.write_text(json.dumps({"openai:validation-model": {"function_strict": strict}}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", [
        "taste_open", "--provider", "openai", "--model", "validation-model",
        "--api-key", "unused", "--no-persist", "--log-path", str(tmp_path / "session.jsonl"),
        "--capabilities-file", str(registry),
    ])

    # End the interactive session without a model request or terminal access.
    import prompt_toolkit

    class EndOfInput:
        def __init__(self, *args, **kwargs):
            pass

        def prompt(self, *args, **kwargs):
            raise EOFError

    monkeypatch.setattr(prompt_toolkit, "PromptSession", EndOfInput)
    monkeypatch.setattr("builtins.input", lambda *args: "quit")
    monkeypatch.setattr(
        OpenAITasteBackend, "_post_with_retry",
        lambda *args, **kwargs: pytest.fail("launch note must not require a model request"),
    )
    taste_open.main()
    lines = [line for line in capsys.readouterr().out.splitlines()
             if "capabilities" in line.lower() and "validation-model" in line]
    assert len(lines) == 1
    expected = "unset" if strict is None else str(strict).lower()
    # The spec does not prescribe Boolean capitalization.
    assert re.search(rf"\bstrict={expected}\b", lines[0], re.IGNORECASE), lines[0]


def test_07_real_registry_declares_luna_route_and_provenance():
    registry = json.loads(REGISTRY.read_text())
    assert LUNA in registry, f"missing capability entry: {LUNA}"
    entry = registry[LUNA]
    assert entry["supports_tools"] is True
    assert entry["supports_parallel_tool_calls"] is False
    assert entry["tool_choice_mode"] == "function_object"
    assert entry["function_strict"] is False
    assert entry["probe_status"] == "declared_from_levadura_2026-10-06"


def test_03_existing_registry_routes_remain_unset():
    registry = json.loads(REGISTRY.read_text())
    for route, entry in registry.items():
        if route != LUNA:
            assert entry.get("function_strict") is None, route
