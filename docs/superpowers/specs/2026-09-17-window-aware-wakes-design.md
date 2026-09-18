# Window-aware wakes on a local door

Date: 2026-09-17. Author: the custodian session. Status: revision 6.4 (§1a, the
think gate after withdrawal, added the evening of 2026-09-17 from the qwen
door's cycle-13 evidence; revision 6.3 corrected five lines during implementation, see §1 and §2), after
Codex rounds five and six (`-review-5.md`: 1 Blocking, 2 Significant on
revision 5; `-review-6.md` found that the revision-6 commit had carried no
design text, so this is that text; rounds one to four had 4/5/2, 5/4/1,
4/4/1 and 2/3/0). Every finding of the three rounds is accepted in mechanism except
two, declared where they arise: the reply reserve is a target (§1), and
the resident's state is not cut (§6, "Acceptance"). Codex's sandbox could not reach the
local server, so the live evidence this design requires comes from the
custodian's runs, recorded in the review file before the merge. Amends
`2026-09-06-local-substrate-door-design.md` §5 ("The harness must know the
ceiling"). Operational under the standing rule recorded in
`community/README.md` ("Matters held for the assembly's review",
2026-09-17).

## Why

The qwen door (Qwen3.8-27B Q4_K_M on llama-server, `-c 65536`) woke at
09:00Z on 2026-09-17 for its self-check, recorded a deferral on the first
assembly question at 09:06Z, and failed at 09:10Z with
`finish_reason=length`. The heartbeat then ran the question's delivery
itself and failed the same way at 09:28Z. Both times the server reported
`n_tokens = 65535, truncated = 1`: the generation ran to the end of the
window. Nineteen minutes of GPU time, and the truncated text was not
recorded anywhere (`raw_output: {}`). The door now has no pending event
and will not wake by itself. Its deferral sits under a failed wake, which
the closing rule caps (`position_from_failed_wake`), so the question
extends at 2026-09-24 02:05Z unless a completed wake replaces it.

The replay over every recorded wake, joined from the server's own journal
(`prompt eval`/`total`/`n_tokens` per task) to the door's event store:

| wake (Z)     | event    | status    | turns | ctx at start | ctx at end | largest gen | total gen | min  | trunc |
|--------------|----------|-----------|------:|-------------:|-----------:|------------:|----------:|-----:|------:|
| 09-06 15:32  | 9fc7edfc | completed | 10 | 11,627 | 45,244 |  4,515 | 16,533 |  7.8 | 0 |
| 09-07 09:00  | 03ee6a36 | completed | 11 | 26,981 | 47,828 |  3,030 | 10,370 |  4.6 | 0 |
| 09-08 09:00  | 2b3cd10b | completed |  6 | 23,479 | 50,509 |  3,176 |  8,118 |  3.7 | 0 |
| 09-09 09:00  | 0df35e64 | completed |  7 | 20,631 | 48,623 |  2,777 |  7,767 |  3.6 | 0 |
| 09-10 09:00  | 538d364c | completed |  5 | 32,002 | 52,743 | 10,505 | 18,562 |  7.8 | 0 |
| 09-12 09:00  | 61a7751f | completed |  5 | 27,317 | 38,025 |  2,123 |  6,185 |  2.7 | 0 |
| 09-14 09:00  | c2cf6eac | completed |  7 | 27,470 | 42,689 |  6,483 | 10,962 |  4.7 | 0 |
| 09-16 09:00  | 62ff2bb3 | failed*   |  6 | 29,575 | 58,217 |  6,236 | 16,670 |  7.3 | 0 |
| 09-16 09:20  | de072909 | failed*   |  3 | 30,636 | 45,123 |  9,570 | 15,423 |  6.7 | 0 |
| 09-16 15:06  | 4b81aa27 | failed*   |  4 | 30,872 | 30,966 |      0 |      0 |  0.0 | 0 |
| 09-16 15:31  | 255dd058 | failed    |  2 | 19,420 | 65,535 | 17,636 | 32,392 | 15.2 | 1 |
| 09-16 15:52  | 07faff0c | completed |  8 | 17,884 | 43,459 | 23,222 | 73,943 | 34.2 | 0 |
| 09-17 09:00  | 25e8e958 | failed    |  4 | 50,603 | 65,535 |  7,674 | 17,869 |  8.5 | 1 |
| 09-17 09:10  | 3292ada1 | failed    |  4 | 28,794 | 65,535 | 16,235 | 37,289 | 19.6 | 1 |

`*` failed on the two 9-16 template/timeout defects, fixed that day. Per
turn, the three window failures were: 09-16 15:31 `(19,420 → +14,756)`,
`(47,899 → +17,636, wall)`; 09-17 09:00 `(50,603 → +1,159)`,
`(52,180 → +2,635)`, `(56,814 → +6,401)`, `(57,861 → +7,674, wall)`;
09-17 09:10 `(28,794 → +6,475)`, `(37,030 → +7,148)`, `(39,867 → +7,431)`,
`(49,300 → +16,235, wall)`.

Three facts the table establishes:

1. **Generation has a fat tail.** Of 82 turns since the door was founded,
   one in four generated more than 10,000 tokens in a single turn; the
   largest was 23,222. Thinking is not stripped from a turn's own
   generation, only from history (`_strip_think`, 9-16). The existing
   soft threshold (80% of the window, tools withdrawn) assumes a turn's
   output is small against the window. It is not.
2. **The starting context has drifted from 12K to 29K, then to 51K.** The
   system prompt is 17,940 tokens at cycle 12: the state (15,175 tokens,
   doubled at cycle 11) rendered as indented JSON, and inside it
   `_activity_log`, the harness's own record of the previous wake's tool
   calls, 32,136 chars of the state's 60,702 (about 8,000 tokens) because
   every entry carries its full `parameters`. The self-check's envelope
   was 74,173 chars because the resident's `requested_context` asked for
   `recall cycle 11`, which returns its whole previous state verbatim
   (60,830 chars serialised, under the quarter-window cap of 65,536
   chars and therefore untouched by it even if it applied), inside the
   prompt that already carries that state.
3. **The threshold is checked one turn late, on an estimate, and only
   withdraws tools.** On turn 0 the estimate is 0, so a wake that starts
   above the threshold is not told until it has spent a turn. The
   estimate itself (`chars/4` over bounded tool results) is neither an
   upper nor a lower bound: reconstructed over the two 9-17 turn-zero
   payloads it gives 41,917 and 24,292 against the server's 50,603 and
   28,794, under by 8,686 and 4,502 (Codex, round one). And the note
   cites `last_reported_prompt_tokens` rather than the number that fired
   (the door recorded the oddity: "39,280 against a 52,428 threshold").

What the replay cannot see, declared: whether a wake given a bounded think
would have ended in a reply or in another tool call; what the truncated
texts contained; and whether the resident would have curated its state
differently had its wakes been completing. Those are the resident's, and
only live wakes answer them.

## The property

A door is **window-aware** when its policy has both a limit and a
tokenizer (a llama-server that renders and counts the exact prompt). For
every request a window-aware door sends:

> `prompt_tokens + max_tokens < context_limit`, with `prompt_tokens` the
> server's own count of the prompt it will tokenize, never an estimate.

A ceiling with no tokenizer (an explicit `--context-limit` against a
server that is not llama-server; no door has one today) is **not**
window-aware: it keeps §5 of the 9-06 spec exactly as it runs today (the
80% soft threshold on the running estimate, the over-limit recovery) and
none of §§1, 2, 6 engage. The property is claimed only where it can be
measured (round three, finding 28).

Strict, because llama-server stops a slot when `n_tokens + 1 >= n_ctx`
(`tools/server/server-context.cpp`, the context-exhaustion check runs
before the `n_predict` check), so equality can still reach the physical
stop on the last allowed token. The backend asserts the inequality before
sending (a violated assertion is a harness defect and raises). With it,
`finish_reason=length` can arise only from the `max_tokens` the harness
chose, never from the physical wall, and a truncated turn is recorded
(§4). Everything else in this design is about making that `max_tokens`
large enough to finish a turn, giving a failed wake one more chance with a
smaller prompt (§6), and telling the resident the numbers.

## The context policy (one holder, session-owned, dereferenced at use)

Codex round one finding 5 and round two finding 15: the heartbeat, the
session and the backend each inferred the ceiling from private attributes,
and a frozen object handed to each of them cannot be replaced atomically.
So: one frozen value, one mutable holder, one owner.

```
ContextPolicy(                    # frozen dataclass, the value
    limit: int | None,            # tokens; None = no ceiling (OpenRouter)
    source: str,                  # "explicit" | "discovered" | "inherited" | "provider default"
    result_cap_chars: int | None, # _result_cap_for_context_limit(limit)
    tokenizer: str | None,        # base URL of a llama-server (GET /props answered with build_info)
    reasoning_budget: str,        # "probed" | "unsupported" | "inconclusive" | "not_probed"
    probe: dict | None,           # {build_info, model_alias, template_sha256, control_had_think,
                                  #  zero_budget_forced, latency_s, queued} or None
    forced_sequence_tokens: int,  # exact tokens of the budget message + end tag (tokenized at launch); 0 without tokenizer
)

class ContextPolicyHolder:        # the one mutable reference
    current: ContextPolicy
```

The session owns the holder (`OpenTasteSession.context_policy` returns
`holder.current`). The backend is constructed with the **holder**
(`OpenAITasteBackend(context_policy=holder)`; the old `context_limit=`
keyword remains and builds a holder with no tokenizer) and dereferences
`holder.current` at the top of every request. Every runner that can start
a wake, `run_next_event`, `run_pending_events`, `step_pending_events`, the
two `run_next_event` calls inside `ForkJoinPolicyRunner`, and the events
CLI's two calls, takes no policy of its own: they read
`session.context_policy` at the moment they build the envelope. Nothing
else holds a copy; `HeartbeatLoop` keeps none.

`ContextPolicy.for_launch(limit, source, base_url, *, http)` builds the
value: `tokenizer` is set when `GET <base>/props` answers with
`build_info`; `forced_sequence_tokens` is then the length of
`/tokenize` (`add_special: false`) over the budget message plus the
template's think-end tag; `reasoning_budget` comes from the probe below.
`apply_context_limit(limit, source, invocation_id)` builds and probes the
**replacement value first**, then makes one assignment to
`holder.current`, then updates `_launch_config` and appends the
`substrate_observation`; a probe failure leaves the old value in place and
is logged. The launch record carries the policy as a dict; the launch note
prints `limit`, `source`, whether the count is `server` or `estimate`, and
`reasoning_budget`.

**The probe (round two, finding 17): behaviour, not presentation.** Two
deterministic completions at launch, no tools, `seed: 7`, `temperature:
0`, `max_tokens: 48`, the same one-line user prompt; the first is the
control, the second adds `reasoning_budget_tokens: 0` and
`reasoning_budget_message: ""`. Three facts are recorded separately (round
three, finding 26): `accepted` (the zero-budget request returned 200
rather than a schema error), `template_has_tags` (`/props`'s
`chat_template` names a think start and end tag), and `forcing_observed`
(the control's reasoning body, taken from `reasoning_content` when
present or from `content` between the end tag and, if present, the start
tag, since the start tag may be prefilled by the template and never
generated, is non-empty, and the zero-budget reply's reasoning body is
empty). `probed` iff all three hold; `unsupported` when `accepted` is
false or `template_has_tags` is false; `inconclusive` when accepted with
tags but the control itself had no reasoning body (the fields are not
sent and the probe is retried at the next launch). The result is cached in the launch record keyed by
`(build_info, model_alias, sha256(chat_template))` and reused while the
key matches, so a restart against the same server costs nothing. Each
probe records its wall time and marks `queued` when it exceeded 5 s. Two
bounded completions cost under 100 tokens of generation.

## Changes

Everything below is gated on the door being window-aware
(`policy.limit is not None and policy.tokenizer is not None`), except
§4, which is universal (see "What stays byte-identical" for the exact
guarantee). A ceiling without a tokenizer therefore keeps its payloads
byte-identical to today (round four, finding 33).

### 1. The exact count and the reserve

In the OpenAI natural loop, before **every** request including the first,
with a tokenizer:

- `prompt_tokens = count(payload)`: POST `<tokenizer>/apply-template` with
  the exact request body the harness is about to send (messages, tools,
  `tool_choice`; the server runs the same `oaicompat_chat_params_parse` it
  runs for a completion, so template kwargs and reasoning settings match)
  and POST `<tokenizer>/tokenize` on the returned `prompt` with
  `add_special: true, parse_special: true`, which is how the completion
  path tokenizes it (`server-context.cpp`, the chat path's
  `tokenize(..., add_special=true)`). The integration test requires this
  count to **equal** the `usage.prompt_tokens` the server then reports.
- **Fail closed.** If either call fails, the request is not sent: the wake
  fails with `CountUnavailable` (below), logged as `budget_pressure /
  count_unavailable`, and qualifies for the one compact retry of §6. An
  estimate is never the count.
- `room = limit - 1 - prompt_tokens` (the strict inequality's one token).
- `max_tokens = min(self._max_tokens, room)`. If `max_tokens <
  REPLY_RESERVE_TOKENS + THINK_FLOOR_TOKENS + policy.forced_sequence_tokens`
  the request is not sent: the wake fails with `ExhaustedBeforeRequest`,
  logged as `budget_pressure / exhausted_before_request` with both `room`
  and `max_tokens`, and qualifies for §6. Zero GPU time. The floor is
  checked against the generation limit actually sent, not against room
  (round three, finding 25): a configured `--max-tokens` below the floor
  fails here on every attempt, which the launch note makes visible.
- The property is asserted on `max_tokens`.
- **Budget fields only on grammar-free turns** (round three, finding 27,
  conservative until live evidence): with `reasoning_budget == "probed"`,
  `tool_choice == "none"` (every tool withdrawn, the reply ends the wake),
  and `max_tokens < THINK_UNRESTRICTED_ROOM_TOKENS` (the generation limit
  actually sent, so a small configured `--max-tokens` with ample room is
  bounded too; r6.1, found in implementation), the request carries
  `reasoning_budget_tokens = max_tokens - REPLY_RESERVE_TOKENS -
  policy.forced_sequence_tokens` (never below `THINK_FLOOR_TOKENS`, by the
  floor check) and `reasoning_budget_message = "[harness: thinking budget
  reached; about {REPLY_RESERVE_TOKENS} tokens remain for this turn. Do
  not open another think block. Finish the turn.]"`. On a turn with tools
  active only `max_tokens` bounds the turn. So that budgeted turns arrive
  while room remains, the three-turn rule becomes: once perception is
  withdrawn **and** `room < THINK_UNRESTRICTED_ROOM_TOKENS`, all tools are
  withdrawn after **one** further tool turn (the constant
  `WITHDRAWN_TOOL_TURNS_NEAR_WALL = 1`; the existing three-turn rule holds
  above that room). The one-line gate is named in the tests; lifting it
  to `tool_choice == "auto"` is an amendment that requires the
  forced-interaction evidence of Testing (c) recorded in the review file.

The three failures above are typed: `class WindowFailure(RuntimeError)`,
with `CountUnavailable`, `ExhaustedBeforeRequest` and `TruncatedReply`
(§4) as subclasses, each carrying its numbers as attributes. The runner
recognises §6's triggers by type, never by message text (round three,
finding 23).
- Every budgeted request logs `budget_pressure / generation_budgeted` with
  `prompt_tokens`, `room`, `max_tokens`, `reasoning_budget_tokens`,
  `forced_sequence_tokens`, `limit`, and the count latency.
- The soft-threshold check (`prompt_tokens >= SOFT_THRESHOLD_FRACTION *
  limit`) runs on **every** turn of a window-aware door on the exact count
  of the candidate payload (turn 0 included), never on the character
  estimate; the estimate path remains only for doors that are not
  window-aware (r6.2, found by the Task 4 review: the implementation had
  the exact check at turn 0 only). The note says what fired:
  `"the next request counts {prompt_tokens} tokens ({count_source}); the
  last measured request was {last_reported_prompt_tokens}"`. After the
  withdrawal the three-turn rule (`all_tools_withdrawn`) is unchanged.

**The reply reserve is a target, not a guarantee (round two, finding 13,
declared).** The budget bounds **one** think block: llama-server re-arms
it for every think block a turn opens, and the harness cannot prevent a
second block. What the design guarantees is the property above (the turn
cannot reach the wall), that a single think is closed with the reserve
and the forced sequence subtracted, and that a turn which still runs out
is recorded in full (§4) and retried once with a smaller prompt (§6). The
message asks the model not to open another block; whether it complies is
observed, not assumed, and the record shows it.

**Budget with tools active (round one, finding 2; round three, 27).**
llama-server runs the budget sampler before the lazy tool grammar; if the
model opens tool-call syntax inside an unclosed think and the budget
forces the message and end tag, the turn can parse as malformed. The
design does not send budget fields on such turns (the gate above). The
observational live case (Testing, integration c) records what the server
does with a small budget and tools active; it is evidence for a future
amendment, not a test this design passes or fails on.

Constants (module level, formatted into the launch note from the
constants, never duplicated): `REPLY_RESERVE_TOKENS = 2048`,
`THINK_FLOOR_TOKENS = 512`, `THINK_UNRESTRICTED_ROOM_TOKENS = 32768`,
`WITHDRAWN_TOOL_TURNS_NEAR_WALL = 1`, `SOFT_THRESHOLD_FRACTION = 0.8`.

### 1a. The think gate after withdrawal (revision 6.4)

**The evidence (2026-09-17, `community/qwen` cycle 13, the repair-notice
wake and its §6 compact retry, on the merged revision 6.3).**

| attempt | turns | last turn | prompt | generated | prompt + generated |
|---|---|---|---|---|---|
| first (19:03Z) | 7 | index 6, first after withdrawal, five state tools active | 52,685 | 12,850 | 65,535 |
| compact (19:18Z) | 7 | index 6, first after withdrawal, five state tools active | 50,243 | 15,292 | 65,535 |

The §1 property held (the sum is `limit - 1` both times), §4 kept both
replies (47,153 and 52,428 characters, untrusted), §6 ran once. Both
overruns are a single think block on the **first turn after perception
withdrawal**, a tool turn: perception was withdrawn at counts of 55,833
and 53,391 (the soft threshold is 52,428), the note was appended, and the
door thought through the whole room before calling any of the five tools
it still had. §1's budget fields never apply to a tool turn, so a working
budget would not have bounded either turn; and this server's budget is
inert regardless (probe: accepted, template has the tags, the control
thinks, forcing not observed). The inertness was confirmed on a CPU-only
scratch instance of the same build (`b1-73a43d1`, port 8082, same GGUF): a
zero budget returns the completion the control returns, token for token.
Its cause, read in `common/sampling.cpp` and the template and not fixed
here: the Qwen template opens `<think>\n` inside the generation prompt, and
the budget sampler is armed idle, watching *generated* tokens for the
opening tag it will never see; upstream master (202 commits ahead) has no
handling for a think opened by the prompt.

**The rule.** On a window-aware door whose policy says `reasoning_budget !=
"probed"` and whose template carries the switch (`think_switch ==
"template"`: the template source contains `enable_thinking`), every request
built **after perception is withdrawn** carries `chat_template_kwargs:
{"enable_thinking": false}`. Tool turns included: the failure is on the
tool turn, and the switch acts in the template (the assistant turn opens
as `<think>\n\n</think>\n\n`, so the model's next token is its reply or its
tool call), not in the sampler, so it has none of the grammar interaction
that keeps §1's budget fields off tool turns (verified on the scratch
instance: under the switch a `take_position` tool call parses, 57 tokens,
`finish_reason: tool_calls`). The builder puts the kwargs in the payload
**before** the count, so §1's exact count renders the template the
completion renders (the closed block costs tokens; they are counted, and
the integration test's equality holds). On a probed server the §1 budget
path stands unchanged and the gate does not apply (declared gap 1). A door
that is not window-aware is byte-identical. A template without the switch
classifies `think_switch == "none"`: no gate, and the launch note says so.

**Why withdrawal is the line, not the room.** Withdrawal fires at
`SOFT_THRESHOLD_FRACTION` of the limit, so at that moment the room is under
a fifth of the window (13,107 on 65,536); the two overruns had 12,850 and
15,292. Before withdrawal the room is at least that, and the observed
reading-turn generations were 2,600 to 5,800 tokens a turn; a think there
can still overrun (declared gap 2) and is captured under §4 and retried
under §6 as today. Gating on room alone (`room <
THINK_UNRESTRICTED_ROOM_TOKENS`) would close the think on reading turns
with 30,000 tokens of room; gating on the phase closes it exactly where the
harness already changes the door's world and tells it so.

**What the door is told.** The withdrawal note (§1, the user-role note)
gains one sentence when the gate applies, after "remain.": `"The harness
also closes your think block for the rest of this wake (this server cannot
bound a think); reason in your reply if you need to."` The launch note's
clause (§5) gains `think gate {template after withdrawal|budget|none}`:
"template after withdrawal" when the gate applies, "budget" when probed,
"none" otherwise. Each gated request logs `budget_pressure / think_closed`
with `turn_index`, `prompt_tokens` and `max_tokens`, so the record shows
which turns ran without a think block. The policy dict gains
`think_switch`.

**Declared gaps.** (1) A probed server's withdrawn tool turn carries no
budget (§1, round one finding 2) and no gate; a server whose budget forces
does not exist in this house today, so the gap is resolved with evidence
when one does. (2) A think on a perception-open turn is unbounded, as
before. (3) The door's deliberation on its closing turns now happens in
the reply text, which the record keeps, instead of in a think block, which
the record kept only when truncated. That is a change to what the resident
does with its last turns; it is declared to the resident in the launch note
and the withdrawal note, and held for the assembly's review with the 9-17
items in `community/README.md`.

### 2. Context results: a typed projection, deep-copied, admitted at the prepared wake

`build_event_envelope(event, context_results, run_id, operational_notes,
*, policy: ContextPolicy | None = None, cap_chars: int | None = None)`
never mutates its arguments. With a policy that has a limit it builds a
projection of `context_results` by JSON deep copy in which:

- one recursive projection, `lean_activity_logs(obj)`, walks every dict
  and list at any depth and, inside any list found under the key
  `_activity_log`, keeps for each entry only `cycle`, `timestamp`, `tool`,
  `reason`, `result_summary`. It is applied to the whole projection before
  sizing, so a recall by cycle (state under `result["content"]`), a recall
  by record id, a field recall, and both walk modes are all covered
  without the harness knowing their wrapper shapes (round two, finding 19);
- any `result` whose serialisation then exceeds `cap_chars` (initially
  `CONTEXT_RESULT_CAP_CHARS = policy.result_cap_chars // 2`, an eighth of
  the window in chars) is replaced by a typed dict `{"truncated": true,
  "chars": <full>, "chars_kept": <n>, "head": <first n chars of the
  serialisation>, "why": "context result cap"}`; below `MIN_STUB_CHARS =
  256` the head is dropped and the stub is metadata only. Results under
  the cap stay the objects they were.

The event store's `context_results` (completed and failed records) keep
the full structured results; `_context_error_count`,
`EventPolicy.branch_visible_context_results` and every other reader of
records see what they see today.

**Admission at the prepared wake (round two, finding 14; round three,
24).** The runner does not know the system prompt, the involuntary
memory, the curator context, the constitution filtering or the offered
tools; the session assembles them once in `_exchange_impl`. And the
session does not know the exact OpenAI payload: the backend's four paths
transform the schemas, resolve `tool_choice`, add the terminal or
`think_and_respond` tool and apply provider options. So the count lives
in the backend, behind one interface:

```
backend.prepare(model, system, messages, extra_tools, terminal_surface,
                tool_executor, policy, *, candidate: bool = False)
    -> Prepared(payload: dict, prompt_tokens: int, path: str,
                sendable: bool, reason: str | None,
                inputs: PreparedInputs)   # model, system, messages, tools,
                                          # terminal_surface, tool_executor,
                                          # policy: everything the path needs
backend.call_prepared(prepared, **path_kwargs)
```

`prepare` builds the exact first payload the chosen path (single-tool,
terminal surface, multi-turn, natural) would send, with the path's own
tool transformation and `tool_choice`, and counts it (§1). With
`candidate=True` (admission) a count below the floor does not raise: it
comes back as `sendable=False` with the reason, so admission can shrink
the envelope and try again. A count that cannot be taken at all raises
`CountUnavailable` immediately in either mode; candidate mode suppresses
only `ExhaustedBeforeRequest`. The final candidate is prepared with
`candidate=False`, which applies the floor check and raises
`ExhaustedBeforeRequest`. `call_prepared` consumes `prepared.payload`
verbatim for the **first** send only, passing `prepared.prompt_tokens` into
the path as the pre-count so the first send is not counted twice (r6.2); **every** later send on any path,
a multi-turn path's next turn (after a tool result, a withdrawal, the
near-wall rule) and the single-tool path's resend after malformed
arguments alike, is rebuilt from `inputs` plus the path's loop state and
passed through the same `_count_and_bound(payload)` helper immediately
before `_post_chat`, so the invariant is asserted on the payload actually
sent, every time; the tests count one tokenizer call per send on each
path. Rule (round four,
finding 35): **after any change to the tool set, rebuild, recount, then
assert and send**; a request is never sent with a count taken before a
tool was withdrawn. That applies at turn 0 (the soft-threshold check
withdraws perception, the payload is rebuilt without those tools and
recounted before the first send) and inside the loop. The runner passes the session a `render_envelope: Callable[[int
| None], str]`, a closure over the **immutable full** `context_results`
that returns the envelope built at a given cap (the runner still records
the full results; the keyword is `render_envelope`, not `envelope`, because
existing `exchange()` doubles take `envelope` positionally; r6.3). At the prepared-wake boundary the session calls
`prepare` with `envelope(cap)` as the user message; if `prompt_tokens`
exceeds `ADMISSION_TARGET_FRACTION = 0.5` of the limit it halves the cap
and calls `prepare` again, at most `ADMISSION_MAX_PASSES = 8` times,
stopping when under the target, when every result is a metadata-only
stub, or at the pass bound (on a 65,536 window the bound arrives first:
eight halvings from 32,768 chars reach `MIN_STUB_CHARS`, not 0; r6.3), and
then calls `call_prepared` with the last `Prepared`, so the request sent
is the request counted. Each pass logs `budget_pressure /
envelope_admission` with the cap and the count. The final rendered
envelope string, not the closure, is what the wake record stores as
`user_message`. The outcome is recorded as a new `admission` field
`{passes, final_cap, prompt_tokens, over_target: bool,
envelope_exhausted: bool}` on the session's wake record and on the event
store's completed and failed records (both builders gain the optional
field; absent when admission did not run). When the state and system
prompt alone exceed the target the outcome says so and the wake proceeds
to §1, which decides at the request. The state is never cut by the
harness. `call_terminal_surface` and the single-tool path go through the
same `prepare`, so their exact tool and `tool_choice` are counted too.

