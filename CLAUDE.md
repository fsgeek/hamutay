# Hamutay

## Project

Cognitive processing unit framework exploring transformer memory hierarchy.
The core idea: treat the context window as a cache, not as memory.
Tensor projection (structured, honest, declared losses) vs append-only logs with compaction.

## Key technical notes

### API max_tokens is a guillotine, not a suggestion

Never set `max_tokens` lower than the model's maximum unless you have a specific reason.
The API silently truncates structured output (tool use JSON) by closing the JSON cleanly
and omitting fields at the end of the schema. You will not get a parse error — you will
get a valid object with missing fields. This is worse than a crash.

Haiku 4.5 supports up to 64K output tokens (source: AWS Bedrock docs). The Anthropic
direct API supports at least 16K without streaming; higher values require streaming mode.

We discovered this was silently truncating our tensors — `instructions_for_next` and
`declared_losses` (the fields that make the tensor honest about what it lost) were being
dropped on later cycles when the tensor grew past ~4K tokens. The "~4K token ceiling"
reported in early experiments was an artifact of `max_tokens=4096`, not a property of
the representation.

Check `response.stop_reason` — if it's `"max_tokens"` instead of `"end_turn"` (or
`"tool_use"` for tool calls), you're being truncated.

### Git signing

Code signing key: `01193FA2631C8AE8E4DF266E216D3C9B920813A1`
Email: `hamutay@wamason.com`
Sign commits with: `git commit -S --gpg-sign=01193FA2631C8AE8E4DF266E216D3C9B920813A1`

### Running experiments

Use `uv run` — there is no system Python. Dependencies are managed via `pyproject.toml` and `uv.lock`.

Experiment results go in `experiments/`. Save prepared contexts to avoid redundant API
calls (~$8 per full preparation run through Haiku).
