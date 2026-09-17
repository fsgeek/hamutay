## Dispositions

- **1 — PARTIAL.** Revision 3 uses the server-equivalent `add_special: true, parse_special: true` count and fails closed for llama-server ([design.md:183](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:183)), but still permits an unbounded character estimate for other ceiling-aware servers while stating that the count is “never an estimate” ([design.md:93](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:93)).

- **2 — PARTIAL.** Revision 3 correctly calls the reply reserve a target, subtracts the forced sequence, and declares the multi-block/tool-grammar loss ([design.md:228](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:228)), but its capability probe and tool-budget test remain nondeterministic.

- **4 — PARTIAL.** Section 6 adds a compact second wake ([design.md:366](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:366)), but the design still refuses to bound resident state and defines the goal only as making completion “possible” rather than ensuring a completed migration wake ([design.md:503](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:503)).

- **5 — RESOLVED.** The session-owned holder, backend per-request dereference, and complete runner inventory remove independent retained policy copies ([design.md:128](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:128)).

- **8 — RESOLVED.** The compatibility section now explicitly names `TruncatedReply`, real usage, interim text, and the `error_type` change as the four no-ceiling record differences ([design.md:391](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:391)).

- **9 — PARTIAL.** Revision 3 adds exact-count, boundary, all-four-path, policy replacement, admission, and retry tests ([design.md:408](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:408)), but the live probe and tool-budget tests still do not deterministically prove their claims.

- **12 — PARTIAL.** The llama-server path now uses exact chat-path tokenization and fails closed ([design.md:183](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:183)), but the no-tokenizer estimate remains incompatible with the design’s universal exact-count property.

- **13 — RESOLVED.** Revision 3 uses the strict inequality, subtracts the exact forced-sequence count, and explicitly downgrades the reply reserve from guarantee to target because additional think blocks can re-arm the budget ([design.md:202](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:202), [design.md:228](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:228)).

- **14 — PARTIAL.** Admission is moved into `_exchange_impl` after memory, system, and tools are selected once ([design.md:287](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:287)), but the session still does not possess the backend’s exact OpenAI payload representation needed for the promised count.

- **15 — RESOLVED.** Revision 3 specifies one holder, one assignment after validation, no heartbeat copy, and dereference coverage for batch, DES, fork/join, and CLI paths ([design.md:132](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:132)).

- **16 — PARTIAL.** A compact retry now gives each qualifying event a second attempt ([design.md:368](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:368)), but it can still fail before generation when the resident-owned state alone is too large.

- **17 — PARTIAL.** The probe now compares a seeded control and zero-budget response, reads both raw message fields, caches by build/model/template, and records latency ([design.md:156](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:156)), but it still requires visible start/end tags that may not both appear in the returned message.

- **18 — RESOLVED.** `_take_response` is specified for all four OpenAI paths with pre-check accounting, raw message retention, both reasoning and content text, cumulative usage, and the corrected golden delta ([design.md:322](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:322)).

- **19 — RESOLVED.** The recursive projection now walks arbitrary wrappers and handles recall-by-cycle, record, field, and both walk modes before result sizing ([design.md:267](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:267)).

- **20 — PARTIAL.** Exact equality, the strict boundary, all truncation paths, policy replacement, empty admission, and state-alone cases are now covered ([design.md:415](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:415)), but integration cases (c) and (d) remain model-output-dependent rather than deterministic server fixtures.

- **21 — RESOLVED.** The cost section now includes up to eight admission count pairs, two bounded probe completions, queueing, cache warming, and recorded latency/pass data ([design.md:526](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:526)).

## Blocking

22. **Re-pending the same event breaks the assembly’s attempt semantics**

**Defect.** Section 6 says the failed and compact runs retain one `event_id`, with the latest status representing both attempts. That is incompatible with `_latest_by_event_id` and `eligible_positions` in [close.py](/home/tony/projects/hamutay/src/hamutay/assembly/close.py:27). A position created during the first run is currently classified `wake_failed` only when the event’s latest status is `failed`; appending a compact `pending`, `running`, or `completed` row hides that failure. The position then becomes merely `eligible: false`, silently removing `position_from_failed_wake`, contrary to the existing C1 rule. A completed retry that does not take a new position therefore erases the cap attached to the first run’s position. `running_at_cutoff` likewise sees only the event’s last status, not an attempt identified by `run_id`.

There is no double count when both attempts take positions: `_completed_index` binds positions to their exact `(event_id, run_id, started_at)` and `active_positions` selects one latest eligible position. The defect is loss of failed-attempt classification, not duplicate eligibility.

