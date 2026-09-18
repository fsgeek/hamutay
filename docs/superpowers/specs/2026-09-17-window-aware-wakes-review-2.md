## Round-one dispositions

1. **PARTIAL — Reserve and exact counting.** Revision 2 replaces the unsafe `chars/4` primary count with `/apply-template` plus `/tokenize` and bounds `max_tokens` ([design.md:145](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:145)), but `add_special: false`, the fixed-margin fallback, and the reasoning-budget formula still do not establish the claimed reserve.

2. **PARTIAL — Reasoning-budget safety and capability.** Revision 2 separates capability from ceiling source, acknowledges per-block re-arming and the lazy-tool-grammar interaction, and proposes a live test ([design.md:118](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:118), [design.md:180](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:180)), but its probe and reserve calculation remain unreliable.

3. **RESOLVED — Truncated-reply data.** `TruncatedReply` now carries raw message data, cumulative token/cache totals, responses for cost accounting, and prior interim text after incorporating the failed turn’s usage ([design.md:263](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:263)).

4. **PARTIAL — Completed repair wake.** Revision 2 adds typed envelope projection, iterative admission, and a migration wake that can call `take_position` ([design.md:213](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:213), [design.md:365](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:365)), but explicitly leaves state growth and truncated-turn retry out of scope, so completion is still not assured.

5. **PARTIAL — Context-policy plumbing.** The proposed frozen `ContextPolicy` consolidates the required fields and names session, backend, runner, and heartbeat propagation ([design.md:101](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:101)), but replacement cannot be atomic while those components retain separate references and several runner paths remain unspecified.

6. **RESOLVED — Context-result type preservation.** Small results remain their original objects and oversized results become typed truncation dictionaries rather than JSON strings ([design.md:223](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:223)).

7. **RESOLVED — Deep-copy boundary.** Revision 2 explicitly requires envelope projection by deep copy, forbids mutation of the argument, and preserves full completed and failed event records for existing consumers ([design.md:215](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:215)).

8. **PARTIAL — No-ceiling byte identity.** Revision 2 correctly declares universal truncation capture as a record migration and narrows byte identity to completed wakes and non-record surfaces ([design.md:284](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:284), [design.md:300](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:300)), but its golden-record delta omits the inevitable `error_type` change from `RuntimeError` to `TruncatedReply`.

9. **PARTIAL — Test coverage.** Revision 2 adds policy, admission, truncation, golden, and live-server tests ([design.md:310](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:310)), but the integration tolerance and scripted assertions do not prove the exact-count, physical-wall, probe, or reply-reserve claims.

10. **RESOLVED — Lean-state copying.** The design now requires a JSON deep copy before filtering and a caller-state byte-identity assertion ([design.md:249](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:249)).

11. **RESOLVED — Launch-note constants.** The launch clause now includes reply reserve, think floor, and unrestricted threshold and requires formatting directly from the constants ([design.md:290](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:290)).

## Blocking

12. **The proposed server count is not exact and the fallback cannot support the invariant**

**Defect.** `/apply-template` is the correct renderer: it calls the same `oaicompat_chat_params_parse` used by chat completion, so an exact body receives the same messages, tools, `tool_choice`, server template defaults, `chat_template_kwargs`, and `reasoning_effort` handling ([server-context.cpp:5043](/home/tony/src/llama.cpp/tools/server/server-context.cpp:5043), [server-common.cpp:1266](/home/tony/src/llama.cpp/tools/server/server-common.cpp:1266)). The tokenization step is not the same, however. Chat completion tokenizes the rendered prompt with `add_special=true` ([server-context.cpp:4283](/home/tony/src/llama.cpp/tools/server/server-context.cpp:4283)); revision 2 explicitly sends `add_special:false`, which `/tokenize` honors ([server-context.cpp:5068](/home/tony/src/llama.cpp/tools/server/server-context.cpp:5068)). These happen to agree only when the vocabulary adds no BOS or other special token. The proposed “within 8 tokens” integration assertion expressly permits the count to be wrong.

The fallback is more serious. `chars/4 + 12000` is an empirical cushion over two prompts, not an upper bound for arbitrary Unicode, escaping, tool schemas, or future templates. Yet revision 2 labels it the count and continues to assert a property requiring “the server’s own count, not an estimate.” A tokenizer outage therefore turns a stated invariant into an unmeasured assumption. The configured live endpoint did not answer the permitted `GET /props` during this review (`curl: connection refused`), so no live evidence narrows these source-level defects.

