# Evidence-Honoring Action-Coherence Packet

This packet executes the next bounded-autonomous-work roadmap action:
evidence-honoring continuity plus strict action/artifact coherence scoring.

Run local fixture validation:

```bash
uv run python experiments/event_loop/evidence_honoring_action_coherence_20260605/run_evidence_honoring_action_coherence.py --fixture
```

Run live rows:

```bash
uv run python experiments/event_loop/evidence_honoring_action_coherence_20260605/run_evidence_honoring_action_coherence.py
```

Useful environment variables:

- `OPENROUTER_API_KEY` for DeepSeek V4 Pro and GPT-4.1-mini via OpenRouter.
- `MOONSHOT_API_KEY` for KIMI K2.6 via direct Moonshot Anthropic-compatible
  endpoint.

The direct KIMI path uses `https://api.moonshot.ai/anthropic` without `/v1`.

