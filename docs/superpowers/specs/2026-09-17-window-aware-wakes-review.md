## Blocking

1. **The proposed reserve does not actually reserve reply space**

**Defect.** In `OpenAITasteBackend._call_natural`, payload construction currently sets `max_tokens` directly at [taste_open.py:1899](/home/tony/projects/hamutay/src/hamutay/taste_open.py:1899). The design changes that to `min(self._max_tokens, room)`, which still permits generation to consume every remaining context token. `reasoning_budget_tokens = room - REPLY_RESERVE_TOKENS` does not fix this: the forced budget message and closing tag also consume tokens, non-reasoning output is unbounded up to `max_tokens`, and llama.cpp re-arms the full reasoning budget for every new think block at [reasoning-budget.cpp:146](/home/tony/src/llama.cpp/common/reasoning-budget.cpp:146). Thus `finish_reason=length` can still occur at the physical wall, not only when “the reply alone exceeds the reserve.”

The turn-zero estimator is also not a safe bound. Reconstructing the two 2026-09-17 turn-zero payloads gives `chars/4` estimates of 41,917 and 24,292 tokens, versus the server-reported 50,603 and 28,794: underestimates of 8,686 and 4,502 tokens. The estimator counts serialized HTTP JSON, while llama-server counts the tokenizer output of its rendered chat template. It can also overestimate because JSON quoting, field names, and escaping are not rendered verbatim into the model prompt. Therefore it is neither an upper nor lower bound, and its error is larger than the 2,048-token reserve.

**Recommendation.** Obtain the rendered prompt’s real token count from llama.cpp, or adopt a measured conservative upper bound with an explicit safety margin larger than demonstrated error. Bound total generation below physical room, subtract the forced-message/end-tag overhead from the reasoning budget, and specify how multiple think blocks are handled. The invariant should assert that `prompt_tokens + maximum possible completion_tokens < context_limit`, not merely inspect payload fields.

2. **`reasoning_budget_tokens` can make a turn malformed or still hit the wall**

**Defect.** llama.cpp applies the reasoning-budget sampler before the tool grammar at [sampling.cpp:631](/home/tony/src/llama.cpp/common/sampling.cpp:631). For `tool_choice="auto"`, the tool grammar is lazy and is disabled while reasoning is active at [sampling.cpp:452](/home/tony/src/llama.cpp/common/sampling.cpp:452). If the model starts tool-call syntax without first emitting a recognized think-end tag, budget exhaustion can force the harness message and think-end sequence into the middle of that syntax. The result may parse as malformed content or a malformed tool call. With multiple think blocks, the budget resets each time, so total reasoning is not bounded.

There is an additional capability error: the design enables the fields based on `context_limit_source == "discovered"`. Source is not capability. An explicitly configured qwen llama-server supports the fields but would not receive them; an inherited ceiling can later be validated against a new llama-server invocation but would initially be excluded.

**Recommendation.** Introduce an explicit `supports_reasoning_budget` capability tied to the server implementation/version, integration-test it with qwen’s actual template under `tool_choice="auto"` and `"none"`, and define malformed-call behavior. Either prevent budget re-arming or account for every possible think block. Do not present this mechanism as preserving a guaranteed reply reserve until those server-level tests pass.

3. **`TruncatedReply` lacks the data required for the proposed failure record**

**Defect.** The length failure occurs before usage is accumulated and before content is added to `interim_text`, at [taste_open.py:1953](/home/tony/projects/hamutay/src/hamutay/taste_open.py:1953). The proposed exception carries only the truncated turn’s `prompt_tokens`, `completion_tokens`, `text`, and `turn_index`. The session failure handler at [taste_open.py:2979](/home/tony/projects/hamutay/src/hamutay/taste_open.py:2979) cannot reconstruct prior turns’ token totals, cache totals, cost metadata, responses, or earlier `interim_text` from those fields. Consequently, “usage with the wake’s measured totals” and “interim_text carries what earlier turns said” are not implementable as specified.

Today the failure path does preserve the system prompt, user message, prior state, and `tool_activity_full`; it loses generated assistant text and reports zero usage. The proposed placement need not duplicate text if the truncated turn appears only under `truncated_reply`, but the design must explicitly keep it out of `interim_text`. Storing only flattened `text` may also lose structured content parts returned by the server.

