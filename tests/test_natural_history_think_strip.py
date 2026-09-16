"""Prior turns' <think> blocks must not be re-sent as history.

Found live 2026-09-16 on community/qwen c10: the natural loop appended
each assistant turn to the conversation with its full content, including
the <think> block, so every think re-entered the prompt on the next turn
(the server log shows a 6,483-token generation re-entering as 6,406 prompt
tokens). With reasoning preserved, a 65,536-token door ran out of context
mid-wake. Qwen's own guidance: history carries the final output only.
The record (interim_text, raw_output) keeps the full text; only what is
sent back changes.
"""
import json

from hamutay.taste_open import OpenAITasteBackend, _strip_think
from hamutay.tools import ToolExecutor
from hamutay.tools.schemas import TOOL_SCHEMAS, UPDATE_STATE_SCHEMA


def test_strip_think_string_and_blocks():
    assert _strip_think("<think>\nlong\n</think>\n\nvisible") == "visible"
    assert _strip_think("no think here") == "no think here"
    assert _strip_think("<think>only think</think>") == ""
    assert _strip_think(None) is None
    blocks = [{"type": "text", "text": "<think>x</think>a"}, {"type": "text", "text": "b"}]
    assert _strip_think(blocks) == [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]


def _turn(content=None, tool_calls=None, finish="stop"):
    return {"choices": [{"finish_reason": finish,
                         "message": {"role": "assistant", "content": content, "tool_calls": tool_calls}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 10}}


def test_history_sent_back_has_no_think_but_the_record_keeps_it(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    executor.execute = lambda name, args: {"content": "ok"}
    tc = [{"id": "c1", "type": "function", "function": {"name": "clock", "arguments": "{}"}}]
    script = [_turn(content="<think>private deliberation</think>calling clock", tool_calls=tc, finish="tool_calls"),
              _turn(content="<think>more</think>done")]
    backend = OpenAITasteBackend(api_key="k", wake_mode="natural")
    backend.payloads = []
    def fake_post(payload):
        backend.payloads.append(json.loads(json.dumps(payload)))
        return script.pop(0)
    backend._post_chat = fake_post
    result = backend.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}],
                          experiment_label="t", extra_tools=[TOOL_SCHEMAS["clock"], UPDATE_STATE_SCHEMA],
                          tool_executor=executor)
    second = backend.payloads[1]["messages"]
    assistant = [m for m in second if m["role"] == "assistant"]
    assert assistant and assistant[0]["content"] == "calling clock"
    assert "private deliberation" not in json.dumps(second)
    assert result.interim_text == ["<think>private deliberation</think>calling clock"]
    assert result.raw_output["response"] == "<think>more</think>done"  # the record keeps the think
