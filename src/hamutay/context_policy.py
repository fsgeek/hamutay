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
# What `forced_sequence_tokens` falls back to when `/tokenize` cannot answer.
# The forced sequence is the budget message plus the think-end tag, whose
# real length is a door-and-template property; 96 is a deliberately generous
# over-estimate of it, so the floor check errs towards refusing a send rather
# than towards a request that will not fit. It is a fallback, never a default:
# a door that reaches it is a door whose tokenizer is not answering, which is
# why the use is printed.
FORCED_SEQUENCE_FALLBACK_TOKENS = 96
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


def probe_think_switch(root: str, model: str, http, *, template: str) -> str:
    """r6.4 §1a: "template" when the switch is present AND effective: the generation
    prompt rendered by /apply-template under `chat_template_kwargs: {enable_thinking: false}`
    ends with the closed block (THINK_END) and the plain render does not. One render each,
    no generation. Any failure classifies "none" (the gate is then absent and declared)."""
    if "enable_thinking" not in template:
        return "none"
    body = {"model": model, "messages": [{"role": "user", "content": PROBE_PROMPT}]}
    try:
        plain = http("POST", f"{root}/apply-template", dict(body))["prompt"]
        closed = http("POST", f"{root}/apply-template",
                      dict(body, chat_template_kwargs={"enable_thinking": False}))["prompt"]
    except Exception:
        return "none"
    effective = closed.rstrip().endswith(THINK_END) and not plain.rstrip().endswith(THINK_END)
    return "template" if effective else "none"


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
    # r6.4 §1a: "template" when the chat template carries `enable_thinking`, so the
    # harness can close the think block through `chat_template_kwargs`; "none" otherwise.
    think_switch: str = "none"

    @property
    def window_aware(self) -> bool:
        return self.limit is not None and self.tokenizer is not None

    def as_dict(self) -> dict:
        d = asdict(self)
        d["window_aware"] = self.window_aware
        if not self.window_aware:
            # r6.4 §1a: a door without a window keeps its launch-record bytes (§5).
            d.pop("think_switch", None)
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
        except Exception as e:
            forced = FORCED_SEQUENCE_FALLBACK_TOKENS
            print(f"  context policy: /tokenize did not answer ({e}); "
                  f"forced_sequence_tokens falls back to {forced}")
        switch = probe_think_switch(root, model, http, template=template)
        return cls(limit, source, _result_cap_chars(limit), root, _classify(probe), probe, forced, invocation_id,
                   think_switch=switch)


@dataclass
class ContextPolicyHolder:
    current: ContextPolicy = field(default_factory=ContextPolicy.none)
