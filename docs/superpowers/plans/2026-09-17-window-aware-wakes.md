# Window-Aware Wakes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local door (llama-server, known window) never runs a generation into the physical wall: every request is counted exactly by the server, bounded so that `prompt_tokens + max_tokens < limit`, given a bounded think on grammar-free turns, and if a wake still fails on the window its output is captured and it gets one compact retry; the assembly's close pass classifies positions by the run that recorded them.

**Architecture:** One frozen `ContextPolicy` value in a session-owned `ContextPolicyHolder`, dereferenced at use by the backend and the event runners. The OpenAI backend gains a `TokenCounter` (llama-server `/apply-template` + `/tokenize`), a `_count_and_bound` step before every send on all four paths, a `_take_response` step that accounts before checking `finish_reason`, typed `WindowFailure`s, and `prepare`/`call_prepared` so the session's admission loop counts the exact first payload. The event envelope is a deep-copied, lean, typed projection built by a closure the runner hands the session; the event store gains a fsynced two-line failed-plus-retry append; the close pass gains a per-run lifecycle.

**Tech Stack:** Python 3.14 (`uv run`), pytest, httpx (already a dependency), dataclasses, `fcntl` locks already in `EventStore`/`Ledger`.

**Spec:** `docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md` revision 6 (commit `b7ab196`), reviews `-review.md` … `-review-7.md`. The spec is the authority; where this plan is more specific, the plan wins on names and signatures.

## Global Constraints