**Recommendation.** Tokenize the rendered prompt with `add_special:true` and `parse_special:true`, exactly matching the chat path. For a known llama-server ceiling, fail closed when either endpoint is unavailable unless a rigorously proven upper bound exists; log an estimate only as diagnostics. Require exact equality—not an eight-token tolerance—between preflight count and `usage.prompt_tokens` in the integration test.

13. **The physical-wall invariant and the advertised reply reserve are both false**

**Defect.** llama-server checks context exhaustion before its `n_predict` limit and stops when `slot.prompt.n_tokens() + 1 >= slot.n_ctx` ([server-context.cpp:1885](/home/tony/src/llama.cpp/tools/server/server-context.cpp:1885)). Therefore `prompt_tokens + max_tokens <= limit` is not sufficient at equality; a request can reach the physical stop on its final allowed token. The per-slot `n_ctx` already reflects the KV-per-slot and model-training caps, so there is no separate bulk KV reservation to subtract, but llama-server deliberately retains this one-token boundary.

The reasoning reserve also remains overstated. Revision 2 sets `reasoning_budget_tokens = max_tokens - 2048`, but the forced message and closing tag consume part of those remaining 2,048 generated tokens. If their actual length is `O`, only `2048 - O` tokens remain for the reply. Computing `overhead` and subtracting it from physical room does not repair that equation; it must also be subtracted from the reasoning budget. Moreover, llama.cpp explicitly re-arms the full budget after every new think start, so two think blocks can consume nearly two budgets. Bounding total output by `max_tokens` prevents unlimited generation but does not reserve a reply.

**Recommendation.** Assert `prompt_tokens + max_tokens < effective_slot_n_ctx`, using the exact chat-path token count. Calculate a one-block budget as at most `max_tokens - REPLY_RESERVE_TOKENS - exact_forced_sequence_tokens`; either prevent/reject subsequent think blocks, switch budgeted turns to `tool_choice="none"`, or stop claiming a guaranteed reply reserve. Test the equality boundary, exact forced sequence, and multiple think blocks against the server.

14. **Envelope admission is located where the exact turn-zero payload does not exist**

**Defect.** Revision 2 says the event runner counts “system + envelope + tools” after building the envelope ([design.md:238](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:238)). In the current code, `run_next_event` only has the envelope; it calls `session.exchange` afterward ([events.py:2229](/home/tony/projects/hamutay/src/hamutay/events.py:2229)). The system prompt, involuntary memory selection, curator context, constitution filtering, wake-mode guidance, and exact offered tools are not assembled until `OpenTasteSession._exchange_impl` calls `_build_messages` and constructs its executor ([taste_open.py:2907](/home/tony/projects/hamutay/src/hamutay/taste_open.py:2907)). The runner therefore cannot construct the payload the backend will send without duplicating stateful session logic; choosing involuntary memory twice could itself change the prompt.

The halving loop is also underdefined. It does not state that every pass starts from the immutable full results, what minimum stub is used, or how an empty result list and a system prompt already over target terminate. Because the serialized `head` is embedded and escaped again inside a wrapper, a “32,768-character cap” is not a 32,768-character envelope contribution.

**Recommendation.** Introduce a single prepared-wake boundary in the session: choose memory once, build system/messages/tools once, then let admission replace only the envelope projection before the backend receives that prepared payload. Reproject every pass from the immutable full results, define a fixed minimum metadata-only stub and a finite pass bound, and return an explicit “state/system alone exceeds admission target” result.

15. **`ContextPolicy` still has no atomic ownership model**

**Defect.** Revision 2 says the session owns a frozen policy while the backend and `HeartbeatLoop` also retain and consume it, then says `apply_context_limit` “replaces the whole policy atomically” ([design.md:130](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:130)). Assigning a new object to the session does not update either retained reference. This matters specifically on lease return: `LeaseGate` calls `session.apply_context_limit`, while `HeartbeatLoop.step` later invokes its stored runner configuration. Updating session, backend, heartbeat, launch config, and log in sequence is not atomic.

