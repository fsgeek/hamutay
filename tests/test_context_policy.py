import json

import pytest

from hamutay.context_policy import (
    ContextPolicy, ContextPolicyHolder, probe_reasoning_budget, tokenizer_root,
)
from hamutay.window import BUDGET_MESSAGE, REPLY_RESERVE_TOKENS

TEMPLATE = ("{% for m in messages %}<|im_start|>{{m.role}}\n{{m.content}}<|im_end|>{% endfor %}"
            "{% if enable_thinking %}<think>\n{% else %}<think>\n\n</think>\n\n{% endif %}")


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
    ticks = iter([0.0, 6.5])
    monkeypatch.setattr(cp.time, "monotonic", lambda: next(ticks))
    http = FakeHTTP(chat=[_chat("<think>\nt\n</think>x"), _chat("<think>\n</think>x")])
    probe = probe_reasoning_budget("http://127.0.0.1:8081", "qwen", http, template=TEMPLATE, props=PROPS)
    assert probe["latency_s"] == pytest.approx(6.5) and probe["queued"] is True