**Recommendation.** Make the exception carry cumulative wake accounting, cache/cost accounting, prior `interim_text`, and the raw response/message or content value. Update totals before raising, or construct a complete failure snapshot in `_call_natural`. Add a multi-turn truncation test proving earlier usage and interim text are retained exactly once.

4. **The stated completed-wake goal is not guaranteed by the declared scope**

**Defect.** The context-result cap does not cap the motivating self-check result. `_result_cap_for_context_limit` returns 65,536 characters for a 65,536-token window at [taste_open.py:607](/home/tony/projects/hamutay/src/hamutay/taste_open.py:607); the recorded recall result is 60,830 serialized characters, so it passes whole even though it duplicates nearly the complete state. Lean rendering reduces only the state copy in `_build_messages`; `tool_recall` still returns the full prior state at [memory.py:259](/home/tony/projects/hamutay/src/hamutay/tools/memory.py:259). With further state growth, turn zero will simply fail the proposed pre-request check. That saves GPU time but does not produce a completed qwen wake.

The migration also sends a new repair notice rather than re-pending the failed assembly event. A completed repair-notice wake does not itself replace the failed position or complete the original question wake.

**Recommendation.** Include aggregate prompt admission and requested-context projection in scope: cap or lean recalled state independently of the per-result quarter-window limit, and define a target maximum turn-zero prompt. If the goal includes repairing the assembly wake, explicitly schedule an event that asks the resident to reconsider/replace its position, subject to the project’s authorization rules.

## Significant

5. **The required context-source plumbing does not exist**

**Defect.** `OpenAITasteBackend.__init__` receives only `context_limit` at [taste_open.py:1214](/home/tony/projects/hamutay/src/hamutay/taste_open.py:1214); it never receives `context_limit_source`. The source exists only in heartbeat’s launch record at [heartbeat.py:1375](/home/tony/projects/hamutay/src/hamutay/heartbeat.py:1375). Moreover, `OpenTasteSession.apply_context_limit` updates only the backend’s `_context_limit` at [taste_open.py:3674](/home/tony/projects/hamutay/src/hamutay/taste_open.py:3674), so a post-lease rediscovery would not update any newly added source/capability field.

Likewise, `HeartbeatLoop` stores neither the ceiling nor the result cap in its constructor at [heartbeat.py:342](/home/tony/projects/hamutay/src/hamutay/heartbeat.py:342), and its call to `run_pending_events` at [heartbeat.py:619](/home/tony/projects/hamutay/src/hamutay/heartbeat.py:619) cannot pass the proposed cap. `OpenTasteSession` also has no authoritative context-limit property for the proposed `_build_messages(... lean_activity_log=...)` call at [taste_open.py:2907](/home/tony/projects/hamutay/src/hamutay/taste_open.py:2907).

**Recommendation.** Specify one session-owned context policy object containing limit, source, result cap, and server capabilities. Pass it to the backend and event runner, and update it atomically in `apply_context_limit`. Avoid having heartbeat, session, and backend infer policy independently from private attributes or `launch_config`.

6. **The context-result transformation changes the result’s type**

**Defect.** `resolve_requested_context` produces `result` as a dictionary at [events.py:1058](/home/tony/projects/hamutay/src/hamutay/events.py:1058), and existing callers/tests consume it structurally. The proposed call `json.dumps(result)` followed by `_bound_tool_result_for_context` returns a string even when no truncation is required. If stored directly “in its place,” `context_results[i]["result"]` changes from an object to a JSON-encoded string for every ceiling-aware wake. That is more than truncation and makes the model consume escaped JSON.

**Recommendation.** Preserve ordinary results as objects. For oversized results, use a typed object such as `{"truncated": true, ...}` rather than a JSON string, or define a new `result_projection` field. Add tests for both small and large results’ types.

7. **Full record preservation depends on an unstated deep-copy boundary**

**Defect.** The same `context_results` object is passed into `build_event_envelope` at [events.py:2229](/home/tony/projects/hamutay/src/hamutay/events.py:2229) and later into `append_completed_atomic` or `append_failed` at [events.py:2274](/home/tony/projects/hamutay/src/hamutay/events.py:2274). If envelope bounding mutates that list, the event-store record is also bounded, contrary to the design. This would break consumers such as `_context_error_count`, which expects dictionary results at [events.py:1490](/home/tony/projects/hamutay/src/hamutay/events.py:1490), and branch projections in `EventPolicy.branch_visible_context_results` at [event_policies.py:379](/home/tony/projects/hamutay/src/hamutay/event_policies.py:379).

