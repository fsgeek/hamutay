# Window-aware wakes on a local door

Date: 2026-09-17. Author: the custodian session. Status: revision 3, after
Codex round two (`2026-09-17-window-aware-wakes-review-2.md`: 5 Blocking,
4 Significant, 1 Minor on revision 2; round one had 4/5/2). Every finding
of both rounds is accepted in mechanism except one, declared under §1
("the reply reserve is a target"). Codex's sandbox could not reach the
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

For every request a ceiling-aware door sends:

> `prompt_tokens + max_tokens < context_limit`, with `prompt_tokens` the
> server's own count of the prompt it will tokenize, never an estimate.

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
`reasoning_budget_message: ""`. The raw `message` of each (both `content`
and `reasoning_content`) is inspected for a think body between the
template's tags. `probed` when the control has a think body and the
zero-budget reply has none; `unsupported` when both are identical;
`inconclusive` when the control itself has no think body (the model did
not think; the fields are then not sent and the probe is retried at the
next launch). The result is cached in the launch record keyed by
`(build_info, model_alias, sha256(chat_template))` and reused while the
key matches, so a restart against the same server costs nothing. Each
probe records its wall time and marks `queued` when it exceeded 5 s. Two
bounded completions cost under 100 tokens of generation.

## Changes

Everything below is gated on `policy.limit is not None`, except §4, which
is universal, and §6, which is gated on the two failures §1 and §4 define
(see "What stays byte-identical" for the exact guarantee).

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
  fails with `RuntimeError("OpenAI backend: the prompt could not be
  counted: {error}")`, logged as `budget_pressure / count_unavailable`,
  and qualifies for the one compact retry of §6. On a llama-server ceiling
  an estimate is never the count. Only a ceiling with no tokenizer (an
  explicit `--context-limit` against a server that is not llama-server, a
  case no door has today) uses the estimate `chars/4 +
  ESTIMATE_MARGIN_TOKENS` (`12000`, above the largest demonstrated
  under-count, 8,686), and its launch note says `count estimate` so the
  record shows the property is estimated there.