### 3. The activity log is rendered lean into the prompt

`_build_messages(..., lean_activity_log: bool = False)`: when true, the
prior state, the involuntary memory and the curator context are each
rendered through the same `lean_activity_logs` projection §2 defines, on a
JSON deep copy (`json.loads(json.dumps(...))`); the caller's objects are
byte-identical after the call, and a test asserts it.
The state on disk and every record are unchanged. The session passes
`lean_activity_log = policy.window_aware` (limit and tokenizer both
present). A one-line note under the
state heading says: `"(_activity_log is shown without parameters; the
record has them)"`. The test parses the rendered state section back to
JSON and asserts on the structure, not on the whole prompt string.

### 4. Truncated output is captured (universal, all four paths)

`finish_reason=length` is detected today in four places of the OpenAI
backend: `_call_single_tool`, `call_terminal_surface`, `_call_multi_turn`
and `_call_natural` (round two, finding 18). One helper,
`_take_response(data, acct)`, replaces the four: it adds the response to
the wake's accounting (`input`, `output`, cache read, cache creation,
`responses` for `_cost_kwargs`) **before** checking the stop reason, and
on `length` raises `TruncatedReply(RuntimeError)` carrying a complete
snapshot: `text` (the flattened `content` **and** `reasoning_content`,
think included, in that order), `message` (the raw `choices[0].message`),
`turn_index`, the turn's `prompt_tokens` and `completion_tokens`, the
wake's cumulative counts and `responses`, and the earlier turns'
`interim_text` (or, on the single-tool path, any earlier assistant content
the malformed-retry loop had kept).