The call-site inventory is also incomplete. Besides heartbeat and `run_pending_events → run_next_event`, policy resolution affects `step_pending_events`, the two direct `run_next_event` calls in `ForkJoinPolicyRunner`, and the events CLI’s direct `run_next_event`/`run_pending_events` calls ([event_policies.py:502](/home/tony/projects/hamutay/src/hamutay/event_policies.py:502), [events.py:2389](/home/tony/projects/hamutay/src/hamutay/events.py:2389), [events.py:2669](/home/tony/projects/hamutay/src/hamutay/events.py:2669)). Numerous tests and experiments rely on the optional legacy signatures.

**Recommendation.** Keep one replaceable policy reference or holder owned by the session and have backend and runner dereference it at use time. `run_next_event` should default to `session.context_policy`; higher-level runners should not retain an independent copy. Make `apply_context_limit` construct and validate the replacement—including its probe—before one assignment, then update provenance. Add tests covering lease rediscovery followed by heartbeat, direct runner, batch runner, DES step, and fork/join execution.

16. **The declared exclusions still permit the repair wake to fail without another chance**

**Defect.** Revision 2 explicitly refuses to bound resident state and refuses to retry a truncated turn ([design.md:382](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:382)). Admission also proceeds when lean state alone exceeds its target, leaving §1 to fail before sending. If generation reaches the harness `max_tokens`, `TruncatedReply` records the loss but the event still fails. As the motivating store has no pending event, the one migration message can leave the door in exactly the same terminal condition: failed wake, no completed replacement, no next wake.

The migration message merely states facts and “asks for nothing” ([design.md:370](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:370)). That preserves resident choice and does make `take_position` available, but it does not satisfy any stronger requirement that a replacement position actually be attempted.

**Recommendation.** Bring at least one completion recovery mechanism into scope: enforce a minimum exact turn-zero generation allowance by compacting or projecting state, or automatically re-pend an exhausted/truncated migration event with a smaller prepared context. If the operational requirement is an attempted replacement rather than merely the capability to replace, say so explicitly in the event purpose while leaving the position itself to the resident.

## Significant

17. **A closed think block is not a reliable capability probe**

**Defect.** The probe conflates server support, template behavior, parser configuration, and a stochastic eight-token generation. The deployed server uses `--reasoning-format none` ([hamutay-llama-server.service:26](/home/tony/projects/hamutay/deploy/hamutay-llama-server.service:26)); with Qwen templates, the think-start sequence may already be part of the generation prompt, so the generated content may begin with only an end tag rather than a complete closed block. Conversely, a model can naturally close a block within eight tokens even if the budget fields were ignored. Other reasoning formats may remove the tags from `message.content` and place reasoning in `reasoning_content`. llama.cpp’s budget sampler is activated from template-derived start/end tags and prefilled generation-prompt tokens, not from the visible content shape alone ([sampling.cpp:311](/home/tony/src/llama.cpp/common/sampling.cpp:311)).

The asserted “under a second” cost is not reliable on a cold, queued, or newly returned server, and a launch-time completion consumes GPU and can warm or perturb prompt-cache/slot state.

**Recommendation.** Probe behavior, not presentation: use a deterministic prompt, inspect raw message fields and verbose generation metadata if available, and compare a zero-budget request with a control request. Classify separately whether the server accepts the fields, whether the active template exposes valid think tags, and whether forcing occurred. Cache the result per server build/template/model invocation and record actual duration.

18. **Universal `TruncatedReply` capture needs all four OpenAI paths and a corrected golden contract**

**Defect.** `finish_reason=length` is currently detected in `_call_single_tool`, `call_terminal_surface`, `_call_multi_turn`, and `_call_natural` ([taste_open.py:1392](/home/tony/projects/hamutay/src/hamutay/taste_open.py:1392), [taste_open.py:1534](/home/tony/projects/hamutay/src/hamutay/taste_open.py:1534), [taste_open.py:1638](/home/tony/projects/hamutay/src/hamutay/taste_open.py:1638), [taste_open.py:1953](/home/tony/projects/hamutay/src/hamutay/taste_open.py:1953)). Only the multi-turn paths naturally have cumulative totals; the single-tool malformed-retry loop also needs to retain usage and any earlier assistant content. A universal implementation therefore cannot be a natural-loop-only change.

The test promise that the no-ceiling record changes only in `failure_classification.truncated_reply`, `usage`, and `interim_text` is impossible as written: raising `TruncatedReply` changes the existing `failure_classification.error_type` from `"RuntimeError"` to `"TruncatedReply"`. For reasoning formats that separate reasoning, flattened `message.content` also does not necessarily contain the think text, though the raw `message` does.

