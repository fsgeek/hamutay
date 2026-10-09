"""Local histories and strict transport fakes; no detector implementation."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib
import json
from uuid import uuid4

from hamutay import events
from hamutay.context_policy import ContextPolicy, ContextPolicyHolder
from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession


T0 = datetime(2026, 10, 8, 10, tzinfo=timezone.utc)
NOW = T0 + timedelta(hours=6)
SENTINEL = "UNEXECUTED-PARAM-9c4f7a21-ONLY-IN-RESIDENT-REPLY"
WITHDRAWN = "Every tool had been withdrawn for that turn, so nothing could receive it."
UNKNOWN = "The record does not say why it was not parsed as a call."
CLEAN = "Natural reply without any XML call."
REPAIRED = "Clean repair reply."


def xml(name="send_message", parameter=SENTINEL):
    return (
        f"<tool_call>\n<function={name}>\n"
        f"<parameter=to>plaza</parameter>\n"
        f"<parameter=text>{parameter}</parameter>\n"
        "</function>\n</tool_call>"
    )


LEAK = "<think> </think>\n" + xml()


def detect(text):
    # Missing production code fails individual cases, rather than collection.
    return importlib.import_module("hamutay.tool_call_text").detect_unexecuted_tool_calls(text)


def status(kind, event_id="event-sentinel", run_id="run-sentinel", at=T0, **fields):
    row = {
        "record_type": "event_status", "event_type": "inbound_message",
        "event_id": event_id, "run_id": run_id, "status": kind,
        "created_at": at.isoformat(),
    }
    if kind in ("completed", "failed"):
        row[f"{kind}_at"] = at.isoformat()
    if kind == "running":
        row["started_at"] = at.isoformat()
    if kind == "failed":
        row.update(error_type="RuntimeError", error="wake failure sentinel")
    row.update(fields)
    return row


def leaked(event_id="event-sentinel", run_id="run-sentinel", names=("send_message",),
           withdrawn=False, **fields):
    return status(
        "completed", event_id, run_id,
        response_text=LEAK,
        unexecuted_tool_calls=[{"function": name} for name in names],
        final_turn={"tools_offered": not withdrawn, "all_tools_withdrawn": withdrawn},
        **fields,
    )


def expected_note(row):
    names = [item["function"] for item in row["unexecuted_tool_calls"]]
    assert len(names) == 1, "exact singular wording oracle"
    cause = WITHDRAWN if row.get("final_turn", {}).get("all_tools_withdrawn") else UNKNOWN
    return (
        f"Your wake for event {row['event_type']} {row['event_id']} "
        f"(run {row['run_id']}) ended with a call to `{names[0]}` written as text. "
        f"It was not carried out. {cause}"
    )


def notes(records, current=None):
    current = current or status("pending", "receiving-event", "receiving-run")
    return events.operational_notes_for_event(records, current, now=NOW)


def pending(store, purpose="Validation knock"):
    event = events.build_inbound_event(purpose=purpose, sender="tony", label="plaza:validation-mail")
    event["created_at"] = T0.isoformat()
    store.append(event)
    return event


def completed_kwargs(event=None, **fields):
    return {
        "event": event or status("pending"), "run_id": "storage-run",
        "wake_cycle": 1, "result_record_id": uuid4(), "response_text": LEAK,
        **fields,
    }


def turn(text=None, calls=None, finish="stop", tokens=100):
    return {
        "choices": [{"finish_reason": finish,
                     "message": {"role": "assistant", "content": text, "tool_calls": calls or []}}],
        "usage": {"prompt_tokens": tokens, "completion_tokens": 10},
    }


def call(name, arguments, call_id="validation-call"):
    return {"id": call_id, "type": "function",
            "function": {"name": name, "arguments": json.dumps(arguments)}}


def wake_script(text=LEAK, withdrawal="none", finish="stop"):
    # Same estimate-based natural-loop mechanism as test_context_ceiling.py:
    # the first measured 850/1000 response withdraws perception next turn;
    # three more accepted state-tool turns force full withdrawal.
    script = []
    if withdrawal in ("perception", "full"):
        script.append(turn(calls=[call("clock", {})], tokens=850))
    if withdrawal == "full":
        for i in range(3):
            script.append(turn(calls=[call("update_state", {"updates": {"n": i}}, f"state-{i}")],
                               tokens=860 + i))
    script.append(turn(text, finish=finish))
    return script


class ScriptedChat:
    def __init__(self, script):
        self.script = deepcopy(script)
        self.payloads = []
        self.accepted = []

    def __call__(self, payload):
        self.payloads.append(deepcopy(payload))
        assert self.script, "unexpected extra chat request"
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        self.accepted.append(deepcopy(payload))
        return item


class RepairValidator:
    def __init__(self):
        self.session = None
        self.calls = []

    def validate(self, **kwargs):
        self.calls.append({
            "response_text": kwargs["response_text"],
            "evidence": deepcopy(getattr(self.session, "_last_natural_final_turn", None)),
        })
        valid = kwargs["response_text"] == REPAIRED
        return {"valid": valid, "status": "valid" if valid else "invalid"}


class RepairBuilder:
    def __init__(self):
        self.calls = []

    def build_repair_prompt(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        return "Repair this validation state."


def fixed_tokenizer(method, url, body):
    if url.endswith("/apply-template"):
        return {"prompt": "validation prompt"}
    if url.endswith("/tokenize"):
        return {"tokens": [0] * 1000}
    raise AssertionError(f"unexpected HTTP call {method} {url}")


def session_and_store(tmp_path, monkeypatch, script, *, repair=False, aware=False):
    kwargs = {}
    if aware:
        kwargs["context_policy"] = ContextPolicyHolder(ContextPolicy(
            10_000, "validation", 10_000, "http://tokenizer.invalid",
            "not_probed", None, 0,
        ))
        kwargs["http"] = fixed_tokenizer
    else:
        kwargs["context_limit"] = 1000
    backend = OpenAITasteBackend(api_key="unused", wake_mode="natural", **kwargs)
    transport = ScriptedChat(script)
    monkeypatch.setattr(backend, "_post_chat", transport)
    validator, builder = RepairValidator(), RepairBuilder()
    store = events.EventStore(tmp_path / "events.jsonl")
    session = OpenTasteSession(
        backend=backend, model="validation-model", wake_mode="natural", enable_tools=True,
        project_root=tmp_path, event_log_path=str(store.path),
        log_path=str(tmp_path / "session.jsonl"),
        state_validator=validator if repair else None,
        state_repair_builder=builder if repair else None,
    )
    validator.session = session
    return session, store, transport, validator, builder


def persisted_completion(store, run_id):
    # Reopen the actual event log, not the object returned by the runner.
    rows = events.EventStore(store.path).read_records()
    matches = [r for r in rows if r.get("status") == "completed" and r.get("run_id") == run_id]
    assert len(matches) == 1
    return matches[0], rows