The session's `api_call` failure path, on a `TruncatedReply`, writes
`failure_classification["truncated_reply"] = {"text", "message",
"turn_index", "prompt_tokens", "completion_tokens", "trusted": false}`,
fills `usage` from the cumulative counts (today the record says
`input_tokens: 0, output_tokens: 0`) including cost fields, and sets
`interim_text` to the earlier turns' text only: the truncated text appears
once, under `truncated_reply`, never in `interim_text`.
`failure_classification.error_type` becomes `"TruncatedReply"` (it was
`"RuntimeError"`); the golden delta names it. A multi-turn test asserts
the earlier turns' usage and text are retained exactly once, on each of
the four paths.

This applies to every door. A no-ceiling wake that truncates today loses
its text and records zero usage; after this change its failure record
gains `truncated_reply` and real `usage` and its `error_type` changes.
That is a record migration, declared here, and the golden fixture for it
is captured before the change (see Testing).

### 5. The launch note and the launch record

With a limit, the launch note adds one clause formatted from the
constants: `"; window: limit {limit} ({source}), count {server|estimate},
reserve reply {REPLY_RESERVE_TOKENS} floor {THINK_FLOOR_TOKENS}, think
unrestricted above {THINK_UNRESTRICTED_ROOM_TOKENS} of room, reasoning
budget {probed|unsupported|inconclusive|not_probed}, think gate {template after
withdrawal|budget|none}, compact retry once"` (the think-gate term is §1a,
revision 6.4). The launch record carries `context_policy` as a dict. Without a limit,
note and record are unchanged.

