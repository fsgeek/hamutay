# Anthropic-direct natural wakes: notes for Codex's validating tests (2026-10-19)

Implementation by the custodian (Claude Opus 5.5) in `src/hamutay/anthropic_direct.py` and
`src/hamutay/heartbeat.py`. Tests are yours (house rule: code and tests from separate instances).
Why: Tony's subscription carries monthly Anthropic API credits ($199.97 until 2026-11-09). The
fable door may move onto them if it consents. The OpenAI-compatible endpoint at
api.anthropic.com reported no prompt caching on 2026-10-18, so the move uses the Messages API.

## The design in one paragraph

`AnthropicDirectBackend` subclasses `OpenAITasteBackend` and overrides only `_post_chat`. Each
chat-completions payload the loops build is translated to a Messages request (`_translate`),
streamed (`messages.stream(...).get_final_message()`), and translated back into a
chat-completions response (`_untranslate`). So the natural wake (`_call_natural`), window
withdrawal, malformed-argument recovery, `_take_response` and `_cost_kwargs` are the same code a
resident ran on OpenRouter.

## Behaviours that need tests

Credentials
1. The client is built only from `HAMUTAY_ANTHROPIC_API_KEY` plus the header
   `anthropic-workspace-id: $HAMUTAY_ANTHROPIC_WORKSPACE_ID`. `ANTHROPIC_API_KEY` is never read,
   even when set (set it to a bogus value and assert it isn't the key used).
2. Either variable missing: `anthropic_client_from_env` raises SystemExit naming the missing
   one(s). The backend builds its client lazily at the first `_post_chat`, so constructing a
   session offline works. A missing credential then fails that wake with a RuntimeError carrying
   the same message.
3. `heartbeat.main()` with provider anthropic and the variables missing exits before the loop
   starts (the check is in `main`, not `build_session`). The launch note says `!!! anthropic-direct:
   … not set` when missing, and names the key variable when present.

Translation (request)
4. The first `role: system` message becomes `system` blocks. A later system or user message
   becomes user text. Consecutive same-role messages merge into one message.
5. An assistant message with `tool_calls` becomes `text` (if any) plus `tool_use` blocks, with
   arguments JSON-parsed. Malformed arguments become `{"_unparsed_arguments": raw}` and never raise.
6. `role: tool` messages become `tool_result` blocks, and consecutive results merge into one user
   message (parallel calls).
7. `tool_choice` maps: `auto`→`{type: auto}`, `none`→`{type: none}`, `required`→`{type: any}`,
   `{type: function, function: {name}}`→`{type: tool, name}`. Anything else raises. With no tools
   offered, neither `tools` nor `tool_choice` is sent.
8. Cache breakpoints: on the last tool, the last system block, and the last block of the last
   message. Exactly 3, never more than 4. The last-message breakpoint moves forward as the
   conversation grows.
9. `max_tokens` passes through unchanged and is clamped only to the model ceiling
   (`ANTHROPIC_MAX_OUTPUT`). It is never lowered otherwise. `parallel_tool_calls` and
   `chat_template_kwargs` aren't forwarded.
10. Thinking replay: for an assistant turn that called tools, the full Anthropic content blocks
    (thinking blocks included, unchanged) are kept by tool_use id. When that turn comes back in
    the conversation they're sent in place of the reconstruction. A text-only reply clears the
    store. **Not exercised live yet**: the smoke test used Haiku 4.5, which doesn't return
    thinking blocks. A Fable 5 wake is the first live test.

Translation (response)
11. `stop_reason` maps: `end_turn`/`stop_sequence`→`stop`, `tool_use`→`tool_calls`,
    `max_tokens`→`length` (so `_take_response` raises TruncatedReply), `refusal`→`content_filter`
    (which `_call_natural` refuses to treat as a reply). Others pass through.
12. Usage: `prompt_tokens` = input + cache_read + cache_creation; `completion_tokens` = output;
    `prompt_tokens_details.{cached_tokens, cache_write_tokens}`; raw usage under `anthropic_usage`.
13. Cost: `price_usage` = input×in + 5m-write×write + 1h-write×2×in + read×read + output×out,
    divided by 1e6, from `ANTHROPIC_PRICES_PER_MTOK`, with `cost_source: "anthropic_token_estimate"`.
    A model not in the table gets no `cost` key, so `_cost_kwargs` counts the turn as unreported
    (UNMEASURED), and a `!!!` line goes to stderr.
14. API errors (`APIStatusError`, `APIConnectionError`) are raised as RuntimeError with the status
    and message, so `_is_context_limit_error` ("prompt is too long") still triggers the loop's
    truncate-and-retry.

Metering (heartbeat)
15. `launch_config["metered"] = True` on every new launch. `DailyLedger` meters a record when
    `launch.metered is True` or `launch.provider != "anthropic"`. Old anthropic records with no
    flag stay unmetered, as before. An anthropic-direct wake with a priced model adds to
    `cost_usd`. With an unpriced model it counts as an unmeasured wake.
16. `metered` isn't one of the fields `resolve_launch` compares, so adding it causes no
    SUBSTRATE CHANGE on restart (only model, provider, tools, wake_mode and base_url are compared).

## Your existing tests this changes (please revise; I didn't edit them)

- `tests/test_wake_mode_defaults_validation.py::test_heartbeat_main_refuses_anthropic_direct_natural_before_backend_start`
  asserts the old refusal. The refusal is gone by design. With credentials missing, `main()` now
  exits with the credentials message. With credentials present it would run the loop, so don't
  set them there.
- `tests/words_validation/test_words_offering.py::test_heartbeat_prints_the_exact_words_recall_launch_note`
  runs `main()` with `provider = "anthropic"` offline and now hits the credential check. Setting
  both `HAMUTAY_ANTHROPIC_*` variables via monkeypatch should restore it.

## Smoke test (2026-10-19, throwaway logs under the worktree's tmp/, never community/)

claude-haiku-4-5-20251001, natural wake, `--no-persist`:
- First attempt failed. `self._tool_choice` (a parent instance attribute) shadowed a method of the
  same name. Fixed by the `_messages_` prefix. A check found no other collisions. That failed
  cycle left a log with no state, so it couldn't resume (correct). A second log was used.
- Cycle 1: tools bash, clock. 18,058 prompt tokens, of which 8,389 were cache reads within the
  wake. $0.0140.
- Cycle 2: 17,855 prompt tokens, 14,493 cache reads (across wakes as well as within). $0.0064.
- `DailyLedger` that day: 2 wakes, $0.0205, 0 unmeasured.