- `room = limit - 1 - prompt_tokens` (the strict inequality's one token).
- If `room < REPLY_RESERVE_TOKENS + THINK_FLOOR_TOKENS +
  policy.forced_sequence_tokens` the request is not sent: the wake fails
  with `RuntimeError("OpenAI backend: context exhausted before the
  request: {prompt_tokens} of {limit} in hand, {room} left")`, logged as
  `budget_pressure / exhausted_before_request`, and qualifies for §6.
  Zero GPU time.
- Otherwise `max_tokens = min(self._max_tokens, room)`, and the property is
  asserted.
- With `reasoning_budget == "probed"` and `room <
  THINK_UNRESTRICTED_ROOM_TOKENS`, the request also carries
  `reasoning_budget_tokens = max_tokens - REPLY_RESERVE_TOKENS -
  policy.forced_sequence_tokens` and `reasoning_budget_message =
  "[harness: thinking budget reached; about {REPLY_RESERVE_TOKENS} tokens
  remain for this turn. Do not open another think block. Finish the
  turn.]"`. With more room the fields are omitted (server default,
  unrestricted), so a wake with ample room is unchanged.
- Every budgeted request logs `budget_pressure / generation_budgeted` with
  `prompt_tokens`, `room`, `max_tokens`, `reasoning_budget_tokens`,
  `forced_sequence_tokens`, `limit`, and the count latency.
- The soft-threshold check (`prompt_tokens >= SOFT_THRESHOLD_FRACTION *
  limit`) runs on turn 0 too, on the same count. The note says what fired:
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

**Budget with tools active (round one, finding 2).** llama-server runs the
budget sampler before the lazy tool grammar; if the model opens tool-call
syntax inside an unclosed think and the budget then forces the message
and the end tag, the turn can parse as malformed content or a malformed
tool call. That is a turn the model had already malformed, and the loop
already survives malformed tool calls (`_MAX_MALFORMED_PER_WAKE`, a tool
result that says so). The design accepts it as a declared loss and
requires a deterministic live test before merge (Testing, integration c):
`seed: 7`, `temperature: 0`, tools active, `tool_choice: "auto"`, a prompt
that reliably produces a tool call under the control run, and
`reasoning_budget_tokens: 32`; the test asserts the loop's handling of
whatever the server returns (a parseable call, a text reply, or a
malformed call that lands as a tool result) and records the raw reply. If
that test cannot be made to pass, the fields are sent only when
`tool_choice == "none"` (a one-line gate, named in the test) and this
section is amended.

Constants (module level, formatted into the launch note from the
constants, never duplicated): `REPLY_RESERVE_TOKENS = 2048`,
`THINK_FLOOR_TOKENS = 512`, `THINK_UNRESTRICTED_ROOM_TOKENS = 32768`,
`ESTIMATE_MARGIN_TOKENS = 12000`, `SOFT_THRESHOLD_FRACTION = 0.8`.

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

**Admission at the prepared wake (round two, finding 14).** The runner
does not know the system prompt, the involuntary memory, the curator
context, the constitution filtering or the offered tools; the session
assembles them once in `_exchange_impl`. So the runner passes the session
an `envelope: Callable[[int | None], str]`, a closure over the **immutable
full** `context_results` that returns the envelope built at a given cap
(the runner still records the full results). At the prepared-wake
boundary, after `_build_messages` and the tools list exist and before the
backend is called, the session with a tokenizer counts the exact prompt
(`/apply-template` + `/tokenize`, as §1) with `envelope(cap)` as the user
message. If the count exceeds `ADMISSION_TARGET_FRACTION = 0.5` of the
limit it halves the cap and rebuilds from the full results, at most
`ADMISSION_MAX_PASSES = 8` times, stopping when under the target or when
every result is a metadata-only stub. Each pass logs `budget_pressure /
envelope_admission` with the cap and the count. The outcome is recorded
on the wake as `admission: {passes, final_cap, count, over_target:
bool}`; when the state and system prompt alone exceed the target the
outcome says so (`over_target: true, envelope_exhausted: true`) and the
wake proceeds to §1, which decides at the request. The state is never cut
by the harness. Without a tokenizer, admission is skipped and the initial
cap alone applies.

### 3. The activity log is rendered lean into the prompt

`_build_messages(..., lean_activity_log: bool = False)`: when true, the
prior state, the involuntary memory and the curator context are each
rendered through the same `lean_activity_logs` projection §2 defines, on a
JSON deep copy (`json.loads(json.dumps(...))`); the caller's objects are
byte-identical after the call, and a test asserts it.
The state on disk and every record are unchanged. The session passes
`lean_activity_log = policy.limit is not None`. A one-line note under the
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
budget {probed|unsupported|inconclusive|not_probed}, compact retry once"`.
The launch record carries `context_policy` as a dict. Without a limit,
note and record are unchanged.

### 6. One compact retry (completion recovery)

Round two, finding 16: a door whose wakes fail on the window, with no
pending event, is left exactly where it was. So the runner gives a wake
one more chance, once. When a wake fails with `count_unavailable`,
`exhausted_before_request` or `TruncatedReply` and the event's status
history holds no earlier `compact_context` retry, the runner re-pends the
event with `detail: {"compact_context": true, "retry_of_run": <run_id>,
"reason": <which failure>}`, due immediately. On that run the prepared
wake is built compact: the envelope at metadata-only stubs from the first
pass, the prior state, memory and curator context rendered with every
`_activity_log` **omitted** (a note under the state heading says so and
that the record has it; `_activity_log` is the harness's record, not the
resident's curation, so omitting it from the prompt cuts nothing of the
resident's), and the `generation_budgeted` fields from turn 0 when the
server is `probed`. A second failure is terminal, recorded as today, and
the door is not re-pended again for that event. The two runs are joined in
the store by `retry_of_run`, so the close pass and the report see one
event with two attempts. This is the mechanism that gives the migration
wake of §Migration its second chance; it is not specific to it.

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
from it only in those four places. §6 never fires without a ceiling
(its three triggers are ceiling-gated except `TruncatedReply`, and the
retry is gated on `policy.limit is not None` explicitly).

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
   `count_unavailable` event and error; a no-tokenizer explicit ceiling
   uses the estimate with the margin and says `count estimate`.
4. `room < REPLY_RESERVE + THINK_FLOOR + forced_sequence_tokens` fails
   before any request (no payload recorded), with the error and event.
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
11. Compact retry: each of the three failures re-pends the event once with
    the detail; the retried wake's prompt has no `_activity_log` and a
    stub-only envelope; a second failure does not re-pend; no retry
    without a ceiling.
12. Launch note and record: the clause is formatted from the constants and
    absent without a limit.

Integration (`tests/integration/test_local_window.py`, skipped unless
`http://127.0.0.1:8081/props` answers; run by the custodian, outside any
door's wake, with the output pasted into the review record before merge):

- (a) `/apply-template` + `/tokenize(add_special=true, parse_special=true)`
  on three real payloads (no tools; tools; tools with `tool_choice:
  "none"`) **equals** the `usage.prompt_tokens` the server reports for the
  same request with `max_tokens: 1`.
- (b) the probe classifies the live server, and the result is the same on
  a second run (cache key stable).
- (c) the deterministic budget-with-tools case of §1.
- (d) `forced_sequence_tokens` equals the difference in
  `completion_tokens` between a zero-budget reply and its control when
  both produce no other text (bounded prompt, `max_tokens: 48`).

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
  `_activity_log` from the prompt.
- Any change to the Anthropic backend.

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