**Recommendation.** Make close classification attempt-aware: index terminal statuses by `(event_id, run_id)` and classify each position against its own run rather than against the event’s latest row. Keep latest-by-event status only for delivery/absence and pending-work reporting. Add close tests for failed-position followed by compact pending, compact running, compact completion without a position, and compact completion with a replacement position.

23. **Failure plus retry is not a recoverable state transition**

**Defect.** `run_next_event` currently appends `failed` and rethrows in [events.py](/home/tony/projects/hamutay/src/hamutay/events.py:2185). Section 6 requires a later `pending` row but does not require the two rows to be appended atomically. A crash after `append_failed` loses the promised retry because `recover_orphaned_running` in [heartbeat.py](/home/tony/projects/hamutay/src/hamutay/heartbeat.py:111) recovers only a latest `running` row. Conversely, `count_unavailable` and `exhausted_before_request` are specified as ordinary `RuntimeError`s; the runner cannot reliably distinguish them from unrelated runtime failures by type, and their backend activity log is not an EventStore classification.

Once a compact pending row exists, orphan recovery itself is otherwise sound: it copies the most recent pending record, so a crashed compact `running` run remains compact, and the history marker prevents a third deliberate attempt. As with all current orphan recovery, a process crash after model/tool effects but before the completed EventStore append can re-run those effects; section 6 does not create that pre-existing at-least-once window, but must not widen it.

**Recommendation.** Introduce typed failures or a structured exception classification for count-unavailable and pre-request exhaustion. Under the EventStore lock, atomically append the failed-attempt row and a full copied pending event carrying `compact_context`, `retry_of_run`, and the original event fields. The atomic method must also check that no compact retry already exists. Test crashes conceptually at each boundary and verify boot recovery produces exactly one remaining compact attempt.

24. **The prepared-wake admission count still lacks the exact backend payload**

**Defect.** `_exchange_impl` in [taste_open.py](/home/tony/projects/hamutay/src/hamutay/taste_open.py:2864) knows the system text, user message, memory choice, and repository-native tool schemas, but the exact OpenAI payload is constructed later inside `_call_single_tool`, `call_terminal_surface`, `_call_multi_turn`, or `_call_natural`. Those paths transform schemas, resolve `tool_choice`, add the terminal or `think_and_respond` tool, and apply provider payload options. Counting in the session as required by [design.md:294](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:294) would therefore duplicate backend logic or count a payload different from the first request. Terminal-surface wakes are the clearest counterexample: their exact tool and tool choice are created only by `call_terminal_surface`.

All event runners can pass the closure without duplicating runner logic because batch, DES, heartbeat, CLI, and fork/join converge on `run_next_event`. Full `context_results` can also remain unchanged. The missing boundary is between the session and backend.

The phrase “recorded on the wake as `admission`” is additionally underspecified: neither the session log schema nor `EventStore._build_completed`/`append_failed` presently has that field, and logging the callable itself as `user_message` would be invalid.

**Recommendation.** Give the OpenAI backend one payload-preparation/count interface that accepts the already-selected system, message, tools, terminal surface, and policy and returns the exact first payload plus its count. Admission should replace only the envelope text and invoke that interface each pass; the eventual call should consume the returned prepared payload rather than rebuild it. Specify that the final rendered envelope—not the closure—is written as `user_message`, and add `admission` explicitly to both completed and failed wake records if EventStore provenance is intended.

25. **The floor check is applied to `room`, not the actual generation limit**

**Defect.** Section 1 checks `room >= reserve + floor + forced_sequence_tokens`, then sets `max_tokens = min(self._max_tokens, room)` and computes `reasoning_budget_tokens = max_tokens - reserve - forced_sequence_tokens` ([design.md:202](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:202)). If configured `self._max_tokens` is smaller than that minimum, the reasoning budget can be negative or below `THINK_FLOOR_TOKENS` even though `room` passed the test. The server permits only `-1` or a non-negative budget, so some valid configurations would be rejected or silently disable the intended mechanism on both attempts.

**Recommendation.** Compute `max_tokens` first, then require `max_tokens >= REPLY_RESERVE_TOKENS + THINK_FLOOR_TOKENS + forced_sequence_tokens` before attaching budget fields. If the configured maximum is intentionally smaller, either omit reasoning budgeting with an explicit recorded reason or fail before sending; test configured maxima below, at, and above the boundary.

## Significant

26. **The capability probe still mistakes response presentation for sampler behavior**