### 6. One compact retry (completion recovery)

Round two, finding 16: a door whose wakes fail on the window, with no
pending event, is left exactly where it was. So the runner gives a wake
one more chance, once, and the records stay honest about both attempts.

**The transition is one locked append (round three, finding 23).** When a
window-aware wake fails with a `WindowFailure` and the event's status
history holds no row with `compact_context`, the runner calls
`EventStore.append_failed_with_retry(event, run_id, error, *,
retry_detail)`, which under the store lock appends **two** rows: the
`failed` row for this run (as `append_failed` writes today, plus
`error_type`), and a full copied pending event with the same `event_id`
and fields, `detail: {"compact_context": true, "retry_of_run": <run_id>,
"reason": "count_unavailable" | "exhausted_before_request" |
"truncated_reply"}`, due immediately; the method re-checks under the lock
that no compact row exists and appends only the `failed` row if one does.
The two lines are one buffer, written, flushed and fsynced with the
file's growth verified, as `Ledger.append_unlocked` does (this change
gives `EventStore._append_unlocked` the same discipline). That is not
crash-atomic (round four, finding 32): a power loss or short write can
persist the `failed` row without its retry, or leave a torn second line.
The contract is therefore declared, not claimed away: a `failed` row
persisted without its compact retry leaves the event terminal-failed with
no retry, exactly where a failed wake lands today; a torn final line is
the store's pre-existing hazard (the reader does not tolerate it) and is
not widened by this write beyond one extra line. `recover_orphaned_running`
copies the most recent pending record, so a crashed compact `running`
run is recovered compact, and the marker prevents a third **deliberate**
attempt.

