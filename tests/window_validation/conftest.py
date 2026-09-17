from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest

from hamutay.assembly.binding import bind, load_members
from hamutay.assembly.convene import convene
from hamutay.assembly.ledger import Ledger
from hamutay.assembly.outbox import run_outbox
from hamutay.assembly.records import reduce
from hamutay.context_policy import ContextPolicy, ContextPolicyHolder
from hamutay.events import build_inbound_event
from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession
from hamutay.tools.schemas import (
    DECLARE_QUIET_SCHEMA,
    TOOL_SCHEMAS,
    UPDATE_STATE_SCHEMA,
)

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
CLOSE = T0 + timedelta(days=7)
DOORS = ("a", "b", "c", "d")
_UNSET = object()


class ScriptedCounter:
    """A counter whose returned counts and observed payloads are test data."""

    def __init__(self, counts):
        self.counts = list(counts)
        self.payloads: list[dict] = []

    def count(self, payload):
        self.payloads.append(json.loads(json.dumps(payload)))
        value = self.counts.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class FakeHTTP:
    """Callable HTTP fake for llama-server's render/tokenize endpoints."""

    def __init__(self, counts=(), *, fail_at: str | None = None):
        self.counts = list(counts)
        self.fail_at = fail_at
        self.calls: list[tuple[str, str, dict | None]] = []

    def __call__(self, method: str, url: str, body: dict | None) -> dict:
        copied = json.loads(json.dumps(body)) if body is not None else None
        self.calls.append((method, url, copied))
        if self.fail_at and url.endswith(self.fail_at):
            raise OSError(f"scripted failure at {self.fail_at}")
        if url.endswith("/apply-template"):
            return {"prompt": json.dumps(body, sort_keys=True)}
        if url.endswith("/tokenize"):
            return {"tokens": list(range(self.counts.pop(0)))}
        raise AssertionError(f"unexpected fake HTTP call: {method} {url}")


def turn(
    content=None,
    *,
    tool_calls=None,
    finish="stop",
    prompt_tokens=100,
    completion_tokens=10,
    reasoning_content=None,
):
    message = {"role": "assistant", "content": content, "tool_calls": tool_calls}
    if reasoning_content is not None:
        message["reasoning_content"] = reasoning_content
    return {
        "choices": [{"finish_reason": finish, "message": message}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
    }


def tool_call(name, arguments, call_id="call-1"):
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def natural_tools():
    return [
        TOOL_SCHEMAS["read"],
        TOOL_SCHEMAS["clock"],
        TOOL_SCHEMAS["bash"],
        TOOL_SCHEMAS["schedule_event"],
        UPDATE_STATE_SCHEMA,
        DECLARE_QUIET_SCHEMA,
    ]


def aware_policy(
    limit=65_536,
    *,
    reasoning_budget="probed",
    forced_sequence_tokens=23,
    invocation_id="validation-invocation",
):
    return ContextPolicy(
        limit,
        "discovered",
        limit,
        "http://tokenizer.invalid",
        reasoning_budget,
        {},
        forced_sequence_tokens,
        invocation_id,
    )


def scripted_backend(
    script,
    *,
    counts=None,
    policy=_UNSET,
    wake_mode="natural",
    max_tokens=64_000,
    http=None,
):
    kwargs = {
        "api_key": "validation-key",
        "wake_mode": wake_mode,
        "max_tokens": max_tokens,
    }
    if policy is not _UNSET:
        kwargs["context_policy"] = ContextPolicyHolder(policy)
    if http is not None:
        kwargs["http"] = http
    backend = OpenAITasteBackend(**kwargs)
    backend.payloads = []
    if counts is not None:
        backend._counter = ScriptedCounter(counts)

    replies = list(script)

    def fake_post(payload):
        backend.payloads.append(json.loads(json.dumps(payload)))
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    backend._post_chat = fake_post
    return backend


def seeded_session(tmp_path: Path, backend, *, name="session", wake_mode="natural"):
    log_path = tmp_path / f"{name}.jsonl"
    session = OpenTasteSession(
        model="validation-model",
        backend=backend,
        log_path=str(log_path),
        experiment_label="window-validation",
        enable_tools=True,
        project_root=tmp_path,
        wake_mode=wake_mode,
    )
    session.seed_state({"cycle": 1, "note": "validation"}, 1)
    return session, log_path


def records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def inbound_event(*, event_id=None):
    resolved_event_id = (
        uuid4() if event_id is None else uuid5(NAMESPACE_URL, str(event_id))
    )
    return build_inbound_event(
        purpose="validate a window-aware wake",
        sender="validation-suite",
        event_id=resolved_event_id,
    )


@dataclass
class House:
    root: Path
    ledger: Ledger
    config: object
    question: dict
    bindings: dict


@pytest.fixture
def house_factory(tmp_path):
    made = 0

    def build() -> House:
        nonlocal made
        made += 1
        root = tmp_path / f"house-{made}"
        plaza = root / "community" / "plaza"
        plaza.mkdir(parents=True)
        members = {
            door: {
                "session": f"community/{door}/session.jsonl",
                "events": f"community/{door}/session.jsonl.events.jsonl",
            }
            for door in DOORS
        }
        (plaza / "members.json").write_text(
            json.dumps({"ledger": "community/plaza/assembly.jsonl", "members": members})
        )
        for door in DOORS:
            (root / "community" / door).mkdir()
        config = load_members(root)
        ledger = Ledger(config.ledger)
        question = convene(
            ledger,
            config,
            convener="custodian",
            text="ratify the validation proposal?",
            closes_in=timedelta(days=7),
            now=T0,
            proposal_procedure={"rule": "consent-v0", "max_rounds": 3, "quorum": "ceil(half)"},
            artifact={"path": "proposal", "commit": "validation", "sha256": "digest"},
        )
        with ledger.locked():
            run_outbox(ledger, reduce(ledger.read_unlocked()), now=T0)
        bindings = {
            door: bind(root, config.members[door].session, config.members[door].events)[0]
            for door in DOORS
        }
        return House(root, ledger, config, question, bindings)

    return build