If a separate deep-copied envelope projection is used, consumers reading event records remain safe because the full structured result is retained.

**Recommendation.** Require `build_event_envelope` to construct a deep-copied projection and never mutate its argument. Test completed and failed records, identity/alias separation, structured error detection, and branch projection after a capped envelope.

8. **The no-ceiling byte-for-byte guarantee contradicts change 4**

**Defect.** Changes 1–3 and 5 can be conditionally inert: `_build_messages` can default to false, event caps can default to `None`, and payload fields can be omitted. Change 4, however, says the loop raises `TruncatedReply` “where it raises today” and the session records new failure data. Applied generally, that changes `error_type`, `failure_classification`, `usage`, and `interim_text` for a no-ceiling wake. That violates the stated guarantee that every no-ceiling record remains byte-for-byte unchanged. Invariant 6 is not qualified by a known ceiling.

**Recommendation.** Decide explicitly whether capture is global or ceiling-gated. If byte identity is mandatory, raise `TruncatedReply` and alter the failure record only when a ceiling is known, and add a no-ceiling length-failure golden record. If capture should be universal, narrow the guarantee to successful payloads/prompts and acknowledge the record migration.

9. **The invariant suite tests field presence, not the safety claim**

**Defect.** Invariant 2 proves only that three request fields contain formulas; it does not prove that a reply reserve survives actual llama tokenization or generation. There is no test for estimator error, forced-message overhead, multiple think blocks, malformed tool-call interaction, explicit local-server capability, live `apply_context_limit`, or cumulative truncated-turn accounting. Invariant 7 is not independently testable “before and after” unless byte fixtures from commit `0aeb0674` are captured before implementation. Invariant 5’s phrase “no `parameters` key inside `_activity_log`” is ambiguous when asserted against an undelimited prompt string.

**Recommendation.** Freeze exact baseline fixtures from `0aeb0674`, including a no-ceiling length failure. Add llama-server integration tests using the qwen template; multi-turn usage/interim tests; live context-policy update tests; deep-copy/type tests for context results; and a property asserting actual prompt plus worst-case completion stays below the server ceiling. Parse the rendered state section structurally when testing lean activity rather than searching the whole prompt.

## Minor

10. **The lean-state implementation needs a defined copy operation**

**Defect.** `_build_messages` currently serializes `prior_state` directly at [taste_open.py:2358](/home/tony/projects/hamutay/src/hamutay/taste_open.py:2358). The design says the prompt copy alone is filtered but does not require a deep copy. A shallow or in-place edit could remove fields from `self._state`, the `prior_state` snapshot, or future memory-tool results.

**Recommendation.** Require a JSON-safe deep copy before filtering and add an assertion that the caller’s state is byte-identical after `_build_messages`.

11. **The launch note does not name all three constants**

**Defect.** Change 5 says the note adds “the three constants,” but its specified text mentions only the 2,048-token reply reserve and the 32,768-token unrestricted threshold. It omits the 512-token think floor, which controls whether a request is rejected. The current note is constructed at [heartbeat.py:1306](/home/tony/projects/hamutay/src/hamutay/heartbeat.py:1306), so this omission would become durable launch provenance.

**Recommendation.** Include the exhaustion floor explicitly and test all three values, preferably formatting the note from the constants rather than duplicating literals.

## Verdict

The design is not safe to implement as written. The reserve formula and turn-zero estimate do not establish the claimed safety property; llama.cpp’s reasoning budget can reset or interfere with a tool call; and the proposed exception cannot supply the promised failure record.

Before implementation, revise the design to use a real or conservatively bounded prompt-token count, define a true total-generation reserve including forced-token overhead, validate reasoning-budget behavior against the qwen template, add cumulative failure-state fields, introduce explicit context-policy plumbing, preserve structured context-result types through a deep-copy projection, and resolve the no-ceiling record contradiction. The immediate completed-wake goal also requires controlling duplicated recalled state and explicitly scheduling the wake that is meant to repair the failed assembly outcome.