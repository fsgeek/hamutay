"""Evidence against the live llama-server (spec Testing, integration a-d).
Run by the custodian outside any door's wake; paste the output into the review record.

Skips cleanly unless a server answers at BASE's /props within 2s. BASE defaults
to the real local server (http://127.0.0.1:8081/v1) but can be overridden with
HAMUTAY_LOCAL_WINDOW_URL, e.g. to a dead address for a clean-skip check without
touching the live server.
"""
import json
import os

import httpx
import pytest

from hamutay.context_policy import PROBE_MAX_TOKENS, PROBE_PROMPT, PROBE_SEED, ContextPolicy, tokenizer_root
from hamutay.taste_open import _default_http
from hamutay.window import REPLY_RESERVE_TOKENS, TokenCounter, budget_message

BASE = os.environ.get("HAMUTAY_LOCAL_WINDOW_URL", "http://127.0.0.1:8081/v1")
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