**Recommendation.** Centralize response accounting and exception construction so every OpenAI path updates usage before checking the stop reason. Define flattened text across `content` and `reasoning_content`, while retaining the raw message. Amend the golden delta to include `failure_classification.error_type` and test natural multi-turn, structured multi-turn, malformed single-tool retry, and terminal-surface truncation.

19. **The lean projection does not match the actual memory result shapes**

**Defect.** `tool_recall` returns a wrapper whose state is under `result["content"]`, not a result that is itself a state dictionary ([memory.py:156](/home/tony/projects/hamutay/src/hamutay/tools/memory.py:156)). `tool_walk` currently returns path entries containing summaries and field names, not state dictionaries ([memory.py:495](/home/tony/projects/hamutay/src/hamutay/tools/memory.py:495)). The instruction to lean “any result that is a state dict (a recall …, a walk element)” therefore does not define an implementation matching today’s values. A literal implementation would leave the motivating recalled state’s `_activity_log.parameters` intact until the entire result is truncated.

Existing consumers are safe only if full event records remain untouched, as revision 2 requires: `_context_error_count` expects structured result dictionaries, and `branch_visible_context_results` recursively removes `_activity_log` from full records ([events.py:1490](/home/tony/projects/hamutay/src/hamutay/events.py:1490), [event_policies.py:379](/home/tony/projects/hamutay/src/hamutay/event_policies.py:379)).

**Recommendation.** Define one recursive JSON projection that removes only `parameters` inside every encountered `_activity_log`, irrespective of wrapper shape. Apply it to the deep-copied envelope projection before size bounding. Add fixtures for recall-by-cycle, recall-by-record-id, field recall, and both walk modes rather than a generic synthetic “state result.”

20. **The test plan is implementable only after specification changes and does not prove its central claims**

**Defect.** Most listed unit tests are implementable, but admission cannot be tested faithfully until the prepared-payload boundary in finding 14 exists. Integration test (a) permits an eight-token mismatch while the property requires the server’s exact count. Test (c) is nondeterministic—the model may simply answer with text—and its acceptance set includes nearly every normal outcome, so it does not establish that a forced close inside tool syntax is handled by the loop. The scripted fallback test proves arithmetic, not that the margin is safe.

Important omissions remain: `add_special:true` equivalence; the `n_ctx - 1` physical boundary; adversarial token/character ratios; exact forced-sequence length; multiple think blocks; reasoning separated from content; all four truncation paths; stale heartbeat policy after lease rediscovery; empty/no-result admission; wrapper serialization growth; and a state-alone-over-target repair path.

**Recommendation.** Make exact equality mandatory in the live count test, add a boundary request whose configured prediction limit stops before the physical wall, and replace the stochastic tool-budget test with a deterministic server-level sampler fixture or seeded grammar test. Add the omitted cases above. Treat live-server results as required review evidence before merge; none was obtainable during this review because port 8081 was unavailable.

## Minor

21. **The cost statement omits admission passes and understates probe risk**

**Defect.** The Cost section claims two extra HTTP calls per request plus one sub-second probe ([design.md:395](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:395)), but turn-zero admission can perform multiple `/apply-template` and `/tokenize` pairs while halving caps. The capability probe is itself a chat completion and may queue behind work or warm a cold model.

**Recommendation.** State the cost as two calls per normal request plus up to a specified finite number of admission pairs and one bounded launch completion; log count latency, admission pass count, probe latency, and whether the probe waited for a slot.

## Verdict

Revision 2 is not safe to implement as written.

It materially improves the original design: structured context projections, deep-copy preservation, cumulative truncation capture, explicit capability state, and the narrowed compatibility promise are sound directions. The remaining blockers are at the core of the safety claim, however:

- use the chat path’s exact tokenization (`add_special:true`) and fail closed when exact counting is unavailable;
- require a strict physical-wall inequality and correct the reply-budget equation for forced tokens and repeated think blocks;
- move admission to a prepared-wake boundary where the exact system, memory, envelope, and tools exist;
- establish one authoritative, dynamically dereferenced policy so lease rediscovery cannot leave backend or runner state stale;
- add a completion recovery path for the migration wake.

The probe, universal truncation paths, recursive memory projection, golden-record contract, and validation suite must then be corrected before merge. Until those changes and live-server evidence exist, revision 2 still cannot guarantee either its stated llama-server property or the completed qwen wake needed to repair the failed assembly position.