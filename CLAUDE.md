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

### Experiment comparability

All experiments that use tensor projection MUST use the `Projector` class from
`projector.py` rather than making raw API calls. The Projector encapsulates:

- The full `PROJECTION_SCHEMA` with field descriptions that guide output structure.
  A stripped-down schema produces structurally different tensors.
- Collapse detection and checkpoint/recovery (retry from last good tensor).
- Precursor detection (`declared_losses` or `instructions_for_next` going empty).
- Escalation policy hooks.

The Q1 declared losses experiment (2026-03-16) used raw API calls with a simplified
schema and no recovery. This produced 4-6 collapses per condition vs 0 in the original
observation run. The results are valid for comparing conditions *against each other*
(both had the same confounds) but are NOT comparable to prior experiments.

When varying projection behavior for an experiment, subclass `Projector` or modify
the tensor fed to `_build_projection_prompt` — don't reimplement the projection call.

Similarly, `max_tokens` must match across experiments. The `Projector` currently uses
64000 (streaming). Any change should be made in `Projector` itself so all experiments
pick it up.

### Tensor data capture

Every tensor the Projector produces must be persisted. Use the `on_tensor` callback:

- `TensorLog(path)` — append-only JSONL, the fallback for local work
- `ApachetaBridge.from_duckdb(path)` — Yanantin persistence (when available)

Tools that don't capture data are a perversion. Never build a consumer of the Projector
that discards the tensors it produces.

### Batch size as confound

Batch size (tokens of new content per projection cycle) is the strongest predictor of
tensor rewrite behavior. Small batches → incremental integration (14% n-gram survival).
Large batches → structural reorganization (4% survival). Comparative experiments MUST
control for batch size distribution or the comparison is invalid.

### Chat interface

`uv run python -m hamutay` starts a tensor-projected conversation. Every session
produces research data (tensor JSONL in experiments/chat/). The chat interface is
both a demonstration and an instrument.