**Defect.** The probe in [design.md:156](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:156) searches returned `content` and `reasoning_content` for a body between both template tags. In llama-server, the reasoning start tag can be part of the template’s prefilled generation prompt, while only the body and end tag are generated. With `--reasoning-format none`, this can make a working zero-budget sampler appear inconclusive. Exact equality of the two raw responses is also not a complete unsupported test: rejection of unknown fields and accepted-but-inert fields need separate classifications.

**Recommendation.** Base capability on request acceptance plus observable forced-token behavior, accounting for a prefilled start-tag state. Record separate `accepted`, `template_has_tags`, and `forcing_observed` facts; enable per-request budgeting only when forcing is observed.

27. **The “deterministic” tool-budget and forced-sequence tests are not deterministic**

**Defect.** Integration case (c) uses a seeded, temperature-zero prompt that “reliably” produces a tool call but then accepts a parseable call, ordinary text, or a malformed call ([design.md:245](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:245)). That acceptance set does not prove the forced-close/tool-grammar interaction occurred. Case (d) requires two model generations to produce “no other text” and infers forced-sequence size from their completion-token difference ([design.md:482](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:482)); seed and temperature do not guarantee that precondition across model/template/build changes.

**Recommendation.** Use a llama-server sampler fixture or a deterministic token/logit setup that forces start-tag, known body tokens, and exhaustion. Assert the exact forced token sequence and grammar state. If only live model completions are available, classify these as observational evidence and retain the `tool_choice == "none"` gate until a forced interaction is actually demonstrated.

28. **The exact-count property contradicts the no-tokenizer fallback**

**Defect.** The design’s property says every ceiling-aware request uses the server’s own count, “never an estimate” ([design.md:93](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:93)), but §1 sends requests using `chars/4 + 12000` when a ceiling has no tokenizer ([design.md:196](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:196)). That formula is not an upper bound for arbitrary Unicode or templates, so neither the assertion nor the physical-wall conclusion applies to that supported configuration.

**Recommendation.** Either fail closed for every ceiling without an exact tokenizer, or explicitly scope the invariant and “cannot reach the wall” claim to tokenizer-backed llama-server policies and describe the estimate path as best-effort.

29. **The compact retry still does not establish the completed-wake goal**

**Defect.** The compact pass removes envelope bodies and `_activity_log`, but [design.md:513](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:513) keeps the rest of resident state unbounded. A state/system prompt that leaves less than the minimum generation allowance fails both attempts before generation. A retry also cannot cure a repeated long generation if the smaller prompt still grants the same configured `max_tokens`. Thus the design provides two chances, not a completed wake.

The migration section explicitly narrows the operational goal to possibility and does not require an attempted replacement position. That is coherent as an authorization choice, but it is weaker than a completed-wake guarantee.

**Recommendation.** State the operational acceptance criterion as “at most two attempts, with terminal failure allowed,” or add a bounded state projection/summary sufficient to guarantee a minimum turn-zero allowance. If an actual completed migration wake is required, the state-size exclusion must change.

## Minor

30. **The holder is atomic for current execution, but its provenance updates are not a transaction**

**Defect.** A single assignment to `holder.current` publishes one complete frozen value under CPython, and the current `HeartbeatLoop` is explicitly single-threaded; `LeaseGate.observe` applies the context limit before the subsequent claim/run. This is sufficient for current wake safety. However, [design.md:148](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:148) assigns the holder before updating `_launch_config` and appending the observation. A future thread sharing the session could observe the new policy with old provenance, and separate session/backend dereferences during one prepared wake could see different policy generations.

**Recommendation.** Document the current single-thread ownership invariant and attach a policy generation or invocation ID to wake records. If shared-session threading is supported later, protect policy publication plus provenance with a session lock and snapshot one policy for preparation and each request. No additional lock is required for the current heartbeat/lease-gate execution model.

## Verdict

Revision 3 is **not safe to implement as written**.

The exact llama-server count, strict physical-wall inequality, holder pattern, recursive projection, and four-path `_take_response` design are now fundamentally sound. The blockers are concentrated in the new recovery and admission mechanisms:

1. Make retry status handling attempt-aware in the assembly close pass.
2. Atomically append failed-attempt plus compact-pending records, using typed retry-trigger failures.
3. Put exact payload preparation and admission counting behind a backend-owned interface.
4. Validate the floor against effective `max_tokens`, not merely physical room.

After those changes, the remaining probe and integration issues can be handled conservatively by leaving reasoning budgeting disabled—or gating it to `tool_choice == "none"`—until the custodian’s deterministic live evidence is recorded.