- Every commit: `git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "<message>"` with the trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` when a subagent typed it. The post-commit OTS hook adds a stamp commit; expected (`uv sync --extra dev` once in the worktree so `.venv/bin/ots` exists).
- Work in the worktree `.worktrees/window` on branch `window` from `main`. Never `git stash`. `git add` only the files named in the task.
- Tests: `uv run pytest <path> -q -p no:cacheprovider`. After every task: `tests/test_context_ceiling.py`, `tests/test_context_policy.py` (from Task 2 on), `tests/test_window.py` (from Task 3 on), `tests/unit/test_events.py`, `tests/test_heartbeat.py`, `tests/test_event_ingress.py`, `tests/assembly`, `tests/assembly_validation` must pass. Before the merge the full suite (`uv run pytest tests -q -p no:cacheprovider --ignore=tests/integration`) must pass.
- Code and tests come from separate minds: the implementer writes the tests in this plan; Codex authors independent validation afterwards (Task 11).
- The property, asserted in code: for every window-aware request, `prompt_tokens + max_tokens < limit` (strict).
- Constants (module `src/hamutay/window.py`, never duplicated as literals elsewhere): `REPLY_RESERVE_TOKENS = 2048`, `THINK_FLOOR_TOKENS = 512`, `THINK_UNRESTRICTED_ROOM_TOKENS = 32768`, `WITHDRAWN_TOOL_TURNS_NEAR_WALL = 1`, `SOFT_THRESHOLD_FRACTION = 0.8`, `ADMISSION_TARGET_FRACTION = 0.5`, `ADMISSION_MAX_PASSES = 8`, `MIN_STUB_CHARS = 256`, `BUDGET_MESSAGE = "[harness: thinking budget reached; about {reserve} tokens remain for this turn. Do not open another think block. Finish the turn.]"`.
- A door is **window-aware** iff `policy.limit is not None and policy.tokenizer is not None`. With no ceiling, every payload, prompt, envelope, launch note and completed record is byte-identical to today; a ceiling with no tokenizer keeps today's §5 behaviour byte-identical. The one declared record migration: a length failure's record on any door gains `failure_classification.truncated_reply`, real `usage`, earlier `interim_text`, and `error_type == "TruncatedReply"`.
- Budget fields (`reasoning_budget_tokens`, `reasoning_budget_message`) are sent only when `policy.reasoning_budget == "probed"`, `tool_choice == "none"`, and `room < THINK_UNRESTRICTED_ROOM_TOKENS`.
- Every instant is timezone-bearing ISO-8601. Do not touch `community/*` live files or running units until Task 11. Check the process table before anything touches the live door.

---

## File Structure

Create:
- `src/hamutay/window.py` — constants, `WindowFailure` family, `WakeAccount`, `TokenCounter`, `Bound`, `bound_payload`, `lean_activity_logs`, `project_context_results`, `budget_message`.
- `src/hamutay/context_policy.py` — `ContextPolicy`, `ContextPolicyHolder`, `probe_reasoning_budget`, `tokenizer_root`.
- `tests/fixtures/window_golden/` — JSON fixtures captured in Task 1 from the pre-change code.
- `tests/test_window.py`, `tests/test_context_policy.py`, `tests/integration/test_local_window.py`.

Modify:
- `src/hamutay/taste_open.py` — `OpenAITasteBackend` (`__init__`, `_send`, `_take_response`, `prepare`, `call_prepared`, the four paths), `_build_messages(lean_activity_log=)`, `OpenTasteSession` (`context_policy`, `_exchange_impl` admission and compact rendering, the `api_call` failure branch, `_log_entry(admission=)`, `apply_context_limit`).
- `src/hamutay/events.py` — `build_event_envelope(policy=, cap_chars=)`, `run_next_event` (envelope closure, compact runs, typed-failure retry), `EventStore._append_unlocked`, `EventStore.append_failed_with_retry`, `_build_completed(admission=)`, `append_failed(admission=)`.
- `src/hamutay/assembly/close.py` — `_runs_by_event`, `eligible_positions`, `try_close`.
- `src/hamutay/heartbeat.py` — policy at launch, launch note clause, launch record.
- `tests/test_context_ceiling.py`, `tests/assembly/test_close.py`, `tests/test_heartbeat.py`, `tests/unit/test_events.py`.

---

### Task 1: Golden fixtures from the pre-change code

**Files:**
- Create: `tests/fixtures/window_golden/no_ceiling_two_turn.json`, `tests/fixtures/window_golden/no_ceiling_length_failure.json`, `tests/fixtures/window_golden/explicit_ceiling_two_turn.json`
- Create: `tests/test_window_golden.py`
- Create: `scripts/capture_window_golden.py`

**Interfaces:**
- Produces: three fixture files, each `{"payloads": [...], "system_prompt": "...", "record": {...}}` captured from the code at the plan's base; a test module that replays the same scripted wake and asserts byte-equality (or, for the length failure, equality except in four named places).

- [ ] **Step 1: Write the capture script**

`scripts/capture_window_golden.py` (run once now, kept for re-capture):

```python
"""Capture golden fixtures for the window-aware change from the code AS IT IS.

Run from the repo root BEFORE implementing anything in the window plan:
    uv run python scripts/capture_window_golden.py
Writes tests/fixtures/window_golden/*.json. Task 1 of
docs/superpowers/plans/2026-09-17-window-aware-wakes.md.
"""
import json
from pathlib import Path

from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession
from hamutay.tools import ToolExecutor
from hamutay.tools.schemas import DECLARE_QUIET_SCHEMA, TOOL_SCHEMAS, UPDATE_STATE_SCHEMA

OUT = Path("tests/fixtures/window_golden")


def _tool_call(name, args, call_id="c1"):
    return {"id": call_id, "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}


def _turn(content=None, tool_calls=None, finish="stop", prompt_tokens=100, completion_tokens=10):
    return {"choices": [{"finish_reason": finish,
                         "message": {"role": "assistant", "content": content, "tool_calls": tool_calls}}],
            "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}}


def _tools():
    return [TOOL_SCHEMAS["read"], TOOL_SCHEMAS["clock"], TOOL_SCHEMAS["bash"],
            TOOL_SCHEMAS["schedule_event"], UPDATE_STATE_SCHEMA, DECLARE_QUIET_SCHEMA]


def _backend(script, **kw):
    b = OpenAITasteBackend(api_key="k", wake_mode="natural", **kw)
    b.payloads = []

    def fake_post(payload):
        b.payloads.append(json.loads(json.dumps(payload)))
        nxt = script.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt
    b._post_chat = fake_post
    return b


def _session(tmp, backend):
    log = tmp / "session.jsonl"
    s = OpenTasteSession(model="m", backend=backend, log_path=str(log), experiment_label="golden",
                         enable_tools=True, project_root=tmp)
    s.seed_state({"cycle": 3, "note": "golden", "_activity_log": [
        {"cycle": 3, "timestamp": "2026-09-01T00:00:00+00:00", "tool": "clock", "reason": "r",
         "parameters": {"x": 1}, "result_summary": "clock: cycle 3", "result_hash": "h", "duration_ms": 1}]}, 3)
    return s, log


def capture(name, tmp, backend, run):
    s, log = _session(tmp, backend)
    try:
        run(s)
    except Exception:
        pass
    records = [json.loads(l) for l in log.read_text().splitlines()]
    rec = records[-1]
    for k in ("timestamp", "record_id"):
        rec.pop(k, None)
    (OUT / f"{name}.json").write_text(json.dumps(
        {"payloads": backend.payloads, "system_prompt": rec["system_prompt"], "record": rec},
        indent=1, sort_keys=True, default=str))


def main():
    import tempfile
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        b = _backend([_turn(tool_calls=[_tool_call("clock", {})]), _turn(content="done")])
        capture("no_ceiling_two_turn", tmp, b, lambda s: s.exchange("hello"))
        b = _backend([_turn(tool_calls=[_tool_call("clock", {})]), _turn(content="cut", finish="length")])
        capture("no_ceiling_length_failure", tmp, b, lambda s: s.exchange("hello"))
        b = _backend([_turn(tool_calls=[_tool_call("clock", {})]), _turn(content="done")], context_limit=100_000)
        capture("explicit_ceiling_two_turn", tmp, b, lambda s: s.exchange("hello"))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it and inspect the fixtures**

Run: `uv run python scripts/capture_window_golden.py && ls -la tests/fixtures/window_golden/ && python3 -c "import json; d=json.load(open('tests/fixtures/window_golden/no_ceiling_length_failure.json')); print(d['record']['failure_classification'], d['record']['usage'])"`
Expected: three files; the length-failure record shows `error_type: RuntimeError`, `usage: {input_tokens: 0, output_tokens: 0, stop_reason: error}` (today's loss, to be migrated).

- [ ] **Step 3: Write the golden test**

`tests/test_window_golden.py`:

```python
"""Byte-identity guards for the window-aware change (spec 'What stays byte-identical').

Fixtures were captured from commit b7ab196's parent code by
scripts/capture_window_golden.py BEFORE any window change landed.
"""
import json
from pathlib import Path

import pytest

from scripts.capture_window_golden import _backend, _session, _tool_call, _turn

FIX = Path("tests/fixtures/window_golden")


def _load(name):
    return json.loads((FIX / f"{name}.json").read_text())


def _run(tmp_path, backend, exc=None):
    s, log = _session(tmp_path, backend)
    if exc is None:
        s.exchange("hello")
    else:
        with pytest.raises(exc):
            s.exchange("hello")
    rec = json.loads(log.read_text().splitlines()[-1])
    for k in ("timestamp", "record_id"):
        rec.pop(k, None)
    return json.loads(json.dumps(backend.payloads, sort_keys=True)), rec


def test_no_ceiling_two_turn_wake_is_byte_identical(tmp_path):
    g = _load("no_ceiling_two_turn")
    b = _backend([_turn(tool_calls=[_tool_call("clock", {})]), _turn(content="done")])
    payloads, rec = _run(tmp_path, b)
    assert payloads == g["payloads"]
    assert rec["system_prompt"] == g["system_prompt"]
    assert json.loads(json.dumps(rec, sort_keys=True, default=str)) == g["record"]


def test_explicit_ceiling_without_tokenizer_is_byte_identical(tmp_path):
    g = _load("explicit_ceiling_two_turn")
    b = _backend([_turn(tool_calls=[_tool_call("clock", {})]), _turn(content="done")], context_limit=100_000)
    payloads, rec = _run(tmp_path, b)
    assert payloads == g["payloads"]
    assert rec["system_prompt"] == g["system_prompt"]


def test_no_ceiling_length_failure_differs_only_in_the_four_declared_places(tmp_path):
    g = _load("no_ceiling_length_failure")
    b = _backend([_turn(tool_calls=[_tool_call("clock", {})]), _turn(content="cut", finish="length")])
    payloads, rec = _run(tmp_path, b, exc=RuntimeError)
    assert payloads == g["payloads"]
    old, new = g["record"], json.loads(json.dumps(rec, sort_keys=True, default=str))
    allowed = {"usage", "interim_text", "failure_classification"}
    for k in set(old) | set(new):
        if k in allowed:
            continue
        assert old.get(k) == new.get(k), k
    fc_old, fc_new = old["failure_classification"], new["failure_classification"]
    for k in set(fc_old) | set(fc_new):
        if k in ("error_type", "truncated_reply", "error"):
            continue
        assert fc_old.get(k) == fc_new.get(k), k
```

- [ ] **Step 4: Run it (all three pass on the unchanged code)**

Run: `uv run pytest tests/test_window_golden.py -q -p no:cacheprovider`
Expected: 3 passed (the third passes trivially now because nothing differs yet; it becomes the migration guard once Task 3 lands).

- [ ] **Step 5: Commit**

```bash
git add scripts/capture_window_golden.py tests/fixtures/window_golden tests/test_window_golden.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "window: golden fixtures captured from the pre-change code (byte-identity guards, spec 'What stays byte-identical')"
```

---

### Task 2: `ContextPolicy`, the holder, and the probe

**Files:**
- Create: `src/hamutay/context_policy.py`
- Test: `tests/test_context_policy.py`

**Interfaces:**
- Produces: `ContextPolicy(limit, source, result_cap_chars, tokenizer, reasoning_budget, probe, forced_sequence_tokens, invocation_id=None)` frozen; `.window_aware -> bool`; `.as_dict() -> dict`; `ContextPolicy.none()`; `ContextPolicy.for_limit(limit, source)`; `ContextPolicy.for_launch(limit, source, base_url, *, http, model, invocation_id=None, cached=None) -> ContextPolicy`; `ContextPolicyHolder(current)`; `tokenizer_root(base_url) -> str`; `probe_reasoning_budget(root, model, http) -> dict`; `http` is `Callable[[str, str, dict | None], dict]` = `(method, url, json_body) -> parsed json` raising on failure.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_context_policy.py
import json

import pytest

from hamutay.context_policy import (
    ContextPolicy, ContextPolicyHolder, probe_reasoning_budget, tokenizer_root,
)
from hamutay.window import BUDGET_MESSAGE, REPLY_RESERVE_TOKENS

TEMPLATE = "{% for m in messages %}<|im_start|>{{m.role}}\n{{m.content}}<|im_end|>{% endfor %}<think>\n"


class FakeHTTP:
    """Routes: /props, /tokenize, /apply-template, /v1/chat/completions."""
    def __init__(self, *, props=None, tokens_per_call=None, chat=None, fail=()):
        self.props = props
        self.tokens = list(tokens_per_call or [])
        self.chat = list(chat or [])
        self.fail = set(fail)
        self.calls = []

    def __call__(self, method, url, body):
        self.calls.append((method, url, body))
        path = url.split("8081", 1)[-1]
        if path in self.fail:
            raise RuntimeError(f"fake failure {path}")
        if path == "/props":
            return self.props
        if path == "/tokenize":
            n = self.tokens.pop(0)
            return {"tokens": list(range(n))}
        if path == "/apply-template":
            return {"prompt": json.dumps(body)}
        if path == "/v1/chat/completions":
            return self.chat.pop(0)
        raise AssertionError(path)


def _chat(content, reasoning=None, completion=20):
    msg = {"role": "assistant", "content": content}
    if reasoning is not None:
        msg["reasoning_content"] = reasoning
    return {"choices": [{"finish_reason": "stop", "message": msg}],
            "usage": {"prompt_tokens": 10, "completion_tokens": completion}}


PROPS = {"build_info": "b1-73a43d1", "model_alias": "qwen", "chat_template": TEMPLATE,
         "default_generation_settings": {"n_ctx": 65536}}


def test_tokenizer_root_strips_v1():
    assert tokenizer_root("http://127.0.0.1:8081/v1") == "http://127.0.0.1:8081"
    assert tokenizer_root("http://127.0.0.1:8081/v1/") == "http://127.0.0.1:8081"


def test_none_and_for_limit_are_not_window_aware():
    assert ContextPolicy.none().window_aware is False
    p = ContextPolicy.for_limit(100_000, "explicit")
    assert (p.limit, p.source, p.tokenizer, p.reasoning_budget) == (100_000, "explicit", None, "not_probed")
    assert p.window_aware is False and p.result_cap_chars == 100_000


def test_for_launch_probed_when_control_thinks_and_zero_budget_does_not():
    http = FakeHTTP(props=PROPS, tokens_per_call=[7],
                    chat=[_chat("<think>\nlong thought\n</think>ready"), _chat("<think>\n</think>ready")])
    p = ContextPolicy.for_launch(65536, "discovered", "http://127.0.0.1:8081/v1", http=http, model="qwen")
    assert p.window_aware and p.tokenizer == "http://127.0.0.1:8081"
    assert p.reasoning_budget == "probed"
    assert p.forced_sequence_tokens == 7
    assert p.probe["accepted"] and p.probe["template_has_tags"] and p.probe["forcing_observed"]
    assert p.probe["template_sha256"] and p.probe["build_info"] == "b1-73a43d1"
    zero = [c for c in http.calls if c[1].endswith("/chat/completions")][1][2]
    assert zero["reasoning_budget_tokens"] == 0 and zero["reasoning_budget_message"] == ""
    assert zero["seed"] == 7 and zero["temperature"] == 0 and zero["max_tokens"] == 48
    tok = [c for c in http.calls if c[1].endswith("/tokenize")][0][2]
    assert tok["add_special"] is False and BUDGET_MESSAGE.format(reserve=REPLY_RESERVE_TOKENS) in tok["content"]


def test_for_launch_unsupported_when_identical_or_not_accepted():
    same = _chat("<think>\nt\n</think>x")
    http = FakeHTTP(props=PROPS, tokens_per_call=[7], chat=[same, json.loads(json.dumps(same))])
    p = ContextPolicy.for_launch(65536, "discovered", "http://127.0.0.1:8081/v1", http=http, model="qwen")
    assert p.reasoning_budget == "unsupported" and p.probe["forcing_observed"] is False
    http = FakeHTTP(props=PROPS, tokens_per_call=[7], chat=[same, RuntimeError("400")])
    http.chat = [same]
    p = ContextPolicy.for_launch(65536, "discovered", "http://127.0.0.1:8081/v1", http=http, model="qwen")
    assert p.reasoning_budget == "unsupported" and p.probe["accepted"] is False


def test_for_launch_inconclusive_when_control_has_no_think_body():
    http = FakeHTTP(props=PROPS, tokens_per_call=[7], chat=[_chat("ready"), _chat("ready")])
    p = ContextPolicy.for_launch(65536, "discovered", "http://127.0.0.1:8081/v1", http=http, model="qwen")
    assert p.reasoning_budget == "inconclusive"


def test_for_launch_reasoning_content_field_counts_as_the_body():
    http = FakeHTTP(props=PROPS, tokens_per_call=[7],
                    chat=[_chat("ready", reasoning="thought"), _chat("ready", reasoning="")])
    p = ContextPolicy.for_launch(65536, "discovered", "http://127.0.0.1:8081/v1", http=http, model="qwen")
    assert p.reasoning_budget == "probed"


def test_for_launch_reuses_a_cached_probe_on_the_same_key_and_reprobes_on_change():
    http = FakeHTTP(props=PROPS, tokens_per_call=[7],
                    chat=[_chat("<think>\nt\n</think>x"), _chat("<think>\n</think>x")])
    p = ContextPolicy.for_launch(65536, "discovered", "http://127.0.0.1:8081/v1", http=http, model="qwen")
    http2 = FakeHTTP(props=PROPS, tokens_per_call=[7])
    p2 = ContextPolicy.for_launch(65536, "discovered", "http://127.0.0.1:8081/v1", http=http2, model="qwen",
                                  cached=p.probe)
    assert p2.reasoning_budget == "probed" and not any(u.endswith("/chat/completions") for _, u, _ in http2.calls)
    changed = dict(PROPS, build_info="b2-ffffff")
    http3 = FakeHTTP(props=changed, tokens_per_call=[7], chat=[_chat("<think>\nt\n</think>x"), _chat("<think>\n</think>x")])
    p3 = ContextPolicy.for_launch(65536, "discovered", "http://127.0.0.1:8081/v1", http=http3, model="qwen",
                                  cached=p.probe)
    assert sum(u.endswith("/chat/completions") for _, u, _ in http3.calls) == 2 and p3.probe["build_info"] == "b2-ffffff"


def test_for_launch_without_a_llama_server_is_not_window_aware():
    http = FakeHTTP(props={"object": "list"}, fail=())
    p = ContextPolicy.for_launch(100_000, "explicit", "https://openrouter.ai/api/v1", http=http, model="m")
    assert p.tokenizer is None and p.reasoning_budget == "not_probed" and p.window_aware is False
    http = FakeHTTP(fail=("/props",))
    p = ContextPolicy.for_launch(65536, "inherited", "http://127.0.0.1:8081/v1", http=http, model="qwen")
    assert p.tokenizer is None and p.window_aware is False


def test_holder_and_as_dict_round_trip():
    h = ContextPolicyHolder(ContextPolicy.none())
    assert h.current.limit is None
    p = ContextPolicy.for_limit(10, "explicit")
    h.current = p
    assert h.current is p
    d = p.as_dict()
    assert d["limit"] == 10 and d["window_aware"] is False and "probe" in d


def test_probe_records_latency_and_queued_flag(monkeypatch):
    import hamutay.context_policy as cp
    ticks = iter([0.0, 6.0, 6.0, 6.5])
    monkeypatch.setattr(cp.time, "monotonic", lambda: next(ticks))
    http = FakeHTTP(chat=[_chat("<think>\nt\n</think>x"), _chat("<think>\n</think>x")])
    probe = probe_reasoning_budget("http://127.0.0.1:8081", "qwen", http, template=TEMPLATE, props=PROPS)
    assert probe["latency_s"] == pytest.approx(6.5) and probe["queued"] is True
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_context_policy.py -q -p no:cacheprovider`
Expected: FAIL, `ModuleNotFoundError: hamutay.context_policy` (and `hamutay.window`, created in Task 3; for this task create `src/hamutay/window.py` with only the constants block from Task 3 Step 3 so the import resolves — Task 3 fills the rest).

- [ ] **Step 3: Write the module**

```python
# src/hamutay/context_policy.py
"""One frozen value for a door's context ceiling, its tokenizer and its
reasoning-budget capability; one mutable holder the session owns.

Spec: docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md,
"The context policy". The value is replaced whole (apply_context_limit); the
backend and the event runners dereference the holder at use.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field

from hamutay.window import BUDGET_MESSAGE, REPLY_RESERVE_TOKENS

PROBE_PROMPT = "Say the word 'ready'."
PROBE_MAX_TOKENS = 48
PROBE_SEED = 7
PROBE_QUEUED_S = 5.0
THINK_START = "<think>"
THINK_END = "</think>"


def tokenizer_root(base_url: str) -> str:
    root = base_url.rstrip("/")
    return root[:-3] if root.endswith("/v1") else root


def _result_cap_chars(limit: int | None) -> int | None:
    from hamutay.taste_open import _result_cap_for_context_limit
    return _result_cap_for_context_limit(limit)


def _reasoning_body(message: dict) -> str:
    """The think body of a raw assistant message, whatever the presentation.

    `reasoning_content` when the server separates it; otherwise the text of
    `content` between the end tag and (if present) the start tag, since a
    template may prefill the start tag so it is never generated."""
    rc = message.get("reasoning_content")
    if isinstance(rc, str):
        return rc.strip()
    content = message.get("content") or ""
    if not isinstance(content, str):
        return ""
    end = content.find(THINK_END)
    if end < 0:
        return ""
    head = content[:end]
    start = head.find(THINK_START)
    return (head[start + len(THINK_START):] if start >= 0 else head).strip()


def probe_reasoning_budget(root: str, model: str, http, *, template: str, props: dict) -> dict:
    """Two deterministic completions: a control and a zero-budget request.

    Records three separate facts (accepted, template_has_tags, forcing_observed);
    `probed` needs all three. Spec "The probe"."""
    t0 = time.monotonic()
    base = {"model": model, "messages": [{"role": "user", "content": PROBE_PROMPT}],
            "max_tokens": PROBE_MAX_TOKENS, "seed": PROBE_SEED, "temperature": 0}
    out = {"build_info": props.get("build_info"), "model_alias": props.get("model_alias"),
           "template_sha256": hashlib.sha256(template.encode()).hexdigest(),
           "template_has_tags": THINK_START in template and THINK_END in template,
           "accepted": False, "control_had_think": False, "forcing_observed": False,
           "latency_s": None, "queued": False}
    try:
        control = http("POST", f"{root}/v1/chat/completions", dict(base))
        control_msg = control["choices"][0]["message"]
        out["control_had_think"] = bool(_reasoning_body(control_msg))
        zero = http("POST", f"{root}/v1/chat/completions",
                    dict(base, reasoning_budget_tokens=0, reasoning_budget_message=""))
        zero_msg = zero["choices"][0]["message"]
        out["accepted"] = True
        out["forcing_observed"] = out["control_had_think"] and not _reasoning_body(zero_msg) \
            and json.dumps(control_msg, sort_keys=True) != json.dumps(zero_msg, sort_keys=True)
    except Exception as e:  # a refused or failed request is "not accepted"
        out["error"] = str(e)[:200]
    out["latency_s"] = time.monotonic() - t0
    out["queued"] = out["latency_s"] > PROBE_QUEUED_S
    return out


def _classify(probe: dict | None) -> str:
    if probe is None:
        return "not_probed"
    if not probe.get("accepted") or not probe.get("template_has_tags"):
        return "unsupported"
    if not probe.get("control_had_think"):
        return "inconclusive"
    return "probed" if probe.get("forcing_observed") else "unsupported"


@dataclass(frozen=True)
class ContextPolicy:
    limit: int | None
    source: str
    result_cap_chars: int | None
    tokenizer: str | None
    reasoning_budget: str
    probe: dict | None
    forced_sequence_tokens: int
    invocation_id: str | None = None

    @property
    def window_aware(self) -> bool:
        return self.limit is not None and self.tokenizer is not None

    def as_dict(self) -> dict:
        d = asdict(self)
        d["window_aware"] = self.window_aware
        return d

    @classmethod
    def none(cls) -> "ContextPolicy":
        return cls(None, "provider default", None, None, "not_probed", None, 0)

    @classmethod
    def for_limit(cls, limit: int | None, source: str) -> "ContextPolicy":
        return cls(limit, source, _result_cap_chars(limit), None, "not_probed", None, 0)

    @classmethod
    def for_launch(cls, limit: int | None, source: str, base_url: str | None, *, http, model: str,
                   invocation_id: str | None = None, cached: dict | None = None) -> "ContextPolicy":
        """Build the value for a launch (or a rediscovery). `http(method, url, body)`."""
        if not base_url:
            return cls.for_limit(limit, source)
        root = tokenizer_root(base_url)
        try:
            props = http("GET", f"{root}/props", None)
        except Exception:
            props = None
        if not isinstance(props, dict) or "build_info" not in props:
            return cls.for_limit(limit, source)
        template = props.get("chat_template") or ""
        key = (props.get("build_info"), props.get("model_alias"), hashlib.sha256(template.encode()).hexdigest())
        if cached and (cached.get("build_info"), cached.get("model_alias"), cached.get("template_sha256")) == key:
            probe = dict(cached)
        else:
            probe = probe_reasoning_budget(root, model, http, template=template, props=props)
        message = BUDGET_MESSAGE.format(reserve=REPLY_RESERVE_TOKENS)
        try:
            forced = len(http("POST", f"{root}/tokenize", {"content": message + THINK_END, "add_special": False})["tokens"])
        except Exception:
            forced = 96
        return cls(limit, source, _result_cap_chars(limit), root, _classify(probe), probe, forced, invocation_id)


@dataclass
class ContextPolicyHolder:
    current: ContextPolicy = field(default_factory=ContextPolicy.none)
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_context_policy.py -q -p no:cacheprovider`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/context_policy.py src/hamutay/window.py tests/test_context_policy.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "window: ContextPolicy, its holder, and the behaviour probe (spec 'The context policy')"
```

---

### Task 3: `window.py`: constants, failures, the counter, bounding, projections

**Files:**
- Modify (fill): `src/hamutay/window.py`
- Test: `tests/test_window.py`

**Interfaces:**
- Produces: constants (Global Constraints); `class WindowFailure(RuntimeError)`; `CountUnavailable(WindowFailure)` (`.error`); `ExhaustedBeforeRequest(WindowFailure)` (`.prompt_tokens, .limit, .room, .max_tokens`); `TruncatedReply(WindowFailure)` (`.text, .message, .turn_index, .prompt_tokens, .completion_tokens, .account: WakeAccount`); `@dataclass WakeAccount(input_tokens=0, output_tokens=0, cache_read=0, cache_write=0, responses: list, interim_text: list)`; `class TokenCounter(root, http)` with `.count(payload) -> int` (POST `/apply-template` with the payload, POST `/tokenize` `{content, add_special: True, parse_special: True}`; any failure raises `CountUnavailable`); `@dataclass Bound(prompt_tokens, room, max_tokens, budget_fields: dict, sendable: bool, reason: str | None, count_source: str)`; `bound_payload(payload, policy, counter, *, configured_max_tokens, tool_choice_none: bool, candidate=False) -> Bound` (mutates `payload["max_tokens"]` and adds budget fields when sendable and not candidate); `lean_activity_logs(obj) -> obj` (deep copy, `_activity_log` entries reduced to the five keys); `project_context_results(results, cap_chars) -> list` (deep copy, lean, typed truncation); `budget_message() -> str`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_window.py
import json

import pytest

from hamutay.context_policy import ContextPolicy
from hamutay.window import (
    ADMISSION_MAX_PASSES, MIN_STUB_CHARS, REPLY_RESERVE_TOKENS, THINK_FLOOR_TOKENS,
    THINK_UNRESTRICTED_ROOM_TOKENS, Bound, CountUnavailable, ExhaustedBeforeRequest, TokenCounter,
    TruncatedReply, WakeAccount, WindowFailure, bound_payload, budget_message, lean_activity_logs,
    project_context_results,
)


class ScriptedCounter:
    def __init__(self, counts):
        self.counts = list(counts)
        self.payloads = []

    def count(self, payload):
        self.payloads.append(json.loads(json.dumps(payload)))
        n = self.counts.pop(0)
        if isinstance(n, Exception):
            raise n
        return n


def _policy(limit=65536, *, budget="probed", forced=20):
    return ContextPolicy(limit, "discovered", limit, "http://127.0.0.1:8081", budget, {}, forced)


def test_failures_are_typed_and_carry_numbers():
    assert issubclass(CountUnavailable, WindowFailure) and issubclass(TruncatedReply, WindowFailure)
    e = ExhaustedBeforeRequest(prompt_tokens=64000, limit=65536, room=1535, max_tokens=1535)
    assert (e.prompt_tokens, e.limit, e.room, e.max_tokens) == (64000, 65536, 1535, 1535)
    assert "64000 of 65536" in str(e)


def test_token_counter_renders_then_tokenizes_with_special_tokens():
    calls = []

    def http(method, url, body):
        calls.append((url, body))
        if url.endswith("/apply-template"):
            return {"prompt": "RENDERED"}
        return {"tokens": [1, 2, 3]}
    c = TokenCounter("http://127.0.0.1:8081", http)
    assert c.count({"model": "m", "messages": []}) == 3
    assert calls[0][0].endswith("/apply-template") and calls[0][1] == {"model": "m", "messages": []}
    assert calls[1][1] == {"content": "RENDERED", "add_special": True, "parse_special": True}


def test_token_counter_failure_is_count_unavailable():
    def http(method, url, body):
        raise OSError("down")
    with pytest.raises(CountUnavailable):
        TokenCounter("http://127.0.0.1:8081", http).count({"model": "m"})


def test_bound_payload_ample_room_sets_only_max_tokens():
    p = {"model": "m", "messages": [], "tool_choice": "auto"}
    b = bound_payload(p, _policy(), ScriptedCounter([20000]), configured_max_tokens=64000, tool_choice_none=False)
    assert b.prompt_tokens == 20000 and b.room == 65536 - 1 - 20000 == 45535
    assert p["max_tokens"] == 45535 and b.max_tokens == 45535 and b.sendable
    assert "reasoning_budget_tokens" not in p and b.budget_fields == {}
    assert b.prompt_tokens + p["max_tokens"] < 65536


def test_bound_payload_budget_only_on_grammar_free_turns_near_the_wall():
    counter = ScriptedCounter([40000, 40000])
    p = {"model": "m", "messages": [], "tool_choice": "auto"}
    b = bound_payload(p, _policy(forced=20), counter, configured_max_tokens=64000, tool_choice_none=False)
    assert b.room == 25535 < THINK_UNRESTRICTED_ROOM_TOKENS and "reasoning_budget_tokens" not in p
    p2 = {"model": "m", "messages": [], "tool_choice": "none"}
    b2 = bound_payload(p2, _policy(forced=20), counter, configured_max_tokens=64000, tool_choice_none=True)
    assert p2["reasoning_budget_tokens"] == 25535 - REPLY_RESERVE_TOKENS - 20
    assert p2["reasoning_budget_message"] == budget_message()
    assert b2.budget_fields["reasoning_budget_tokens"] == p2["reasoning_budget_tokens"]


def test_bound_payload_no_budget_when_not_probed():
    for kind in ("unsupported", "inconclusive", "not_probed"):
        p = {"model": "m", "messages": [], "tool_choice": "none"}
        bound_payload(p, _policy(budget=kind), ScriptedCounter([40000]), configured_max_tokens=64000, tool_choice_none=True)
        assert "reasoning_budget_tokens" not in p and p["max_tokens"] == 25535


def test_bound_payload_floor_is_checked_on_max_tokens_not_room():
    floor = REPLY_RESERVE_TOKENS + THINK_FLOOR_TOKENS + 20
    p = {"model": "m", "messages": [], "tool_choice": "none"}
    with pytest.raises(ExhaustedBeforeRequest) as ei:
        bound_payload(p, _policy(forced=20), ScriptedCounter([65536 - 1 - (floor - 1)]),
                      configured_max_tokens=64000, tool_choice_none=True)
    assert ei.value.max_tokens == floor - 1 and "max_tokens" not in p
    p = {"model": "m", "messages": [], "tool_choice": "none"}
    with pytest.raises(ExhaustedBeforeRequest):   # configured --max-tokens below the floor, room ample
        bound_payload(p, _policy(forced=20), ScriptedCounter([1000]), configured_max_tokens=floor - 1, tool_choice_none=True)
    p = {"model": "m", "messages": [], "tool_choice": "none"}
    b = bound_payload(p, _policy(forced=20), ScriptedCounter([1000]), configured_max_tokens=floor, tool_choice_none=True)
    assert p["max_tokens"] == floor and p["reasoning_budget_tokens"] == THINK_FLOOR_TOKENS


def test_bound_payload_candidate_mode_reports_instead_of_raising_the_floor():
    p = {"model": "m", "messages": [], "tool_choice": "auto"}
    b = bound_payload(p, _policy(), ScriptedCounter([65000]), configured_max_tokens=64000, tool_choice_none=False,
                      candidate=True)
    assert b.sendable is False and b.reason == "exhausted_before_request" and "max_tokens" not in p
    with pytest.raises(CountUnavailable):
        bound_payload(p, _policy(), ScriptedCounter([CountUnavailable("x")]), configured_max_tokens=64000,
                      tool_choice_none=False, candidate=True)


def test_bound_payload_strict_boundary():
    p = {"model": "m", "messages": [], "tool_choice": "auto"}
    b = bound_payload(p, _policy(), ScriptedCounter([10]), configured_max_tokens=1_000_000, tool_choice_none=False)
    assert b.prompt_tokens + p["max_tokens"] == 65536 - 1


def test_lean_activity_logs_is_recursive_and_copies():
    src = {"a": {"_activity_log": [{"cycle": 1, "timestamp": "t", "tool": "x", "reason": "r",
                                    "result_summary": "s", "parameters": {"big": "x" * 100},
                                    "result_hash": "h", "duration_ms": 3, "exit_code": 0}]},
           "b": [{"content": {"_activity_log": [{"tool": "y", "parameters": {}}]}}]}
    before = json.dumps(src)
    out = lean_activity_logs(src)
    assert json.dumps(src) == before
    assert out["a"]["_activity_log"] == [{"cycle": 1, "timestamp": "t", "tool": "x", "reason": "r", "result_summary": "s"}]
    assert out["b"][0]["content"]["_activity_log"] == [{"tool": "y"}]


def test_project_context_results_types_and_caps():
    big = {"request": {"tool": "recall", "cycle": 11},
           "result": {"cycle": 11, "content": {"k": "v" * 5000, "_activity_log": [{"tool": "t", "parameters": {"p": 1}}]}}}
    small = {"request": {"tool": "recall", "cycle": 1, "field": "k"}, "result": {"content": "short"}}
    out = project_context_results([big, small], cap_chars=1000)
    assert out[1]["result"] == {"content": "short"} and out[1]["result"] is not small["result"]
    r = out[0]["result"]
    assert r["truncated"] is True and r["chars_kept"] == 1000 and len(r["head"]) == 1000 and r["why"] == "context result cap"
    assert "parameters" not in json.dumps(r["head"]) or r["chars"] > 0   # lean applied before sizing
    assert "parameters" in json.dumps(big)                                # argument untouched
    out2 = project_context_results([big], cap_chars=MIN_STUB_CHARS - 1)
    assert "head" not in out2[0]["result"] and out2[0]["result"]["chars_kept"] == 0
    assert project_context_results([big, small], cap_chars=None) == [big, small]


def test_wake_account_and_truncated_reply_snapshot():
    acct = WakeAccount()
    acct.input_tokens += 5
    acct.interim_text.append("earlier")
    e = TruncatedReply(text="cut", message={"content": "cut"}, turn_index=2, prompt_tokens=100,
                       completion_tokens=7, account=acct)
    assert e.account.input_tokens == 5 and e.account.interim_text == ["earlier"] and e.turn_index == 2
    assert "finish_reason=length" in str(e)
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_window.py -q -p no:cacheprovider`
Expected: FAIL on imports.

- [ ] **Step 3: Write the module**

```python
# src/hamutay/window.py
"""Window-aware wakes: the numbers, the failures, the counter, the bound, the projections.

Spec: docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md r6.
Property (asserted in bound_payload): prompt_tokens + max_tokens < limit.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

REPLY_RESERVE_TOKENS = 2048
THINK_FLOOR_TOKENS = 512
THINK_UNRESTRICTED_ROOM_TOKENS = 32768
WITHDRAWN_TOOL_TURNS_NEAR_WALL = 1
SOFT_THRESHOLD_FRACTION = 0.8
ADMISSION_TARGET_FRACTION = 0.5
ADMISSION_MAX_PASSES = 8
MIN_STUB_CHARS = 256
BUDGET_MESSAGE = ("[harness: thinking budget reached; about {reserve} tokens remain for this "
                  "turn. Do not open another think block. Finish the turn.]")
LEAN_ACTIVITY_KEYS = ("cycle", "timestamp", "tool", "reason", "result_summary")


def budget_message() -> str:
    return BUDGET_MESSAGE.format(reserve=REPLY_RESERVE_TOKENS)


class WindowFailure(RuntimeError):
    """A wake that could not be sent or finished inside the window."""


class CountUnavailable(WindowFailure):
    def __init__(self, error: str):
        self.error = error
        super().__init__(f"OpenAI backend: the prompt could not be counted: {error}")


class ExhaustedBeforeRequest(WindowFailure):
    def __init__(self, *, prompt_tokens: int, limit: int, room: int, max_tokens: int):
        self.prompt_tokens, self.limit, self.room, self.max_tokens = prompt_tokens, limit, room, max_tokens
        super().__init__(f"OpenAI backend: context exhausted before the request: {prompt_tokens} of "
                         f"{limit} in hand, {room} left, {max_tokens} would be allowed")


@dataclass
class WakeAccount:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0
    responses: list = field(default_factory=list)
    interim_text: list = field(default_factory=list)


class TruncatedReply(WindowFailure):
    def __init__(self, *, text: str, message: dict, turn_index: int, prompt_tokens: int,
                 completion_tokens: int, account: WakeAccount):
        self.text, self.message, self.turn_index = text, message, turn_index
        self.prompt_tokens, self.completion_tokens, self.account = prompt_tokens, completion_tokens, account
        super().__init__("OpenAI backend: finish_reason=length; the reply was truncated and is not trusted")


class TokenCounter:
    """Exact count of the prompt llama-server will tokenize for a request body."""

    def __init__(self, root: str, http):
        self._root, self._http = root, http

    def count(self, payload: dict) -> int:
        try:
            rendered = self._http("POST", f"{self._root}/apply-template", payload)["prompt"]
            toks = self._http("POST", f"{self._root}/tokenize",
                              {"content": rendered, "add_special": True, "parse_special": True})["tokens"]
        except Exception as e:
            raise CountUnavailable(str(e)[:200]) from e
        return len(toks)


@dataclass
class Bound:
    prompt_tokens: int
    room: int
    max_tokens: int
    budget_fields: dict
    sendable: bool
    reason: str | None
    count_source: str = "server"


def bound_payload(payload: dict, policy, counter, *, configured_max_tokens: int,
                  tool_choice_none: bool, candidate: bool = False) -> Bound:
    """Count, bound, and (unless candidate) mutate `payload`; assert the property.

    Raises CountUnavailable always; ExhaustedBeforeRequest unless candidate."""
    prompt_tokens = counter.count(payload)
    limit = policy.limit
    room = limit - 1 - prompt_tokens
    max_tokens = min(configured_max_tokens, room)
    floor = REPLY_RESERVE_TOKENS + THINK_FLOOR_TOKENS + policy.forced_sequence_tokens
    if max_tokens < floor:
        if candidate:
            return Bound(prompt_tokens, room, max_tokens, {}, False, "exhausted_before_request")
        raise ExhaustedBeforeRequest(prompt_tokens=prompt_tokens, limit=limit, room=room, max_tokens=max_tokens)
    fields: dict = {}
    if policy.reasoning_budget == "probed" and tool_choice_none and room < THINK_UNRESTRICTED_ROOM_TOKENS:
        fields = {"reasoning_budget_tokens": max_tokens - REPLY_RESERVE_TOKENS - policy.forced_sequence_tokens,
                  "reasoning_budget_message": budget_message()}
    if not candidate:
        assert prompt_tokens + max_tokens < limit, (prompt_tokens, max_tokens, limit)
        payload["max_tokens"] = max_tokens
        payload.update(fields)
    return Bound(prompt_tokens, room, max_tokens, fields, True, None)


def lean_activity_logs(obj):
    """Deep copy in which every `_activity_log` list's entries keep only the five lean keys."""
    def walk(x):
        if isinstance(x, dict):
            return {k: ([{kk: vv for kk, vv in e.items() if kk in LEAN_ACTIVITY_KEYS} if isinstance(e, dict) else e
                         for e in v] if k == "_activity_log" and isinstance(v, list) else walk(v))
                    for k, v in x.items()}
        if isinstance(x, list):
            return [walk(i) for i in x]
        return x
    return walk(json.loads(json.dumps(obj, default=str)))


def project_context_results(results: list, cap_chars: int | None) -> list:
    """A deep-copied, lean, typed projection for the envelope; the argument is untouched."""
    if cap_chars is None:
        return json.loads(json.dumps(results, default=str))
    out = []
    for item in lean_activity_logs(results):
        result = item.get("result") if isinstance(item, dict) else None
        s = json.dumps(result, default=str)
        if len(s) > cap_chars:
            keep = cap_chars if cap_chars >= MIN_STUB_CHARS else 0
            stub = {"truncated": True, "chars": len(s), "chars_kept": keep, "why": "context result cap"}
            if keep:
                stub["head"] = s[:keep]
            item = dict(item, result=stub)
        out.append(item)
    return out
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_window.py tests/test_context_policy.py -q -p no:cacheprovider`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/window.py tests/test_window.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "window: constants, typed failures, the exact counter, the bound, the lean and typed projections (spec §1, §2)"
```

---

### Task 4: The backend: `_send`, `_take_response`, `prepare`/`call_prepared`, the four paths

**Files:**
- Modify: `src/hamutay/taste_open.py` (`OpenAITasteBackend.__init__`, `_call_single_tool`, `call_terminal_surface`, `_call_multi_turn`, `_call_natural`; new `_send`, `_take_response`, `prepare`, `call_prepared`, `_first_payload_*`)
- Test: `tests/test_context_ceiling.py` (extend)

**Interfaces:**
- Consumes: Task 2 `ContextPolicyHolder`, Task 3 everything.
- Produces: `OpenAITasteBackend(..., context_policy: ContextPolicyHolder | None = None, http=None)`; `.policy -> ContextPolicy` (holder dereference); `.counter -> TokenCounter | None`; `Prepared(payload, prompt_tokens, path, sendable, reason, inputs)` dataclass; `prepare(model, system, messages, extra_tools, terminal_surface, tool_executor, *, candidate=False) -> Prepared`; `call_prepared(prepared) -> ExchangeResult`; `_send(payload, acct, *, turn_index, tool_choice_none) -> dict` (bound when window-aware, post, take); `_take_response(data, acct, *, turn_index) -> dict` (accounts, raises `TruncatedReply` on length); the `budget_pressure` events `generation_budgeted`, `exhausted_before_request`, `count_unavailable`; the natural loop's turn-0 soft check on the counted prompt, the near-wall one-turn rule, `all_withdrawn` → `tool_choice: "none"`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_context_ceiling.py`; the file's `_backend`, `_turn`, `_tool_call`, `_tools`, `_names`, `_events` helpers are reused)

```python
# --- window-aware: exact count, bound, budget, capture ----------------------
from hamutay.context_policy import ContextPolicy, ContextPolicyHolder
from hamutay.window import (REPLY_RESERVE_TOKENS, THINK_FLOOR_TOKENS, CountUnavailable,
                            ExhaustedBeforeRequest, TruncatedReply)


class _Counter:
    def __init__(self, counts):
        self.counts = list(counts); self.seen = []

    def count(self, payload):
        self.seen.append(json.loads(json.dumps(payload)))
        n = self.counts.pop(0)
        if isinstance(n, Exception):
            raise n
        return n


def _aware(script, counts, *, budget="probed", forced=20, limit=65536, max_tokens=64000, wake_mode="natural"):
    holder = ContextPolicyHolder(ContextPolicy(limit, "discovered", limit, "http://127.0.0.1:8081", budget, {}, forced))
    backend = OpenAITasteBackend(api_key="k", wake_mode=wake_mode, context_policy=holder, max_tokens=max_tokens)
    backend.payloads = []
    backend._counter = _Counter(counts)

    def fake_post(payload):
        backend.payloads.append(json.loads(json.dumps(payload)))
        nxt = script.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt
    backend._post_chat = fake_post
    return backend


def test_every_send_is_counted_and_bounded_on_the_natural_path(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    b = _aware([_turn(tool_calls=[_tool_call("clock", {})], prompt_tokens=20000), _turn(content="done", prompt_tokens=21000)],
               counts=[20000, 21000])
    b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
           extra_tools=_tools(), tool_executor=executor)
    assert len(b._counter.seen) == 2 == len(b.payloads)
    for c, p in zip(b._counter.seen, b.payloads):
        assert c["messages"] == p["messages"] and c["tools"] == p["tools"]
    assert b.payloads[0]["max_tokens"] == 65536 - 1 - 20000 and "reasoning_budget_tokens" not in b.payloads[0]
    assert all(pt + p["max_tokens"] < 65536 for pt, p in zip((20000, 21000), b.payloads))


def test_turn_zero_soft_threshold_withdraws_rebuilds_and_recounts(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    b = _aware([_turn(content="done", prompt_tokens=53000)], counts=[53000, 52000])   # 53000 >= 0.8*65536
    b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
           extra_tools=_tools(), tool_executor=executor)
    assert len(b._counter.seen) == 2 and len(b.payloads) == 1
    assert _names(b.payloads[0]) == sorted(["update_state", "schedule_event", "declare_quiet"])
    assert b.payloads[0]["max_tokens"] == 65536 - 1 - 52000
    note = [m for m in b.payloads[0]["messages"] if m["role"] == "user" and "withdrawn" in (m["content"] or "")]
    assert note and "53000" in note[0]["content"] and "server" in note[0]["content"]
    ev = _events(executor, "budget_pressure")
    assert ev[0]["action"] == "perception_tools_withdrawn" and ev[0]["prompt_tokens"] == 53000


def test_near_the_wall_all_tools_go_after_one_turn_and_the_budget_arrives(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    script = [_turn(tool_calls=[_tool_call("clock", {})], prompt_tokens=53000),
              _turn(tool_calls=[_tool_call("update_state", {"updates": {"n": 1}}, "u1")], prompt_tokens=54000),
              _turn(content="done", prompt_tokens=55000)]
    b = _aware(script, counts=[53000, 53000, 54000, 55000])
    b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
           extra_tools=_tools(), tool_executor=executor)
    last = b.payloads[-1]
    assert last["tool_choice"] == "none" and "tools" not in last
    room = 65536 - 1 - 55000
    assert last["max_tokens"] == room and last["reasoning_budget_tokens"] == room - REPLY_RESERVE_TOKENS - 20
    assert "reasoning_budget_tokens" not in b.payloads[-2]
    assert [e["action"] for e in _events(executor, "budget_pressure")][-1] == "generation_budgeted"


def test_three_turn_rule_holds_above_the_unrestricted_room(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    script = [_turn(tool_calls=[_tool_call("clock", {})], prompt_tokens=100)]
    for i in range(3):
        script.append(_turn(tool_calls=[_tool_call("update_state", {"updates": {"n": i}}, f"u{i}")], prompt_tokens=100))
    script.append(_turn(content="done", prompt_tokens=100))
    b = _aware(script, counts=[100] * 5, limit=1000)  # limit 1000: 850 threshold; room 899 < 32768
    b._counter.counts = [850, 850, 860, 861, 862]
    b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
           extra_tools=_tools(), tool_executor=executor)
    assert b.payloads[-1]["tool_choice"] == "none"
    assert b.payloads[-3]["tool_choice"] != "none"   # near-wall rule (1 turn) applied since room < 32768


def test_count_unavailable_fails_closed_with_no_request(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    b = _aware([_turn(content="never")], counts=[CountUnavailable("down")])
    with pytest.raises(CountUnavailable):
        b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
               extra_tools=_tools(), tool_executor=executor)
    assert b.payloads == [] and _events(executor, "budget_pressure")[-1]["action"] == "count_unavailable"


def test_exhausted_before_request_sends_nothing(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    b = _aware([_turn(content="never")], counts=[65536 - 1 - 100])
    with pytest.raises(ExhaustedBeforeRequest) as ei:
        b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
               extra_tools=_tools(), tool_executor=executor)
    assert b.payloads == [] and ei.value.max_tokens == 100
    assert _events(executor, "budget_pressure")[-1]["action"] == "exhausted_before_request"


def test_truncated_reply_carries_the_snapshot_after_accounting(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    b = _aware([_turn(content="first", tool_calls=[_tool_call("clock", {})], prompt_tokens=100),
                _turn(content="<think>cut", finish="length", prompt_tokens=200)], counts=[100, 200])
    with pytest.raises(TruncatedReply) as ei:
        b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
               extra_tools=_tools(), tool_executor=executor)
    e = ei.value
    assert e.text == "<think>cut" and e.message["content"] == "<think>cut" and e.turn_index == 1
    assert e.prompt_tokens == 200 and e.completion_tokens == 10
    assert e.account.input_tokens == 300 and e.account.output_tokens == 20 and len(e.account.responses) == 2
    assert e.account.interim_text == ["first"]


def test_truncation_is_typed_on_all_four_paths(tmp_path):
    cut = _turn(content="cut", finish="length")
    # single tool (terminal wake mode, no extra tools)
    b = _backend([json.loads(json.dumps(cut))]); b.wake_mode = "terminal"
    with pytest.raises(TruncatedReply):
        b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t")
    # multi-turn
    b = _backend([json.loads(json.dumps(cut))]); b.wake_mode = "terminal"
    with pytest.raises(TruncatedReply):
        b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
               extra_tools=_tools(), tool_executor=ToolExecutor(project_root=tmp_path, cycle=1))
    # terminal surface
    b = _backend([json.loads(json.dumps(cut))])
    with pytest.raises(TruncatedReply):
        b.call_terminal_surface(model="m", system="s", messages=[{"role": "user", "content": "hi"}],
                                experiment_label="t", terminal_surface=_terminal_surface_for_test())
    # natural: covered above


def test_single_tool_malformed_resend_is_recounted(tmp_path):
    bad = _turn(tool_calls=[{"id": "x", "type": "function", "function": {"name": "think_and_respond", "arguments": "{not json"}}],
                finish="tool_calls")
    good = _turn(tool_calls=[_tool_call("think_and_respond", {"response": "ok"})], finish="tool_calls")
    b = _aware([bad, good], counts=[100, 150], wake_mode="terminal")
    b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t")
    assert len(b._counter.seen) == 2 and b.payloads[1]["max_tokens"] == 65536 - 1 - 150
    assert b._counter.seen[1]["messages"] == b.payloads[1]["messages"]


def test_prepare_returns_the_exact_first_payload_and_call_prepared_sends_it(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    b = _aware([_turn(content="done", prompt_tokens=100)], counts=[100, 100])
    prep = b.prepare("m", "s", [{"role": "user", "content": "hi"}], _tools(), None, executor, candidate=True)
    assert prep.path == "natural" and prep.prompt_tokens == 100 and prep.sendable and prep.payload["model"] == "m"
    assert "max_tokens" not in prep.payload   # candidate mode leaves the payload unbounded
    b.call_prepared(prep)
    assert b.payloads[0]["messages"] == prep.payload["messages"] and b.payloads[0]["tools"] == prep.payload["tools"]
    assert b.payloads[0]["max_tokens"] == 65536 - 1 - 100


def test_prepare_candidate_reports_exhaustion_but_count_failure_raises(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    b = _aware([], counts=[65530])
    prep = b.prepare("m", "s", [{"role": "user", "content": "hi"}], _tools(), None, executor, candidate=True)
    assert prep.sendable is False and prep.reason == "exhausted_before_request"
    b = _aware([], counts=[CountUnavailable("down")])
    with pytest.raises(CountUnavailable):
        b.prepare("m", "s", [{"role": "user", "content": "hi"}], _tools(), None, executor, candidate=True)


def test_prepare_covers_the_terminal_surface_and_single_tool_paths(tmp_path):
    b = _aware([], counts=[10, 11], wake_mode="terminal")
    p = b.prepare("m", "s", [{"role": "user", "content": "hi"}], None, _terminal_surface_for_test(), None, candidate=True)
    assert p.path == "terminal_surface" and p.payload["tools"][0]["function"]["name"] == _terminal_surface_for_test()["tool_name"]
    p = b.prepare("m", "s", [{"role": "user", "content": "hi"}], None, None, None, candidate=True)
    assert p.path == "single_tool" and p.payload["tools"][0]["function"]["name"] == "think_and_respond"


def _terminal_surface_for_test():
    return {"tool_name": "complete_task", "description": "Complete the bounded scheduled task.",
            "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]},
            "tool_choice": "force"}
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_context_ceiling.py -q -p no:cacheprovider -k "counted or turn_zero or near_the_wall or three_turn or count_unavailable or exhausted or truncated or malformed_resend or prepare"`
Expected: FAIL (`context_policy` unknown kwarg, `TruncatedReply` not raised, …).

- [ ] **Step 3: Implement**

In `OpenAITasteBackend.__init__` add the keyword `context_policy: "ContextPolicyHolder | None" = None` and `http=None`, and after the existing `self._context_limit = context_limit` line:

```python
        from hamutay.context_policy import ContextPolicy, ContextPolicyHolder
        from hamutay.window import TokenCounter
        if context_policy is None:
            context_policy = ContextPolicyHolder(ContextPolicy.for_limit(context_limit, "explicit" if context_limit else "provider default"))
        self._policy_holder = context_policy
        self._http = http or _default_http
        root = self._policy_holder.current.tokenizer
        self._counter = TokenCounter(root, self._http) if root else None
```

Add a module-level `_default_http(method, url, body)` using `httpx.request(method, url, json=body, timeout=30.0).json()`, and on the backend:

```python
    @property
    def policy(self):
        return self._policy_holder.current

    @property
    def _context_limit(self) -> int | None:   # keep the old name for the tests and the session
        return self.policy.limit

    @_context_limit.setter
    def _context_limit(self, value):           # apply_context_limit's legacy path
        from hamutay.context_policy import ContextPolicy
        self._policy_holder.current = ContextPolicy.for_limit(value, "explicit")

    def _refresh_counter(self) -> None:
        from hamutay.window import TokenCounter
        root = self.policy.tokenizer
        if root and (self._counter is None or getattr(self._counter, "_root", None) != root):
            self._counter = TokenCounter(root, self._http)
        elif not root:
            self._counter = None

    def _take_response(self, data: dict, acct, *, turn_index: int) -> dict:
        """Account first, then judge the stop. One helper for all four paths."""
        from hamutay.window import TruncatedReply
        acct.responses.append(data)
        usage = data.get("usage") or {}
        acct.input_tokens += usage.get("prompt_tokens", 0) or 0
        acct.output_tokens += usage.get("completion_tokens", 0) or 0
        cr, cw = self._usage_cache(usage)
        acct.cache_read += cr
        acct.cache_write += cw
        choice = data["choices"][0]
        if (choice.get("finish_reason") or "unknown") == "length":
            message = choice.get("message", {}) or {}
            text = self._content_text(message.get("content")) + (message.get("reasoning_content") or "")
            raise TruncatedReply(text=text, message=message, turn_index=turn_index,
                                 prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
                                 completion_tokens=int(usage.get("completion_tokens", 0) or 0), account=acct)
        return data

    def _send(self, payload: dict, acct, *, turn_index: int, tool_choice_none: bool, tool_executor=None) -> dict:
        """Bound (window-aware doors), post, take. Every send on every path goes through here."""
        self._refresh_counter()
        policy = self.policy
        if policy.window_aware:
            from hamutay.window import CountUnavailable, ExhaustedBeforeRequest, bound_payload
            try:
                b = bound_payload(payload, policy, self._counter, configured_max_tokens=self._max_tokens,
                                  tool_choice_none=tool_choice_none)
            except CountUnavailable as e:
                self._log_pressure(tool_executor, "count_unavailable", error=e.error)
                raise
            except ExhaustedBeforeRequest as e:
                self._log_pressure(tool_executor, "exhausted_before_request", prompt_tokens=e.prompt_tokens,
                                   room=e.room, max_tokens=e.max_tokens, limit=e.limit)
                raise
            if b.budget_fields:
                self._log_pressure(tool_executor, "generation_budgeted", prompt_tokens=b.prompt_tokens, room=b.room,
                                   max_tokens=b.max_tokens, limit=policy.limit,
                                   forced_sequence_tokens=policy.forced_sequence_tokens, **b.budget_fields)
        data = self._post_chat(payload)
        return self._take_response(data, acct, turn_index=turn_index)

    @staticmethod
    def _log_pressure(tool_executor, action: str, **detail) -> None:
        if tool_executor is not None:
            tool_executor.log_event({"tool": "_framework", "event": "budget_pressure", "action": action, **detail})
```

Then, path by path, replace every `data = self._post_chat(payload)` with `data = self._send(payload, acct, turn_index=<n>, tool_choice_none=<payload's tool_choice == "none">, tool_executor=<executor or None>)`, create `acct = WakeAccount()` at the top of each path, delete each path's own `if raw_stop == "length": raise RuntimeError(...)` block and its own usage accumulation (read totals from `acct` when building `ExchangeResult`: `input_tokens=acct.input_tokens`, `output_tokens=acct.output_tokens`, `cache_read_tokens=acct.cache_read`, `cache_creation_tokens=acct.cache_write`, `**self._cost_kwargs(acct.responses)`; on the natural path also `interim_text=acct.interim_text or None` and append interim text to `acct.interim_text` where the loop appended to its local list). In `_call_single_tool`, the malformed-retry loop already mutates `payload["messages"]` and loops back: the loop's `_send` call recounts it. In `_call_natural`:

- replace `max_tokens: self._max_tokens` in `_build_payload` with nothing (the bound sets it; without a window-aware policy set `payload["max_tokens"] = self._max_tokens` in `_send` before posting so the no-ceiling golden holds byte-for-byte: keep the key in the same position by building the payload dict as today and only overwriting the value in `_send`);
- turn 0: when `policy.window_aware`, before the first `_send`, count the candidate payload (`self._counter.count(_build_payload())`); if `>= SOFT_THRESHOLD_FRACTION * limit` call `_withdraw_perception("soft threshold reached", measured=count, count_source="server")` and rebuild; the note text becomes `f"the next request counts {measured} tokens ({count_source}); the last measured request was {last_reported_prompt_tokens}"` (keep today's sentence for the no-ceiling estimate path);
- the three-turn rule: `limit_turns = WITHDRAWN_TOOL_TURNS_NEAR_WALL if (policy.window_aware and last_room < THINK_UNRESTRICTED_ROOM_TOKENS) else 3`, where `last_room` is `policy.limit - 1 - <last counted prompt>`; `all_withdrawn` sets `tool_choice: "none"` as today.

`prepare`/`call_prepared`:

```python
@dataclass
class Prepared:
    payload: dict
    prompt_tokens: int | None
    path: str
    sendable: bool
    reason: str | None
    inputs: dict          # model, system, messages, extra_tools, terminal_surface, tool_executor


    def _first_payload(self, path, model, system, messages, extra_tools, terminal_surface) -> dict:
        """The exact first payload `path` would send, built by the path's own code."""
        # factor each path's payload construction into _first_payload_single_tool /
        # _first_payload_terminal_surface / _first_payload_multi_turn / _first_payload_natural
        # (pure functions of these arguments) and call them from both here and the paths.

    def _path_for(self, extra_tools, terminal_surface) -> str:
        if terminal_surface is not None:
            return "terminal_surface"
        if self.wake_mode == "natural":
            return "natural"
        return "multi_turn" if extra_tools else "single_tool"

    def prepare(self, model, system, messages, extra_tools, terminal_surface, tool_executor, *, candidate=False):
        from hamutay.window import bound_payload
        path = self._path_for(extra_tools, terminal_surface)
        payload = self._first_payload(path, model, system, messages, extra_tools or [], terminal_surface)
        inputs = dict(model=model, system=system, messages=messages, extra_tools=extra_tools,
                      terminal_surface=terminal_surface, tool_executor=tool_executor)
        self._refresh_counter()
        if not self.policy.window_aware:
            return Prepared(payload, None, path, True, None, inputs)
        b = bound_payload(json.loads(json.dumps(payload)), self.policy, self._counter,
                          configured_max_tokens=self._max_tokens,
                          tool_choice_none=payload.get("tool_choice") == "none", candidate=True)
        if not b.sendable and not candidate:
            from hamutay.window import ExhaustedBeforeRequest
            raise ExhaustedBeforeRequest(prompt_tokens=b.prompt_tokens, limit=self.policy.limit, room=b.room, max_tokens=b.max_tokens)
        return Prepared(payload, b.prompt_tokens, path, b.sendable, b.reason, inputs)

    def call_prepared(self, prepared: Prepared) -> ExchangeResult:
        i = prepared.inputs
        if prepared.path == "terminal_surface":
            return self.call_terminal_surface(model=i["model"], system=i["system"], messages=i["messages"],
                                              experiment_label="prepared", terminal_surface=i["terminal_surface"])
        return self.call(model=i["model"], system=i["system"], messages=i["messages"], experiment_label="prepared",
                         extra_tools=i["extra_tools"], tool_executor=i["tool_executor"])
```

Because each path builds its first payload through the same `_first_payload_*` function `prepare` used, the first send equals `prepared.payload` byte for byte before bounding; `_send` then bounds it (the test asserts messages/tools equality and the bound `max_tokens`).

- [ ] **Step 4: Run the ceiling tests, the goldens, and the unit suites**

Run: `uv run pytest tests/test_context_ceiling.py tests/test_window_golden.py tests/unit/test_events.py tests/test_heartbeat.py -q -p no:cacheprovider`
Expected: all passed; `test_no_ceiling_length_failure_differs_only_in_the_four_declared_places` still passes (the session record changes land in Task 5; until then the record is unchanged except `error_type`, which is allowed).

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/taste_open.py tests/test_context_ceiling.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "window: every send counted and bounded, accounting before the stop check, typed truncation on all four paths, prepare/call_prepared (spec §1, §4)"
```

---

### Task 5: The session: policy holder, lean rendering, the failure record, `apply_context_limit`

**Files:**
- Modify: `src/hamutay/taste_open.py` (`_build_messages`, `OpenTasteSession.__init__`, `_exchange_impl` failure branch, `_log_entry`, `apply_context_limit`)
- Test: `tests/test_context_ceiling.py` (extend), `tests/test_window_golden.py` (unchanged, must pass)

**Interfaces:**
- Produces: `_build_messages(..., lean_activity_log: bool = False, omit_activity_log: bool = False)`; `OpenTasteSession.context_policy -> ContextPolicy`; `OpenTasteSession._policy_holder` (the backend's holder when the backend has one, else a new one); `apply_context_limit(limit, source, invocation_id)` builds `ContextPolicy.for_launch(limit, source, backend base_url, http=backend._http, model=self._model, invocation_id=invocation_id, cached=<previous probe>)` then assigns once, then `_launch_config` and the observation; failure record on `TruncatedReply`: `failure_classification.truncated_reply`, `usage` from `e.account`, `interim_text` from `e.account.interim_text`; `_log_entry(..., admission: dict | None = None, context_policy_invocation: str | None = None)`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_context_ceiling.py`)

```python
from hamutay.taste_open import OpenTasteSession, _build_messages


def _state_with_log():
    return {"cycle": 2, "k": "v", "_activity_log": [{"cycle": 2, "timestamp": "t", "tool": "clock", "reason": "r",
                                                     "result_summary": "s", "parameters": {"p": 1}, "result_hash": "h"}]}


def _state_section(system: str) -> dict:
    head = system.index("## Your state from cycle")
    body = system[head:].split("\n", 2)[2]
    if body.startswith("(_activity_log"):
        body = body.split("\n", 1)[1]
    return json.loads(body.split("\n## ")[0])


def test_lean_activity_log_rendering_is_structural_and_leaves_the_state_untouched():
    st = _state_with_log(); before = json.dumps(st)
    _, system = _build_messages(st, "u", 3, tools_enabled=True, wake_mode="natural", lean_activity_log=True)
    assert json.dumps(st) == before
    parsed = _state_section(system)
    assert list(parsed["_activity_log"][0]) == ["cycle", "timestamp", "tool", "reason", "result_summary"]
    assert "(_activity_log is shown without parameters; the record has them)" in system
    _, plain = _build_messages(st, "u", 3, tools_enabled=True, wake_mode="natural")
    assert "parameters" in plain and "(_activity_log is shown" not in plain
    _, omitted = _build_messages(st, "u", 3, tools_enabled=True, wake_mode="natural", omit_activity_log=True)
    assert "_activity_log" not in _state_section(omitted) and "(_activity_log is omitted" in omitted


def test_session_records_a_truncated_reply_with_real_usage_once(tmp_path):
    b = _aware([_turn(content="first", tool_calls=[_tool_call("clock", {})], prompt_tokens=100),
                _turn(content="<think>cut", finish="length", prompt_tokens=200)], counts=[100, 200])
    log = tmp_path / "s.jsonl"
    s = OpenTasteSession(model="m", backend=b, log_path=str(log), experiment_label="t", enable_tools=True, project_root=tmp_path)
    s.seed_state({"cycle": 1}, 1)
    with pytest.raises(TruncatedReply):
        s.exchange("hi")
    rec = json.loads(log.read_text().splitlines()[-1])
    fc = rec["failure_classification"]
    assert fc["error_type"] == "TruncatedReply" and fc["truncated_reply"]["text"] == "<think>cut"
    assert fc["truncated_reply"]["trusted"] is False and fc["truncated_reply"]["turn_index"] == 1
    assert rec["usage"]["input_tokens"] == 300 and rec["usage"]["output_tokens"] == 20 and rec["usage"]["stop_reason"] == "max_tokens"
    assert rec["interim_text"] == ["first"] and json.dumps(rec).count("<think>cut") == 1
    assert rec["context_policy_invocation"] is None or isinstance(rec["context_policy_invocation"], str)


def test_session_context_policy_is_the_backends_holder_and_replaces_once(tmp_path, monkeypatch):
    from hamutay.context_policy import ContextPolicy
    b = _aware([], counts=[])
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t")
    assert s.context_policy is b.policy
    seen = []
    monkeypatch.setattr(ContextPolicy, "for_launch", classmethod(
        lambda cls, limit, source, base_url, **kw: seen.append((limit, source, kw.get("invocation_id"))) or
        ContextPolicy(limit, source, limit, "http://127.0.0.1:8081", "probed", {"build_info": "x"}, 20, kw.get("invocation_id"))))
    s.apply_context_limit(32768, "discovered", "inv-1")
    assert seen == [(32768, "discovered", "inv-1")]
    assert b.policy.limit == 32768 and s.context_policy.invocation_id == "inv-1"
    assert s._launch_config["context_limit"] == 32768 and s._launch_config["context_policy"]["limit"] == 32768
    last = json.loads((tmp_path / "s.jsonl").read_text().splitlines()[-1])
    assert last["record_type"] == "substrate_observation" and last["context_limit"] == 32768


def test_apply_context_limit_keeps_the_old_policy_when_the_probe_raises(tmp_path, monkeypatch):
    from hamutay.context_policy import ContextPolicy
    b = _aware([], counts=[])
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t")
    old = s.context_policy
    def boom(cls, *a, **k):
        raise RuntimeError("probe failed")
    monkeypatch.setattr(ContextPolicy, "for_launch", classmethod(boom))
    s.apply_context_limit(32768, "discovered", "inv-2")
    assert s.context_policy is old
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_context_ceiling.py -q -p no:cacheprovider -k "lean_activity or records_a_truncated or holder_and_replaces or old_policy"`
Expected: FAIL.

- [ ] **Step 3: Implement**

`_build_messages`: add `lean_activity_log: bool = False, omit_activity_log: bool = False`; when either is set, render `prior_state`, `memory_state` and `curator_context` through `lean_activity_logs(...)` (from `hamutay.window`) or, for omit, through a copy with every `_activity_log` key removed at any depth (write `_drop_activity_logs(obj)` beside `lean_activity_logs` in `window.py`, same walk, deleting the key); under the `## Your state from cycle N` heading insert the one-line note `(_activity_log is shown without parameters; the record has them)` or `(_activity_log is omitted from this compact wake; the record has it)` before the JSON. With neither flag the output is byte-identical (the golden test guards it).

`OpenTasteSession.__init__`: after `self._backend = ...`, `self._policy_holder = getattr(self._backend, "_policy_holder", None) or ContextPolicyHolder(ContextPolicy.none())`; property `context_policy` returns `self._policy_holder.current`. In `_exchange_impl` pass `lean_activity_log=self.context_policy.window_aware` (Task 6 adds `omit_activity_log` for compact runs) to `_build_messages`.

Failure branch (`except Exception as e:` around `self._backend.call`): 

```python
                from hamutay.window import TruncatedReply
                usage = {"input_tokens": 0, "output_tokens": 0, "stop_reason": "error"}
                interim = None
                if isinstance(e, TruncatedReply):
                    a = e.account
                    usage = {"input_tokens": a.input_tokens, "output_tokens": a.output_tokens,
                             "cache_read_input_tokens": a.cache_read, "cache_creation_input_tokens": a.cache_write,
                             "stop_reason": "max_tokens", **_cost_usage_fields_from_responses(a.responses)}
                    interim = list(a.interim_text) or None
                    failure_classification["truncated_reply"] = {
                        "text": e.text, "message": e.message, "turn_index": e.turn_index,
                        "prompt_tokens": e.prompt_tokens, "completion_tokens": e.completion_tokens, "trusted": False}
                self._last_usage = {"input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"]}
                self._log_entry(..., usage=usage, interim_text=interim, failure_classification=failure_classification,
                                context_policy_invocation=self.context_policy.invocation_id)
```

(`_cost_usage_fields_from_responses` = the backend's `_cost_kwargs(responses)` mapped through the existing `_cost_usage_fields` helper.) `_log_entry` gains `admission: dict | None = None` and `context_policy_invocation: str | None = None` and writes both keys **only when not None** (byte-identity for no-ceiling records) — except that every record on a window-aware door carries `context_policy_invocation`.

`apply_context_limit`:

```python
    def apply_context_limit(self, limit: int, source: str, invocation_id: str) -> None:
        from hamutay.context_policy import ContextPolicy
        old = self._policy_holder.current
        base_url = getattr(self._backend, "_base_url", None)
        http = getattr(self._backend, "_http", None)
        try:
            new = ContextPolicy.for_launch(limit, source, base_url, http=http, model=self._model,
                                           invocation_id=invocation_id, cached=old.probe)
        except Exception as e:
            print(f"  context policy: kept the previous value; rebuilding failed: {e}")
            return
        self._policy_holder.current = new          # the one assignment
        if self._launch_config is None:
            self._launch_config = {}
        self._launch_config["context_limit"] = limit
        self._launch_config["context_limit_source"] = source
        self._launch_config["context_policy"] = new.as_dict()
        self.append_substrate_observation(context_limit=limit, source=source, invocation_id=invocation_id)
```

- [ ] **Step 4: Run**

Run: `uv run pytest tests/test_context_ceiling.py tests/test_window_golden.py tests/unit/test_events.py tests/test_heartbeat.py tests/gpu_lease_validation -q -p no:cacheprovider`
Expected: all passed (the gpu-lease validation exercises `apply_context_limit` through the gate; with a fake `_discover` and no real server, `for_launch` returns `for_limit` because `/props` fails; that keeps the gate's `_context_validated` semantics).

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/taste_open.py src/hamutay/window.py tests/test_context_ceiling.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "window: the session owns the policy holder, renders the activity log lean, records a truncated reply with real usage, rebuilds the policy before one assignment (spec §3, §4, 'The context policy')"
```

---

### Task 6: The envelope projection, the `envelope(cap)` closure, admission at the prepared wake

**Files:**
- Modify: `src/hamutay/events.py` (`build_event_envelope`, `run_next_event`, `EventStore._build_completed`, `append_failed`), `src/hamutay/taste_open.py` (`exchange`/`_exchange_impl`)
- Test: `tests/unit/test_events.py` (extend), `tests/test_context_ceiling.py` (extend)

**Interfaces:**
- Consumes: Task 3 `project_context_results`, Task 4 `prepare`/`call_prepared`, Task 5 session policy.
- Produces: `build_event_envelope(event, context_results, run_id, operational_notes=None, *, policy=None, cap_chars=None)` (with `policy.window_aware`: results projected at `cap_chars` (default `policy.result_cap_chars // 2`); argument never mutated); `run_next_event(..., compact: bool | None = None)` passes `session.exchange(envelope_text, ..., envelope=<closure>, compact=<event detail flag>)`; `OpenTasteSession.exchange(user_message, *, envelope: Callable[[int | None], str] | None = None, compact: bool = False, ...)`; admission in `_exchange_impl`: with `envelope` and a window-aware policy, `prepare(candidate=True)` per pass, cap halved from `policy.result_cap_chars // 2`, at most `ADMISSION_MAX_PASSES`, stop under `ADMISSION_TARGET_FRACTION * limit` or at all-stubs (cap 0); `budget_pressure / envelope_admission` per pass; `admission = {passes, final_cap, prompt_tokens, over_target, envelope_exhausted}` on the session record and returned to the runner through `session._last_admission`; the final rendered envelope is the record's `user_message`; `_build_completed(..., admission=None)` and `append_failed(..., admission=None)` write the key when given; compact runs: cap 0 from the first pass and `omit_activity_log=True`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_events.py`:

```python
def test_build_event_envelope_projects_without_mutating_and_records_keep_full_results():
    from hamutay.context_policy import ContextPolicy
    from hamutay.events import build_event_envelope
    big = {"request": {"tool": "recall", "cycle": 1},
           "result": {"cycle": 1, "content": {"x": "y" * 4000, "_activity_log": [{"tool": "t", "parameters": {"p": 1}}]}}}
    results = [big]
    before = json.dumps(results)
    policy = ContextPolicy(65536, "discovered", 65536, "http://127.0.0.1:8081", "probed", {}, 20)
    env = build_event_envelope(_event_record(), results, "run", policy=policy, cap_chars=1000)
    assert json.dumps(results) == before
    body = json.loads(env)
    assert body["context_results"][0]["result"]["truncated"] is True and "parameters" not in env
    plain = build_event_envelope(_event_record(), results, "run")
    assert "parameters" in plain
    store = EventStore(Path(tmp_path_dir := __import__("tempfile").mkdtemp()) / "e.jsonl")
    rec = store.append_completed(event=_event_record(), run_id="run", wake_cycle=1, result_record_id=UUID(int=1),
                                 response_text="ok", context_results=results, admission={"passes": 2})
    assert rec["context_results"][0]["result"]["content"]["_activity_log"][0]["parameters"] == {"p": 1}
    assert rec["admission"] == {"passes": 2}
```

Append to `tests/test_context_ceiling.py`:

```python
def test_admission_halves_the_cap_from_the_full_results_until_under_target(tmp_path):
    b = _aware([_turn(content="done", prompt_tokens=100)], counts=[40000, 33000, 30000, 30000])   # 3 candidate counts + 1 send
    log = tmp_path / "s.jsonl"
    s = OpenTasteSession(model="m", backend=b, log_path=str(log), experiment_label="t", enable_tools=True, project_root=tmp_path)
    s.seed_state({"cycle": 1}, 1)
    caps = []

    def envelope(cap):
        caps.append(cap)
        return json.dumps({"purpose": "p", "context_results": [{"result": "x" * (cap or 100000)}]})
    s.exchange("ignored", envelope=envelope)
    assert caps == [32768, 16384, 8192] and s._last_admission == {
        "passes": 3, "final_cap": 8192, "prompt_tokens": 30000, "over_target": False, "envelope_exhausted": False}
    rec = json.loads(log.read_text().splitlines()[-1])
    assert rec["admission"]["passes"] == 3 and rec["user_message"] == envelope(8192)
    assert b.payloads[0]["messages"][-1]["content"] == envelope(8192)


def test_admission_stops_at_all_stubs_and_reports_over_target(tmp_path):
    b = _aware([_turn(content="done", prompt_tokens=100)], counts=[40000] * 9 + [40000])
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t",
                         enable_tools=True, project_root=tmp_path)
    s.seed_state({"cycle": 1}, 1)
    s.exchange("ignored", envelope=lambda cap: json.dumps({"cap": cap}))
    a = s._last_admission
    assert a["over_target"] is True and a["envelope_exhausted"] is True and a["final_cap"] == 0 and a["passes"] <= 8


def test_admission_first_candidate_below_the_floor_is_not_an_error(tmp_path):
    b = _aware([_turn(content="done", prompt_tokens=100)], counts=[65000, 30000, 30000])
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t",
                         enable_tools=True, project_root=tmp_path)
    s.seed_state({"cycle": 1}, 1)
    s.exchange("ignored", envelope=lambda cap: json.dumps({"cap": cap}))
    assert s._last_admission["passes"] == 2 and b.payloads


def test_compact_wake_omits_the_activity_log_and_starts_at_stubs(tmp_path):
    b = _aware([_turn(content="done", prompt_tokens=100)], counts=[100, 100])
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t",
                         enable_tools=True, project_root=tmp_path)
    s.seed_state(_state_with_log(), 2)
    caps = []
    s.exchange("ignored", envelope=lambda cap: caps.append(cap) or json.dumps({"cap": cap}), compact=True)
    assert caps == [0] and "_activity_log" not in _state_section(b.payloads[0]["messages"][0]["content"])
    assert "(_activity_log is omitted" in b.payloads[0]["messages"][0]["content"]


def test_no_envelope_or_no_window_means_no_admission(tmp_path):
    b = _backend([_turn(content="done")])
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t")
    s.exchange("plain")
    assert s._last_admission is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/unit/test_events.py tests/test_context_ceiling.py -q -p no:cacheprovider -k "envelope_projects or admission or compact_wake or no_envelope"`
Expected: FAIL.

- [ ] **Step 3: Implement**

`build_event_envelope`: add `*, policy=None, cap_chars=None`; if `policy is not None and policy.window_aware`: `cap = cap_chars if cap_chars is not None else policy.result_cap_chars // 2`; `context_results = project_context_results(context_results, cap)`; else unchanged (the envelope JSON is built from the projected list; the caller's list is never touched).

`run_next_event`: after `context_results` is resolved, 

```python
        policy = getattr(session, "context_policy", None)
        notes = operational_notes_for_event(store.read_records(), event, now=now or datetime.now(timezone.utc))
        full = context_results
        def envelope(cap):
            return build_event_envelope(event, full, run_id, operational_notes=notes, policy=policy, cap_chars=cap)
        compact = bool((event.get("detail") or {}).get("compact_context"))
        response = session.exchange(envelope(None if not compact else 0), force_memory=None,
                                    terminal_surface=event.get("terminal_surface"), event_managed=True,
                                    wake_context=wake_context, envelope=envelope, compact=compact)
        ...
        completed = store.append_completed_atomic(..., admission=getattr(session, "_last_admission", None))
    except Exception as e:
        store.append_failed(event=event, run_id=run_id, exc=e, context_results=context_results,
                            admission=getattr(session, "_last_admission", None))
        raise
```

`exchange`/`_exchange_impl`: add `envelope=None, compact=False`; `self._last_admission = None` at the start of every exchange; when `envelope is not None and self.context_policy.window_aware`: 

```python
            policy = self.context_policy
            cap = 0 if compact else policy.result_cap_chars // 2
            target = int(ADMISSION_TARGET_FRACTION * policy.limit)
            passes = 0; prep = None
            while True:
                passes += 1
                user_message = envelope(cap)
                messages, system = _build_messages(...same args..., lean_activity_log=True, omit_activity_log=compact)
                prep = self._backend.prepare(self._model, system, messages, extra_tools, terminal_surface, tool_executor, candidate=True)
                if tool_executor is not None:
                    tool_executor.log_event({"tool": "_framework", "event": "budget_pressure", "action": "envelope_admission",
                                             "pass": passes, "cap_chars": cap, "prompt_tokens": prep.prompt_tokens, "target": target})
                if prep.prompt_tokens <= target or cap == 0 or passes >= ADMISSION_MAX_PASSES:
                    break
                cap = cap // 2 if cap // 2 >= MIN_STUB_CHARS else 0
            self._last_admission = {"passes": passes, "final_cap": cap, "prompt_tokens": prep.prompt_tokens,
                                    "over_target": prep.prompt_tokens > target, "envelope_exhausted": cap == 0}
            if not prep.sendable:
                prep = self._backend.prepare(..., candidate=False)   # raises ExhaustedBeforeRequest, recorded by the failure branch
            result = self._backend.call_prepared(prep)
```

(the `try/except` failure branch wraps the whole block as it wraps `self._backend.call` today; `user_message` for the record is the final `envelope(cap)` string.) `_log_entry(..., admission=self._last_admission)` on success and failure. Without `envelope` or without a window-aware policy the code path is exactly today's (`_build_messages` + `self._backend.call`), plus `lean_activity_log=policy.window_aware`.

`_build_completed`/`append_failed`: `admission: dict | None = None` → `record["admission"] = admission` when not None.

- [ ] **Step 4: Run**

Run: `uv run pytest tests/unit/test_events.py tests/test_context_ceiling.py tests/test_window_golden.py tests/test_event_ingress.py tests/test_heartbeat.py -q -p no:cacheprovider`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/events.py src/hamutay/taste_open.py tests/unit/test_events.py tests/test_context_ceiling.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "window: the envelope is a deep-copied typed projection built by a closure; admission at the prepared wake counts the exact payload (spec §2)"
```

---

### Task 7: The store: fsynced appends, `append_failed_with_retry`, the one compact retry

**Files:**
- Modify: `src/hamutay/events.py` (`EventStore._append_unlocked`, `append_many`'s write, new `append_failed_with_retry`, `has_compact_retry`, `run_next_event`'s except)
- Test: `tests/unit/test_events.py` (extend)

**Interfaces:**
- Produces: `EventStore._append_unlocked(record)` writes, flushes, fsyncs, verifies growth (raises `OSError` on a short write); `EventStore.has_compact_retry(event_id) -> bool`; `EventStore.append_failed_with_retry(*, event, run_id, exc, context_results=None, admission=None, reason: str) -> tuple[dict, dict | None]` (one locked write of the `failed` row and the compact pending copy; the copy carries `detail={"compact_context": True, "retry_of_run": run_id, "reason": reason}` plus the original event's fields, `status: "pending"`, `created_at` now; re-checks under the lock and appends only `failed` if a compact row exists); `run_next_event`: on `WindowFailure` with `session.context_policy.window_aware` and no compact retry yet → `append_failed_with_retry`, else `append_failed`.

- [ ] **Step 1: Write the failing tests** (append to `tests/unit/test_events.py`)

```python
def test_append_unlocked_fsyncs_and_verifies_growth(tmp_path, monkeypatch):
    import os
    store = EventStore(tmp_path / "events.jsonl")
    synced = []
    monkeypatch.setattr(os, "fsync", lambda fd: synced.append(fd))
    store.append(_event_record())
    assert synced
    real_write = open  # a short write: patch the file object's write to write half
    class Short:
        def __init__(self, f): self.f = f
        def write(self, s): return self.f.write(s[: len(s) // 2])
        def flush(self): return self.f.flush()
        def fileno(self): return self.f.fileno()
        def __enter__(self): return self
        def __exit__(self, *a): return self.f.__exit__(*a)
    monkeypatch.setattr(Path, "open", lambda self, mode="r", **k: Short(real_write(self, mode, **k)) if "a" in mode else real_write(self, mode, **k))
    with pytest.raises(OSError):
        store.append(_event_record())


def test_append_failed_with_retry_writes_two_rows_once(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    ev = _event_record(); store.append(ev)
    _, running = store.claim_next_pending()
    failed, retry = store.append_failed_with_retry(event=ev, run_id=running["run_id"], exc=RuntimeError("cut"),
                                                   reason="truncated_reply")
    rows = store.read_records()
    assert [r["status"] for r in rows] == ["pending", "running", "failed", "pending"]
    assert retry["detail"] == {"compact_context": True, "retry_of_run": running["run_id"], "reason": "truncated_reply"}
    assert retry["event_id"] == ev["event_id"] and retry["purpose"] == ev["purpose"] and retry["created_at"] != ev["created_at"]
    assert store.has_compact_retry(ev["event_id"])
    _, running2 = store.claim_next_pending()
    failed2, retry2 = store.append_failed_with_retry(event=retry, run_id=running2["run_id"], exc=RuntimeError("cut"),
                                                     reason="truncated_reply")
    assert retry2 is None and [r["status"] for r in store.read_records()][-2:] == ["running", "failed"]


def test_a_failed_row_without_its_retry_reads_as_terminal(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    ev = _event_record(); store.append(ev)
    _, running = store.claim_next_pending()
    store.append_failed(event=ev, run_id=running["run_id"], exc=RuntimeError("x"))
    assert store.claim_next_pending() is None and not store.has_compact_retry(ev["event_id"])


def test_run_next_event_retries_a_window_failure_once(tmp_path, monkeypatch):
    from hamutay.context_policy import ContextPolicy
    from hamutay.events import run_next_event
    from hamutay.window import ExhaustedBeforeRequest
    store = EventStore(tmp_path / "events.jsonl"); store.append(_event_record())
    calls = []

    class S:
        _prior_states = []; _bridge = None; _state = {}; cycle = 1; _last_admission = None
        context_policy = ContextPolicy(65536, "discovered", 65536, "http://127.0.0.1:8081", "probed", {}, 20)
        def exchange(self, msg, **kw):
            calls.append(kw.get("compact"))
            raise ExhaustedBeforeRequest(prompt_tokens=65000, limit=65536, room=535, max_tokens=535)
    with pytest.raises(ExhaustedBeforeRequest):
        run_next_event(S(), store)
    assert [r["status"] for r in store.read_records()] == ["pending", "running", "failed", "pending"]
    with pytest.raises(ExhaustedBeforeRequest):
        run_next_event(S(), store)
    assert calls == [False, True] and [r["status"] for r in store.read_records()][-1] == "failed"
    assert store.claim_next_pending() is None


def test_run_next_event_does_not_retry_without_a_window(tmp_path):
    from hamutay.context_policy import ContextPolicy
    from hamutay.events import run_next_event
    from hamutay.window import TruncatedReply, WakeAccount
    store = EventStore(tmp_path / "events.jsonl"); store.append(_event_record())

    class S:
        _prior_states = []; _bridge = None; _state = {}; cycle = 1; _last_admission = None
        context_policy = ContextPolicy.none()
        def exchange(self, msg, **kw):
            raise TruncatedReply(text="t", message={}, turn_index=0, prompt_tokens=1, completion_tokens=1, account=WakeAccount())
    with pytest.raises(TruncatedReply):
        run_next_event(S(), store)
    assert [r["status"] for r in store.read_records()] == ["pending", "running", "failed"]


def test_boot_recovery_of_a_crashed_compact_run_stays_compact(tmp_path):
    from hamutay.heartbeat import recover_orphaned_running
    store = EventStore(tmp_path / "events.jsonl")
    ev = _event_record(); store.append(ev)
    _, running = store.claim_next_pending()
    _, retry = store.append_failed_with_retry(event=ev, run_id=running["run_id"], exc=RuntimeError("x"), reason="count_unavailable")
    store.claim_next_pending()                      # the compact run starts, then the process dies
    recovered = recover_orphaned_running(store)
    assert len(recovered) == 1 and recovered[0]["detail"]["compact_context"] is True
    assert recovered[0]["recovered_from_run_id"] == store.read_records()[-2]["run_id"]
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/unit/test_events.py -q -p no:cacheprovider -k "fsyncs or with_retry or without_its_retry or retries_a_window or not_retry_without or crashed_compact"`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
    def _append_unlocked(self, record: dict) -> None:
        self._write_lines_unlocked([json.dumps(record, default=str) + "\n"])

    def _write_lines_unlocked(self, lines: list[str]) -> None:
        """One buffer: write, flush, fsync, verify growth (Ledger.append_unlocked's discipline)."""
        data = "".join(lines)
        before = self.path.stat().st_size if self.path.exists() else 0
        with self.path.open("a") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        after = self.path.stat().st_size
        if after - before != len(data.encode()):
            raise OSError(f"short write to {self.path}: expected +{len(data.encode())}, got +{after - before}")

    def has_compact_retry(self, event_id: str) -> bool:
        return any(r.get("record_type") == "event_status" and r.get("event_id") == event_id
                   and (r.get("detail") or {}).get("compact_context") for r in self.read_records())

    def append_failed_with_retry(self, *, event: dict, run_id: str, exc: Exception, reason: str,
                                 context_results=None, admission=None) -> tuple[dict, dict | None]:
        failed = {"record_type": "event_status", "event_id": event["event_id"],
                  "event_type": event.get("event_type", EVENT_TYPE_REFLECTION), "status": "failed",
                  "run_id": run_id, "failed_at": utc_now_iso(), "error_type": type(exc).__name__, "error": str(exc)}
        if context_results is not None:
            failed["context_results"] = context_results
        if admission is not None:
            failed["admission"] = admission
        with self._locked():
            records = self._read_records_unlocked()
            exists = any(r.get("event_id") == event["event_id"] and (r.get("detail") or {}).get("compact_context")
                         for r in records)
            if exists:
                self._append_unlocked(failed)
                return failed, None
            retry = {k: v for k, v in event.items() if k not in ("status", "run_id", "started_at", "recovered_by",
                                                                  "recovered_at", "recovered_from_run_id")}
            retry.update({"status": "pending", "created_at": utc_now_iso(),
                          "detail": {**(event.get("detail") or {}), "compact_context": True,
                                     "retry_of_run": run_id, "reason": reason}})
            self._write_lines_unlocked([json.dumps(failed, default=str) + "\n", json.dumps(retry, default=str) + "\n"])
        return failed, retry
```

(`append_many` should call `_write_lines_unlocked` too, so the completed+continuation batch gets the same discipline.) In `run_next_event`'s `except Exception as e:`:

```python
        from hamutay.window import WindowFailure
        policy = getattr(session, "context_policy", None)
        admission = getattr(session, "_last_admission", None)
        if isinstance(e, WindowFailure) and policy is not None and policy.window_aware \
                and not store.has_compact_retry(event["event_id"]):
            reason = {"CountUnavailable": "count_unavailable", "ExhaustedBeforeRequest": "exhausted_before_request",
                      "TruncatedReply": "truncated_reply"}.get(type(e).__name__, "window_failure")
            store.append_failed_with_retry(event=event, run_id=run_id, exc=e, reason=reason,
                                           context_results=context_results, admission=admission)
        else:
            store.append_failed(event=event, run_id=run_id, exc=e, context_results=context_results, admission=admission)
        raise
```

- [ ] **Step 4: Run**

Run: `uv run pytest tests/unit/test_events.py tests/test_heartbeat.py tests/test_event_ingress.py tests/assembly tests/assembly_validation -q -p no:cacheprovider`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/events.py tests/unit/test_events.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "window: fsynced store appends, the failed-plus-compact-retry row pair in one write, one deliberate retry per event (spec §6)"
```

---

### Task 8: The close pass is attempt-aware

**Files:**
- Modify: `src/hamutay/assembly/close.py` (`_runs_by_event`, `eligible_positions`, `try_close` step 2)
- Test: `tests/assembly/test_close.py` (extend)

**Interfaces:**
- Produces: `_runs_by_event(records) -> dict[event_id, dict[run_id, {"status": str, "started_at": str | None, "superseded": bool}]]` (superseded when a later pending row for the event carries top-level `recovered_from_run_id == run_id` or `detail.recovered_from_run_id == run_id` or `detail.retry_of_run == run_id`); `eligible_positions` classifies `wake_failed` when the position's own run has terminal status `failed`; `try_close` computes `running_at_cutoff` from runs that are `running`, started before `closes_at`, and not superseded.

- [ ] **Step 1: Write the failing tests** (append to `tests/assembly/test_close.py`; use the file's `house` fixture and `_wake_and_position` helper; read them first)

```python
def _compact_retry(store, event, run_id):
    return store.append_failed_with_retry(event=event, run_id=run_id, exc=RuntimeError("cut"), reason="truncated_reply")[1]


def test_a_compact_pending_row_does_not_hide_the_failed_first_attempts_position(house):
    led, cfg, bindings, q = house
    # north: position recorded by a run that then failed with a window failure and got a compact retry
    ev, running = _wake_and_position(led, cfg, bindings, q, "north", "assent", at=T0, complete=False)
    store = EventStore(Path(cfg.members["north"].events))
    _compact_retry(store, ev, running["run_id"])
    with led.locked():
        closing = try_close(led, reduce(led.read_unlocked()), reduce(led.read_unlocked()).questions[q["question_id"]],
                            now=T0 + timedelta(days=1, seconds=1), actor="t")
    assert closing["tally"]["position_from_failed_wake"] == ["north"] and closing["tally"]["cap"].startswith("cap:position_from_failed_wake")


def test_a_compact_completion_without_a_position_leaves_the_cap_and_with_one_replaces_it(house):
    led, cfg, bindings, q = house
    ev, running = _wake_and_position(led, cfg, bindings, q, "north", "dissent", at=T0, complete=False)
    store = EventStore(Path(cfg.members["north"].events))
    retry = _compact_retry(store, ev, running["run_id"])
    _, running2 = store.claim_next_pending(now=T0 + timedelta(minutes=1))
    store.append_completed(event=retry, run_id=running2["run_id"], wake_cycle=2, result_record_id=uuid4(), response_text="quiet")
    with led.locked():
        view = reduce(led.read_unlocked())
        closing = try_close(led, view, view.questions[q["question_id"]], now=T0 + timedelta(days=1, seconds=1), actor="t")
    assert closing["tally"]["position_from_failed_wake"] == ["north"]
    # now a house where the compact run records a replacement position
    led2, cfg2, bindings2, q2 = house_factory_second(house) if "house_factory_second" in globals() else (None,) * 4
```

(Replace the last two lines with a second `house` scenario using the fixture's factory if the file has one; otherwise write the replacement case as its own test that reuses `_wake_and_position` for the compact run: the position from the compact run, when its run completes with the joined record, must be the active one and the tally must show no `position_from_failed_wake`.)

```python
def test_a_recovered_orphan_run_is_superseded_and_not_running_at_cutoff(house):
    from hamutay.heartbeat import recover_orphaned_running
    led, cfg, bindings, q = house
    store = EventStore(Path(cfg.members["north"].events))
    run_outbox(led, reduce(led.read_unlocked()), now=T0)
    ev, running = store.claim_next_pending(now=T0)              # the wake starts, the process dies
    recovered = recover_orphaned_running(store)                  # boot recovery re-pends it
    ev2, running2 = store.claim_next_pending(now=T0 + timedelta(minutes=5))
    store.append_completed(event=recovered[0], run_id=running2["run_id"], wake_cycle=2, result_record_id=uuid4(), response_text="ok")
    with led.locked():
        view = reduce(led.read_unlocked())
        closing = try_close(led, view, view.questions[q["question_id"]], now=T0 + timedelta(days=1, seconds=1), actor="t")
    assert closing is not None and "north" not in closing["tally"]["running_at_cutoff"]
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/assembly/test_close.py -q -p no:cacheprovider -k "compact or recovered_orphan"`
Expected: FAIL (`append_failed_with_retry` exists from Task 7; the classification is wrong).

- [ ] **Step 3: Implement**

```python
def _runs_by_event(records: list[dict]) -> dict[str, dict[str, dict]]:
    """event_id -> run_id -> {status, started_at, superseded}. A run is superseded by a later
    pending row that names it (boot recovery's top-level recovered_from_run_id, or a compact
    retry's detail.retry_of_run)."""
    runs: dict[str, dict[str, dict]] = {}
    for r in records:
        if r.get("record_type") != "event_status":
            continue
        eid, rid = str(r.get("event_id")), r.get("run_id")
        if rid:
            entry = runs.setdefault(eid, {}).setdefault(rid, {"status": None, "started_at": None, "superseded": False})
            entry["status"] = r.get("status")
            if r.get("status") == "running":
                entry["started_at"] = r.get("started_at")
        if r.get("status") == "pending":
            detail = r.get("detail") or {}
            for old in (r.get("recovered_from_run_id"), detail.get("recovered_from_run_id"), detail.get("retry_of_run")):
                if old and old in runs.get(eid, {}):
                    runs[eid][old]["superseded"] = True
    return runs
```

In `eligible_positions`, replace the `latest`-based `wake_failed` check with: `run = _runs_by_event(recs).get(p["event_id"], {}).get(p["run_id"])` (compute `_runs_by_event` once per door, cached like `completed`); `if not ok and not c and run is not None and run["status"] == "failed": reason wake_failed`. In `try_close` step 2, replace the loop over `latest[d].values()` with a loop over `_runs_by_event(recs)[eid][rid]` entries where `status == "running" and not superseded and started_at and parse_instant(started_at) < closes_at`.

- [ ] **Step 4: Run**

Run: `uv run pytest tests/assembly tests/assembly_validation -q -p no:cacheprovider`
Expected: all passed, including the untouched existing close tests.

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/assembly/close.py tests/assembly/test_close.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "assembly: the close pass classifies a position by its own run; recovered and retried runs are superseded (window spec §6; held for the assembly's review)"
```

---

### Task 9: The heartbeat: policy at launch, the launch note, the launch record

**Files:**
- Modify: `src/hamutay/heartbeat.py` (`main()` after `resolve_context_limit`; `HeartbeatLoop` untouched except reading nothing new)
- Test: `tests/test_heartbeat.py` (extend)

**Interfaces:**
- Produces: at launch for an OpenAI-provider door, `policy = ContextPolicy.for_launch(context_limit, context_limit_source, base_url, http=_default_http, model=args.model, cached=<probe from the log's latest launch record, if any>)`; the backend is constructed with `context_policy=ContextPolicyHolder(policy)`; the launch note gains, when `policy.limit`, `"; window: limit {limit} ({source}), count {server|estimate}, reserve reply {REPLY_RESERVE_TOKENS} floor {THINK_FLOOR_TOKENS}, think unrestricted above {THINK_UNRESTRICTED_ROOM_TOKENS} of room, reasoning budget {reasoning_budget}, compact retry once"`; `launch_config["context_policy"] = policy.as_dict()`; `latest_context_probe(log_path) -> dict | None` reads the last launch record's `context_policy.probe`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_heartbeat.py`; use the file's existing `main`/argparse test pattern, e.g. the test around `resolve_context_limit` at line ~252, to build `args`)

```python
def test_launch_builds_the_policy_and_says_the_window_clause(tmp_path, monkeypatch):
    from hamutay import heartbeat as hb
    from hamutay.context_policy import ContextPolicy
    from hamutay.window import REPLY_RESERVE_TOKENS, THINK_FLOOR_TOKENS, THINK_UNRESTRICTED_ROOM_TOKENS
    built = {}
    def fake_for_launch(cls, limit, source, base_url, **kw):
        built.update(limit=limit, source=source, base_url=base_url, cached=kw.get("cached"))
        return ContextPolicy(limit, source, limit, "http://127.0.0.1:8081", "probed", {"build_info": "b"}, 20)
    monkeypatch.setattr(ContextPolicy, "for_launch", classmethod(fake_for_launch))
    notes = []
    monkeypatch.setattr(hb.HeartbeatLoop, "_emit", staticmethod(lambda d: notes.append(d)))
    args = _launch_args(tmp_path, provider="openai", base_url="http://127.0.0.1:8081/v1", context_limit=65536)
    session, backend, launch_config = hb.build_session_for_test(args)      # extract this factory from main() if absent
    assert built["limit"] == 65536 and backend.policy.window_aware and launch_config["context_policy"]["reasoning_budget"] == "probed"
    clause = [n["note"] for n in notes if "window:" in n.get("note", "")]
    assert clause and f"reserve reply {REPLY_RESERVE_TOKENS} floor {THINK_FLOOR_TOKENS}" in clause[0]
    assert f"think unrestricted above {THINK_UNRESTRICTED_ROOM_TOKENS} of room" in clause[0] and "compact retry once" in clause[0]


def test_launch_without_a_ceiling_has_no_window_clause(tmp_path, monkeypatch):
    from hamutay import heartbeat as hb
    notes = []
    monkeypatch.setattr(hb.HeartbeatLoop, "_emit", staticmethod(lambda d: notes.append(d)))
    args = _launch_args(tmp_path, provider="openrouter")
    session, backend, launch_config = hb.build_session_for_test(args)
    assert not any("window:" in n.get("note", "") for n in notes) and launch_config["context_policy"]["window_aware"] is False


def test_latest_context_probe_reads_the_last_launch_record(tmp_path):
    from hamutay.heartbeat import latest_context_probe
    log = tmp_path / "s.jsonl"
    log.write_text(json.dumps({"state": {}, "launch": {"context_policy": {"probe": {"build_info": "b1"}}}}) + "\n"
                   + json.dumps({"state": {}, "launch": {"context_policy": {"probe": {"build_info": "b2"}}}}) + "\n")
    assert latest_context_probe(str(log)) == {"build_info": "b2"}
```

(`_launch_args` builds the argparse namespace the way the file's existing launch tests do; if `main()` cannot be called without a network, extract the session/backend/launch-config construction into `build_session(args) -> (session, backend, launch_config)` and have `main()` call it — that refactor is part of this task and must leave `main()`'s behaviour unchanged.)

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_heartbeat.py -q -p no:cacheprovider -k "window_clause or latest_context_probe"`
Expected: FAIL.

- [ ] **Step 3: Implement**

In `main()`'s OpenAI branch, after `resolve_context_limit`:

```python
        from hamutay.context_policy import ContextPolicy, ContextPolicyHolder
        from hamutay.taste_open import _default_http
        policy = ContextPolicy.for_launch(context_limit, context_limit_source, base_url, http=_default_http,
                                          model=args.model, cached=latest_context_probe(args.log_path))
        holder = ContextPolicyHolder(policy)
        if policy.limit:
            HeartbeatLoop._emit({"heartbeat": "launch", "note": window_clause(policy)})
```

with `window_clause(policy)` formatting the clause from the `hamutay.window` constants; pass `context_policy=holder` to `OpenAITasteBackend(...)` (keep `context_limit=context_limit` too); add `"context_policy": policy.as_dict()` (or `ContextPolicy.none().as_dict()` on the Anthropic branch) to `launch_config`. `latest_context_probe(log_path)` scans like `latest_context_observation` for the last state-bearing record whose `launch.context_policy.probe` is a dict.

- [ ] **Step 4: Run**

Run: `uv run pytest tests/test_heartbeat.py tests/test_context_ceiling.py tests/gpu_lease_validation -q -p no:cacheprovider`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/heartbeat.py tests/test_heartbeat.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "heartbeat: build the context policy at launch, say the window clause, carry the policy in the launch record (spec §5)"
```

---

### Task 10: Live-server integration tests (skipped without the server)

**Files:**
- Create: `tests/integration/test_local_window.py`

**Interfaces:**
- Produces: four tests, each `pytest.mark.skipif` unless `GET http://127.0.0.1:8081/props` answers within 2 s; (a) exact count equals `usage.prompt_tokens` on three payload shapes with `max_tokens: 1`; (b) the probe classifies the live server the same way twice; (c) observational: tools active, `tool_choice: "auto"`, `reasoning_budget_tokens: 32`, seeded, temperature 0, records the raw reply into the test output (never fails on the model's choice; fails only on transport errors); (d) `forced_sequence_tokens` from `/tokenize` versus the completion-token difference on the probe prompt, recorded as observational if either reply has other text.

- [ ] **Step 1: Write the tests**

```python
# tests/integration/test_local_window.py
"""Evidence against the live llama-server (spec Testing, integration a–d).
Run by the custodian outside any door's wake; paste the output into the review record."""
import json

import httpx
import pytest

from hamutay.context_policy import PROBE_MAX_TOKENS, PROBE_PROMPT, PROBE_SEED, ContextPolicy, tokenizer_root
from hamutay.taste_open import _default_http
from hamutay.window import REPLY_RESERVE_TOKENS, TokenCounter, budget_message

BASE = "http://127.0.0.1:8081/v1"
ROOT = tokenizer_root(BASE)


def _alive():
    try:
        return httpx.get(f"{ROOT}/props", timeout=2.0).status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _alive(), reason="no llama-server at 127.0.0.1:8081")


def _model():
    return httpx.get(f"{ROOT}/props", timeout=5.0).json()["model_alias"]


def _chat(body):
    return httpx.post(f"{BASE}/chat/completions", json=body, timeout=300.0).json()


TOOLS = [{"type": "function", "function": {"name": "clock", "description": "the time", "parameters": {"type": "object", "properties": {}}}}]


@pytest.mark.parametrize("shape", ["plain", "tools", "tools_none"])
def test_a_exact_count_equals_the_servers_prompt_tokens(shape):
    body = {"model": _model(), "messages": [{"role": "system", "content": "You are terse."},
                                            {"role": "user", "content": "What time is it? Use a tool if you like."}]}
    if shape != "plain":
        body["tools"] = TOOLS
        body["tool_choice"] = "none" if shape == "tools_none" else "auto"
    counted = TokenCounter(ROOT, _default_http).count(body)
    reported = _chat(dict(body, max_tokens=1))["usage"]["prompt_tokens"]
    assert counted == reported, (shape, counted, reported)


def test_b_probe_is_stable_across_two_runs():
    p1 = ContextPolicy.for_launch(65536, "discovered", BASE, http=_default_http, model=_model())
    p2 = ContextPolicy.for_launch(65536, "discovered", BASE, http=_default_http, model=_model())
    print("probe:", json.dumps(p1.probe, indent=1))
    assert p1.reasoning_budget == p2.reasoning_budget and p1.probe["template_sha256"] == p2.probe["template_sha256"]
    assert p1.forced_sequence_tokens > 0


def test_c_observational_budget_with_tools_active():
    body = {"model": _model(), "messages": [{"role": "user", "content": "Call the clock tool now."}], "tools": TOOLS,
            "tool_choice": "auto", "max_tokens": 512, "seed": PROBE_SEED, "temperature": 0,
            "reasoning_budget_tokens": 32, "reasoning_budget_message": budget_message()}
    data = _chat(body)
    print("observational (c) raw reply:", json.dumps(data["choices"][0], indent=1)[:2000])
    assert "choices" in data


def test_d_forced_sequence_tokens_versus_completion_difference():
    m = _model()
    base = {"model": m, "messages": [{"role": "user", "content": PROBE_PROMPT}], "max_tokens": PROBE_MAX_TOKENS,
            "seed": PROBE_SEED, "temperature": 0}
    control = _chat(base)
    zero = _chat(dict(base, reasoning_budget_tokens=0, reasoning_budget_message=budget_message()))
    forced = ContextPolicy.for_launch(65536, "discovered", BASE, http=_default_http, model=m).forced_sequence_tokens
    print("forced:", forced, "control:", control["usage"]["completion_tokens"], "zero:", zero["usage"]["completion_tokens"])
    assert forced > 0
```

- [ ] **Step 2: Run them against the live server** (custodian; check the process table first: `pgrep -af '[h]amutay.heartbeat'` and that no door is mid-wake per `journalctl --user -u 'hamutay-heartbeat@*' -n 5`)

Run: `uv run pytest tests/integration/test_local_window.py -q -p no:cacheprovider -s 2>&1 | tee /tmp/claude-1000/window-live-evidence.txt`
Expected: (a) passes for all three shapes (if it does not, the count is not exact and Task 4's counter must change before the merge: check `add_special`/`parse_special` and whether `/apply-template` needs `chat_template_kwargs`); (b) passes; (c) and (d) print evidence.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_local_window.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "window: live-server evidence tests (exact count, probe stability, two observational cases)"
```

---

### Task 11: Whole-branch review, Codex validation, live evidence, merge, restart, the message

This task is run by the custodian, not a subagent.

**Files:**
- Create (by Codex, frozen): `tests/window_validation/__init__.py`, `tests/window_validation/conftest.py`, `tests/window_validation/test_*.py`
- Create: `docs/superpowers/plans/2026-09-17-window-aware-wakes-review.md`
- Modify: `community/README.md` (the qwen door section: the window clause, the restart, the message)

- [ ] **Step 1: Whole-branch review.** Dispatch one reviewer subagent (most capable model) over every commit since the plan's base with the spec (r6), its seven reviews and this plan as the standard. Fix Important findings. Record findings and dispositions in the review file and **commit it on the branch before the merge**.

- [ ] **Step 2: Codex's independent validation suite, frozen before its first run.** `codex exec -s workspace-write -C <worktree> --ephemeral` with a prompt naming the spec (r6 at `b7ab196`) and this plan; house rule (tests from the invariants in the spec's Testing section 1–17; do not read `src/hamutay/window.py`, `context_policy.py` bodies or the new backend methods; write only under `tests/window_validation/`; do not run pytest); commit as they land: `validation: Codex's independent black-box tests for window-aware wakes (frozen before first run)`. Run `uv run pytest tests/window_validation -q -p no:cacheprovider`. Every failure is a code defect (fix in code, test first in the task's test file, commit) or a test defect (Codex corrects its own file in its own commit). Record each in the review file.

- [ ] **Step 3: Live evidence.** Run Task 10 Step 2 and paste the output into the review file under "Live evidence". If (a) fails, stop: the count is not exact; fix and re-run before anything below.

- [ ] **Step 4: Full suite, merge, push.** `uv run pytest tests -q -p no:cacheprovider --ignore=tests/integration` green in the worktree. Merge to main `--no-ff`, signed, naming the spec revision, the review and the validation count; push. Record the merge commit as `WINDOW_MERGE`.

- [ ] **Step 5: Restart the qwen door when idle.** `pgrep -af '[h]amutay.heartbeat'`; `uv run python -m hamutay.events report --log-path community/qwen/session.jsonl | head -6` (no pending, no running); `systemctl --user restart hamutay-heartbeat@qwen`; `journalctl --user -u hamutay-heartbeat@qwen -n 20 --no-pager` must show the `window:` clause with `count server` and the probe result, and `assembly: member qwen bound`.

- [ ] **Step 6: The message.** Write `deploy/qwen/window-repair-notice.txt` (commit it) stating, as facts: the two failed wakes of 2026-09-17 (09:00Z self-check, 09:10Z question delivery) with the numbers from the spec's table; that both ran to the end of the 65,536-token window; that the texts they generated were not kept and later ones will be, under `truncated_reply`; the fix by `WINDOW_MERGE` in one paragraph (exact count, bound, budget on grammar-free turns, lean activity log, one compact retry); that the first assembly question `9c725552` is open until 2026-09-24 02:05Z, that the deferral recorded at ledger seq 11 came from a wake that later failed and will be capped at the tally as `position_from_failed_wake`, and that a position recorded by a completed wake replaces it through `take_position`, which the door has. It asks for nothing. Send it: `uv run python -m hamutay.events send --log-path community/qwen/session.jsonl --sender custodian --purpose "$(cat deploy/qwen/window-repair-notice.txt)"` (check `send --help` for the exact flags; it must land as an `inbound_message` with `origin: external`). Watch the wake: `journalctl --user -u hamutay-heartbeat@qwen -f`. Record the outcome (completed, or failed and retried compact, or failed twice) in `community/README.md` under the qwen door section and in memory.

- [ ] **Step 7: Memory.** `remember` the state: merge sha, restart time, the launch clause as printed, the message's event id, what the wake did, and whether seq 11 was replaced.

---

## Self-review

**Spec coverage.** The property → Task 3 `bound_payload` assertion, Task 4 `_send`. The context policy and probe → Task 2; holder plumbing and `apply_context_limit` → Task 5; heartbeat launch → Task 9. §1 (count, fail closed, floor on `max_tokens`, budget gate, turn-0 soft check, near-wall rule, typed failures) → Tasks 3, 4. §2 (projection, closure, admission at the prepared wake, `admission` field) → Tasks 3, 6. §3 (lean rendering, window-aware gate) → Task 5. §4 (four paths, `_take_response`, failure record, `error_type`) → Tasks 4, 5. §5 (launch note and record) → Task 9. §6 (locked two-row append, compact run, attempt-aware close, acceptance) → Tasks 7, 8, 6 (compact rendering). "What stays byte-identical" → Task 1 goldens. Testing 1–17 → Tasks 2–9 (unit) and 10 (integration); Codex suite → Task 11. Migration → Task 11.

**Placeholders.** Task 4 Step 3 names the four `_first_payload_*` factorings and tells the implementer to build each path's first payload through them; the payload dicts are the ones the paths build today (shown in the code read for this plan), so this is a refactor instruction with the required property (first send == `prepared.payload` before bounding) stated and tested. Task 8's second test tells the implementer how to write the replacement-position case against the file's own fixture. Task 9 names the `build_session` extraction if `main()` cannot be exercised. No "TBD".

**Type consistency.** `ContextPolicy(limit, source, result_cap_chars, tokenizer, reasoning_budget, probe, forced_sequence_tokens, invocation_id=None)` in Tasks 2, 3 (`_policy` helper), 4, 5, 6, 7, 9. `bound_payload(payload, policy, counter, *, configured_max_tokens, tool_choice_none, candidate=False) -> Bound` in Tasks 3, 4. `Prepared(payload, prompt_tokens, path, sendable, reason, inputs)` in Tasks 4, 6. `prepare(model, system, messages, extra_tools, terminal_surface, tool_executor, *, candidate=False)` in Tasks 4, 6. `exchange(user_message, *, envelope=None, compact=False, ...)` in Task 6 and the runner. `append_failed_with_retry(*, event, run_id, exc, reason, context_results=None, admission=None) -> (failed, retry | None)` in Tasks 7, 8. `_runs_by_event` in Task 8 only. `_build_messages(..., lean_activity_log=False, omit_activity_log=False)` in Tasks 5, 6.
