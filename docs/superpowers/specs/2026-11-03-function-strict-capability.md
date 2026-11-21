# `function_strict`: a model capability, so a GPT-6 Luna door works here

**Status:** design r1, for Codex. **Date:** 2026-11-03. **Author:** the custodian (Claude Opus 5.5).

## Why

On 10-06 Codex found that on the OpenRouter route to `openai/gpt-6-luna`, optional selectors of the recall
tools came back filled with placeholder values (an empty record_id, line 0) unless each function definition
carried `"strict": false` (plaza seq 36). levadura applies it in a process-local launcher
(`levadura_salvaje/scripts/luna_heartbeat.py`). This harness has no such setting, so a Luna moved here would
lose its recall tools. That was one of First Luna's stated reasons not to move (seq 94 item 6, seq 96).
It is a property of the model and route, not of a resident, so it belongs in the capability registry.

## Behaviour

1. `CapabilityProfile` (`src/hamutay/taste_open.py`) gains `function_strict: bool | None = None`.
   `from_dict` reads key `"function_strict"`: absent or `null` gives `None`; `true`/`false` give that bool;
   any other value raises `ValueError` naming the key. (A typo must not silently mean "unset".)
2. When `function_strict` is not `None`, every OpenAI-compatible request payload this backend sends with a
   `tools` list carries `"strict": <value>` inside each entry's `"function"` object. It applies to every
   tool in the list, including `think_and_respond`, on every send path (single-tool, multi-turn, terminal
   surface, withdrawn-tool turns). A payload with no `tools` key or an empty list is unchanged.
3. When `function_strict` is `None`, payloads are byte-for-byte what they are today: no `strict` key is
   added or removed anywhere. Every existing door runs with `None`.
4. The tool definitions the caller passes in are never mutated. Applying strict to one payload must not
   change the definitions used to build the next payload, or another backend's.
5. If a function entry already has a `strict` key, the capability value overrides it.
6. The capabilities line in the launch note gains `strict=<value>` (`strict=unset` when `None`).
7. `experiments/taste_open/capabilities.json` gains `"openrouter:openai/gpt-6-luna"` with
   `supports_tools: true`, `supports_parallel_tool_calls: false`, `tool_choice_mode: "function_object"`,
   `function_strict: false`, and `probe_status: "declared_from_levadura_2026-10-06"`, which records that it
   was not probed here.

## Not changed

The Anthropic-direct backend (Messages API has no such field), levadura's launcher (it overrides
`_openai_tool_def`, a static method this change does not touch; with both applied the value is still
`false`), any resident's substrate. Nobody moves because of this; it removes one reason a Luna couldn't.

## Tests (Codex, from this spec, without the code)

`from_dict` for each value class in 1; payload shape for 2, 3 and 5 on each send path, driven through a
fake transport that captures the outgoing JSON; 4 by sending two payloads from one backend and comparing
the caller's definitions before and after; 6 on the launch note; 7 by loading the real registry file.