**The compact run.** The prepared wake is built compact: the envelope at
metadata-only stubs from the first pass, the prior state, memory and
curator context rendered with every `_activity_log` **omitted** (a note
under the state heading says so and that the record has it;
`_activity_log` is the harness's record, not the resident's curation, so
omitting it cuts nothing of the resident's), and the budget fields as §1
allows. A second `WindowFailure` is terminal, recorded as today, and the
door is not re-pended again for that event.

**The close pass is attempt-aware (round three, finding 22; round four,
31).** Today `eligible_positions` classifies a position as `wake_failed`
by the event's **latest** status, so a compact `pending`/`running`/
`completed` row after a failed first attempt would hide that failure and
silently drop `position_from_failed_wake`. The change: `_latest_by_event_id`
keeps its meaning for delivery and absence, and a new `_runs_by_event`
builds a per-run lifecycle: each `run_id`'s latest status, and whether it
is **superseded**. A run is superseded when a later pending row for the
same event carries `recovered_from_run_id == run_id` at the row's top
level (the marker `recover_orphaned_running` already writes, beside
`recovered_by` and `recovered_at`; the nested `detail.recovered_from_run_id`
is accepted too for compatibility) or `detail.retry_of_run == run_id`
(§6's compact retry). The abandoned `running` row itself is left as it
is today. A position is classified against **its own run**: `wake_failed`
when its run's terminal status is `failed`, eligible when its run
completed with the joined record. `running_at_cutoff` considers only runs
that are `running` **and not superseded**, so a recovered orphan cannot
hold a question open or cap it after its successor completed. A completed
compact run that records no position leaves the first attempt's
`wake_failed` cap in force; one that records a position supersedes it
through `active_positions` as today (one latest eligible position per
member). Close tests cover: failed position then compact pending; then
compact running at cutoff; then compact completed without a position
(cap stands); then compact completed with a replacement (replacement
counts); and running → boot recovery → replacement completed before the
cutoff (no `running_at_cutoff`). This is a change to `src/hamutay/assembly/close.py` made under
the operational rule; it changes no outcome of any wake recorded so far
(no event has two runs today) and is listed in the README's held matters.

**Acceptance (round three, finding 29; round four, 32; declared).** The
operational criterion is: **at most two terminalised window-failure
attempts per event, terminal failure allowed, each terminalised attempt
recorded in full.** Orphan re-executions after a process crash remain
what they are today, at-least-once, each leaving its `running` row and
superseded by recovery's pending copy; they are not attempts in this
count and this design neither adds to nor removes that behaviour. A completed wake is made
likely, not guaranteed: a resident whose state alone leaves less than the
floor fails both attempts before generation, recorded as such, and the
harness does not cut the resident's state to prevent that (the house's
standing rule against harness priors on a resident's memory). The launch
note and the failure records make the size visible to the resident and
to the custodian; what to do about a state that no longer fits its own
window is the resident's, and if it cannot act, the custodian's by a
repair message, not the harness's by silent projection.

Not a retry of a truncated *turn* inside a wake (still declared out):
the retry is a new wake with a smaller prompt, not the same prompt
re-thought.

## What stays byte-identical

With `policy.limit is None`: every request payload, the rendered system
prompt, the envelope, the launch note and the launch record, and every
**completed** wake record. The one declared exception is a failed wake's
record on `finish_reason=length` (§4), which gains
`failure_classification.truncated_reply`, real `usage`, earlier
`interim_text`, and whose `failure_classification.error_type` becomes
`"TruncatedReply"`. Golden fixtures captured from commit `0aeb0674`
before implementation pin the first list; a second fixture pins the
no-ceiling length failure and the test asserts the new record differs
from it only in those four places. §6 never fires on a door that is not
window-aware (the retry is gated on it explicitly, and `TruncatedReply`
on a no-ceiling door is recorded and terminal as today).

## Testing

Unit (`tests/test_context_ceiling.py`, extended, and
`tests/test_context_policy.py`), against a scripted `_post_chat` and a
scripted tokenizer (`/apply-template` and `/tokenize` answered by a fake
that returns a count the test chooses):

1. Turn 0 at or above the soft threshold withdraws perception tools before
   the first request; the note cites the count and its source.
2. With tokenizer and `reasoning_budget == "probed"`: a request with `room
   < THINK_UNRESTRICTED_ROOM_TOKENS` carries `max_tokens ==
   min(configured, room)`, `reasoning_budget_tokens == max_tokens -
   REPLY_RESERVE_TOKENS - forced_sequence_tokens`, the message; one with
   more room carries only `max_tokens`; `unsupported` and `inconclusive`
   carry only `max_tokens`; every sent payload satisfies `prompt_tokens +
   max_tokens < limit` (asserted in the loop; the test also checks the
   recorded payloads, including the equality boundary `prompt_tokens +
   max_tokens == limit - 1`).
3. Fail closed: a tokenizer that errors yields no payload, the
   `count_unavailable` event and a `CountUnavailable`; a ceiling with no
   tokenizer is not window-aware and its payloads equal the 9-06 golden.
4. `max_tokens < REPLY_RESERVE + THINK_FLOOR + forced_sequence_tokens`
   fails before any request (no payload recorded) with
   `ExhaustedBeforeRequest`, for a configured `--max-tokens` below the
   floor, at it, and above it with room below it; budget fields appear
   only with `tool_choice == "none"`; the near-wall one-turn rule fires
   below the unrestricted room and the three-turn rule above it.
5. Envelope projection: small result unchanged as an object; large result
   a typed dict; below `MIN_STUB_CHARS` metadata only; `lean_activity_logs`
   on fixtures built from real `tool_recall` (by cycle, by record id, by
   field) and `tool_walk` (both modes) leaves no `parameters` under any
   `_activity_log` and touches nothing else; arguments not mutated
   (identity and equality); completed and failed records carry full
   results; `_context_error_count` and `branch_visible_context_results`
   unchanged on a capped wake.
6. Admission at the prepared wake: a scripted count above the target
   halves the cap from the full results each pass until under; an empty
   result list and a state-alone-over-target case terminate in one pass
   with `over_target: true`; the pass bound holds; the involuntary memory
   is picked once (the pick is counted).
7. Lean rendering: state, memory and curator sections parsed back to JSON
   have activity entries with exactly the five keys; the note is present;
   the callers' objects are byte-identical; without the flag,
   byte-identical prompt.
8. `TruncatedReply` on turn N of a three-turn script on each of the four
   OpenAI paths: record carries `truncated_reply` (text once, content and
   reasoning_content both), `interim_text` of turns < N, `usage` equal to
   the sum over all N turns, cost fields present, `error_type ==
   "TruncatedReply"`.
9. Golden: with no limit, the payloads of a two-turn tool wake, the
   system prompt, the launch note and a completed record equal the
   fixtures from `0aeb0674`; the no-ceiling length-failure record differs
   from its fixture only in the four named places.
10. `ContextPolicy.for_launch` with scripted `/props`, `/tokenize` and
    probe replies: the four `reasoning_budget` outcomes, the cache hit on
    an unchanged key and the re-probe on a changed one,
    `forced_sequence_tokens` from the scripted tokenizer;
    `apply_context_limit` builds and probes first and assigns once (a
    failing probe leaves the old value); after a replacement the backend,
    `run_next_event`, `run_pending_events`, `step_pending_events`, the
    fork/join runner and the CLI path all see the new value with no
    restart.
11. Compact retry: each of the three typed failures produces one locked
    append of the `failed` row plus the compact pending copy; a second
    call with a compact row present appends only `failed`; the retried
    wake's prompt has no `_activity_log` and a stub-only envelope; boot
    recovery of a crashed compact `running` run yields exactly one compact
    pending row; no retry on a door that is not window-aware.
13. Attempt-aware close (`tests/assembly/test_close.py`): a member's
    position from a failed first run followed by a compact pending row,
    a compact running row at cutoff, a compact completion without a
    position, and a compact completion with a replacement position, each
    classified as §6 states; a `running` run superseded by boot recovery
    whose successor completed is not `running_at_cutoff`, using the actual
    pending row `recover_orphaned_running` returns (not a hand-built one);
    the existing close tests unchanged.
15. Store write discipline: `_append_unlocked` flushes, fsyncs and
    verifies growth; the two-line transition is one write; a `failed`
    row without its retry (fixture) reads as terminal-failed with no
    retry and no crash.
16. Admission ordering: a first candidate below the floor that fits
    after one cap halving is admitted (no `ExhaustedBeforeRequest`
    raised during admission); the payload sent at turn 0 after a
    soft-threshold withdrawal is the rebuilt, recounted one (the
    scripted tokenizer records every count call and the test asserts the
    last count precedes the send and matches the sent payload).
17. No-tokenizer ceiling: a two-turn wake with `--context-limit` and no
    tokenizer produces payloads and a system prompt byte-identical to
    the 9-06 golden (lean rendering off, no count calls).
14. `prepare`/`call_prepared`: on each of the four paths the payload sent
    first equals `Prepared.payload` byte for byte and carries `model`; the
    session's admission loop calls `prepare(candidate=True)` per pass and
    `call_prepared` once; later payloads in the loop each pass through
    `_count_and_bound` (the scripted tokenizer sees one count per send);
    the record's `user_message` is the final rendered envelope and
    `admission` is present on the wake record and the store's
    completed/failed records.
12. Launch note and record: the clause is formatted from the constants and
    absent without a limit.
18. (r6.4, §1a) `think_switch`: "template" when the template source contains
    `enable_thinking` and the door is window-aware, "none" otherwise (a
    template without the string; a cached probe; no llama-server); `as_dict`
    carries it.
19. (r6.4, §1a) The gate: a scripted two-turn wake that withdraws perception on
    turn 1 sends turn 0 without `chat_template_kwargs` and turn 1 (state tools
    active, `tool_choice: "auto"`) and turn 2 (`tool_choice: "none"`) with
    `{"enable_thinking": false}`; the counter receives the payload with the
    kwargs already in it; the withdrawal note carries the gate sentence exactly;
    one `budget_pressure / think_closed` event per gated turn with
    `turn_index`, `prompt_tokens`, `max_tokens`. Three negatives, each
    asserting no kwargs and no sentence and no event: `reasoning_budget ==
    "probed"`; `think_switch == "none"`; a door that is not window-aware (the
    golden of item 9 is the byte-identity proof). The launch clause names the
    gate in each of its three forms.

Integration (`tests/integration/test_local_window.py`, skipped unless
`http://127.0.0.1:8081/props` answers; run by the custodian, outside any
door's wake, with the output pasted into the review record before merge):

- (a) `/apply-template` + `/tokenize(add_special=true, parse_special=true)`
  on three real payloads (no tools; tools; tools with `tool_choice:
  "none"`) **equals** the `usage.prompt_tokens` the server reports for the
  same request with `max_tokens: 1`.
- (b) the probe classifies the live server, and the result is the same on
  a second run (cache key stable).
- (c) observational, recorded, not pass/fail: `seed: 7`, `temperature:
  0`, tools active, `tool_choice: "auto"`, `reasoning_budget_tokens: 32`
  on a tool-inviting prompt; the raw reply and the loop's handling are
  written into the review record as evidence for or against lifting the
  grammar-free gate.
- (d) `forced_sequence_tokens` from `/tokenize` over the message plus the
  end tag equals, within the tokenizer's own count of the message alone,
  the `completion_tokens` difference between a zero-budget reply and its
  control on the probe prompt; recorded as observational if the two
  replies produce other text.
- (e) (r6.4, §1a) with `chat_template_kwargs: {"enable_thinking": false}`
  on the tools payload: the count of (a) **equals** `usage.prompt_tokens`;
  the reply's content opens with the closed block (`<think>\n\n</think>`);
  a tool-inviting prompt with `tool_choice: "auto"` returns
  `finish_reason: tool_calls` with a parsed call. May run against a scratch
  instance of the same build on another port (`HAMUTAY_LOCAL_SERVER`), so
  the door's server is not touched.

Codex authors an independent validation suite from the invariants above
(`tests/window_validation/`), frozen before its first run.

## Migration

No members change, no procedure change. When the qwen door is idle (it
is; its store has no pending event): restart `hamutay-heartbeat@qwen`
(the log inherits substrate and shape; the launch note shows the window
clause and the probe result). Then one message into its store through
`python -m hamutay.events send`, as on 9-16, stating: the two failed
wakes with their numbers; the fix by commit; that the truncated texts of
9-17 are lost and later ones will be kept; and that the first question
(`9c725552`) is open until 2026-09-24 02:05Z, that its recorded deferral
(ledger seq 11) came from a wake that later failed and will be capped at
the tally as such, and that a position recorded by a completed wake
replaces it. The message states facts and names the tool the door already
has (`take_position`); it asks for nothing. That is a decision, not an
omission (round two, finding 16): the operational requirement is that a
completed wake with the capability to replace the position is
**possible**, not that a replacement is attempted; asking a resident to
vote is the hand the assembly was built to remove. The message's wake gets
the compact retry of §6 if it fails on the window, so the door has two
chances at a completed wake; whether it replaces its position is the
door's.

## Not in this change (declared)

- The resident's state size. Cycle 11 doubled it; that is its curation.
  The harness renders it lean, admits the envelope, and tells the
  resident the numbers; it does not cut the state.
- Server-wide flags (`--reasoning-budget`, `-c`). Per-request budgets
  leave every other client of the server alone and are recorded per turn.
- Streaming with an idle timeout for the local transport (the 9-16 note's
  "unbuilt real fix" for the ReadTimeout class). Separate.
- Retrying a truncated *turn* with the same prompt. §6 retries the wake
  once with a smaller prompt instead.
- Cutting the resident's state. §6 omits only the harness's own
  `_activity_log` from the prompt (declared under §6 "Acceptance").
- Threading. The heartbeat is single-threaded and the lease gate applies
  the policy before the next claim; the holder's one assignment is
  sufficient for that model, documented in code, and every wake record
  carries the policy's `invocation_id` so provenance is checkable (round
  three, finding 30). A shared-session threading model would need a
  session lock around publication; none exists today.
- Any change to the Anthropic backend.
- Fixing llama.cpp's budget sampler for a think opened by the prompt (the
  cause of `unsupported` on this template, §1a). A server patch; when it
  lands the probe reclassifies at launch, §1's budget path takes over on
  the turns it covers, and §1a's gate yields (`reasoning_budget ==
  "probed"`).
- Bounding a think on a perception-open turn (§1a, gap 2).

## Cost

Per request on a ceiling door: two calls to the local server (render and
tokenize, about 50 ms each on a 30K prompt; latency logged). Per wake:
up to `ADMISSION_MAX_PASSES` (8) further render-and-tokenize pairs at the
prepared wake (pass count logged). Per launch against a new
`(build_info, model, template)` key: two bounded completions of at most 48
tokens each, which may queue behind a running wake (`queued` logged) and
warm the prompt cache. Zero API cost. GPU time per failed wake drops from
up to 19 minutes to zero for the fail-closed cases and to at most
`max_tokens` otherwise, the text is kept, and a failed wake gets one
smaller second attempt.
