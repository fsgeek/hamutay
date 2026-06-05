# OpenAI-Compatible Tool Parity

## Goal

Bring `OpenAITasteBackend` to functional parity with `AnthropicTasteBackend`
for multi-turn Hamut'ay tool use.

The current OpenAI-compatible backend is incomplete: when `extra_tools` are
provided, it warns that they are ignored and sends only `think_and_respond`.
That is a repo limitation, not a substantive protocol limitation. OpenAI-style
chat completions and OpenRouter can carry multiple function tools and return
tool calls that can be resolved in a loop.

## Required Behavior

- Convert Hamut'ay tool schemas into OpenAI `tools` entries of type
  `function`.
- Send `think_and_respond` plus all enabled extra tools.
- Execute every non-terminal tool call through `ToolExecutor`.
- Append tool results using `role: "tool"` and the matching `tool_call_id`.
- Continue until `think_and_respond` is returned or the bounded turn limit is
  reached.
- Preserve the existing `ExchangeResult` contract, including durable tool
  activity when a `ToolExecutor` is present.
- Support parallel tool calls. If parallel calls fail in a normal provider
  response, treat that as a bug to fix rather than a feature to avoid.

## Failure Semantics

- If the provider returns `finish_reason == "length"`, fail explicitly unless
  the response is handled by a deliberate recovery path. Do not parse a likely
  damaged structured return object as success.
- If OpenRouter `provider.require_parameters` causes routing/provider failure,
  surface that error directly and stop. Do not silently retry without the flag
  or pretend the model completed normally.
- Malformed function-call arguments should produce a clear backend error.
- Unknown tool names should be routed through the existing executor behavior
  and captured in tool activity, matching the Anthropic path where practical.

## V1 Scope

Implement functional parity first. Full context-budget recovery can wait unless
tests or normal research runs show it is needed. Hamut'ay already bounds
in-context tool-result copies while preserving full tool output durably, which
should be enough for the initial parity implementation.

## Suggested Tests

- OpenAI-compatible backend sends extra tools instead of discarding them.
- Serial tool call followed by `think_and_respond`.
- Parallel tool calls followed by `think_and_respond`.
- `finish_reason == "length"` raises instead of accepting damaged output.
- Malformed JSON function arguments raise a clear error.
- OpenRouter/provider error payloads propagate clearly.
- Tool activity is preserved on `ExchangeResult`.
- Existing single-tool `think_and_respond` behavior remains compatible.

