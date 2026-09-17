# Window-aware wakes on a local door

Date: 2026-09-17. Author: the custodian session. Status: revision 2, after
Codex round one (`2026-09-17-window-aware-wakes-review.md`: 4 Blocking,
5 Significant, 2 Minor; every finding accepted in mechanism). Amends
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

> `prompt_tokens + max_tokens ≤ context_limit`, with `prompt_tokens` the
> server's own count of the rendered prompt, not an estimate.

The backend asserts it before sending (a violated assertion is a harness
defect and raises). With it, `finish_reason=length` can arise only from
the `max_tokens` the harness chose, never from the physical wall, and a
truncated turn is recorded (§4). Everything else in this design is about
making that `max_tokens` large enough to finish a turn and telling the
resident the numbers.

## The context policy (one object, session-owned)

Codex round one, finding 5: the heartbeat, the session and the backend each
inferred the ceiling from private attributes. One frozen dataclass replaces
that:

```
ContextPolicy(
    limit: int | None,            # tokens; None = no ceiling (OpenRouter)
    source: str,                  # "explicit" | "discovered" | "inherited" | "provider default"
    result_cap_chars: int | None, # _result_cap_for_context_limit(limit)
    tokenizer: str | None,        # base URL of a llama-server that answers
                                  #   POST /apply-template and POST /tokenize
    reasoning_budget: str,        # "probed" | "unsupported" | "not_probed"
)
```

`ContextPolicy.for_launch(context_limit, source, base_url, probe=...)` builds
it. `tokenizer` is set when `GET <base>/props` answers with `build_info`
(that is a llama-server, whatever the ceiling's source). `reasoning_budget`
is `"probed"` when a one-request probe at launch (`max_tokens: 8`,
`reasoning_budget_tokens: 0`, `reasoning_budget_message: ""`, no tools)
returns a completion whose content begins with a closed think block;
`"unsupported"` when the server answers but the think is not closed;
`"not_probed"` when there is no tokenizer. The probe costs under a second
of GPU and is logged as `budget_pressure / capability_probe` with the
result. Capability is a fact about the server, not about where the ceiling
number came from (finding 2, second part).

The session owns the policy (`OpenTasteSession.context_policy`), passes it
to the backend (`OpenAITasteBackend(context_policy=)`; the old
`context_limit=` keyword remains as sugar that builds a policy with no
tokenizer) and to the event runner (`run_next_event(context_policy=)`,
`run_pending_events(context_policy=)`; `HeartbeatLoop` stores it and passes
it). `apply_context_limit` replaces the whole policy atomically (a
rediscovery after a lease return re-probes). The launch record carries
the policy as a dict; the launch note prints `limit`, `source`,
`tokenizer` presence and `reasoning_budget`.

## Changes

Everything below is gated on `policy.limit is not None`, except §4, which
is universal (see "What stays byte-identical" for the exact guarantee).

### 1. The exact count and the reserve

In the OpenAI natural loop, before **every** request including the first,
with a tokenizer:

- `prompt_tokens = count(payload)`: POST `<tokenizer>/apply-template` with
  the request body the harness is about to send (messages, tools,
  tool_choice; the server renders the same chat template it will use) and
  POST `<tokenizer>/tokenize` on the returned `prompt` with
  `add_special: false`. One failure of either call falls back to the
  estimate below and logs `budget_pressure / count_unavailable`; the
  fallback estimate is `chars/4 + ESTIMATE_MARGIN_TOKENS` with
  `ESTIMATE_MARGIN_TOKENS = 12000` (above the largest demonstrated
  under-count, 8,686, with headroom), so the fallback errs toward the
  reserve.
- Without a tokenizer (explicit ceiling on a non-llama server): the
  fallback estimate is the count, always.
- `room = limit - prompt_tokens`.
- `overhead = BUDGET_MESSAGE_TOKENS` (the tokenized length of the budget
  message plus 16 for tags, computed once at launch through `/tokenize`,
  or 96 without one).
- If `room - overhead < REPLY_RESERVE_TOKENS + THINK_FLOOR_TOKENS` the
  request is not sent: the wake fails with `RuntimeError("OpenAI backend:
  context exhausted before the request: {prompt_tokens} of {limit} in
  hand, {room} left")`, logged as `budget_pressure /
  exhausted_before_request`. Zero GPU time.
- Otherwise `max_tokens = min(self._max_tokens, room - overhead)`, and the
  property above is asserted.
- With `reasoning_budget == "probed"` and `room - overhead <
  THINK_UNRESTRICTED_ROOM_TOKENS`, the request also carries
  `reasoning_budget_tokens = max_tokens - REPLY_RESERVE_TOKENS` and
  `reasoning_budget_message = "[harness: thinking budget reached; about
  {max_tokens - reasoning_budget_tokens} tokens remain for this turn.
  Finish the turn.]"`. With more room the fields are omitted (server
  default, unrestricted), so a wake with ample room is unchanged.
  llama-server re-arms the budget for every think block, so the budget
  bounds one think, not the turn; the turn is bounded by `max_tokens`.
- Every budgeted request logs `budget_pressure / generation_budgeted` with
  `prompt_tokens`, `count_source` (`"server"` | `"estimate"`), `room`,
  `overhead`, `max_tokens`, `reasoning_budget_tokens`, `limit`.
- The soft-threshold check (`prompt_tokens >= 0.8 * limit`) runs on turn 0
  too, on the same count. The note says what fired: `"the next request
  counts {prompt_tokens} tokens ({count_source}); the last measured
  request was {last_reported_prompt_tokens}"`. After the withdrawal the
  three-turn rule (`all_tools_withdrawn`) is unchanged.

**Budget with tools active (finding 2).** llama-server runs the budget
sampler before the lazy tool grammar; if the model opens tool-call syntax
inside an unclosed think and the budget then forces the message and the
end tag, the turn can parse as malformed content or a malformed tool call.
That is a turn the model had already malformed (a tool call inside a think
is not a tool call), and the loop already survives malformed tool calls
(`_MAX_MALFORMED_PER_WAKE`, a tool result that says so). The design
accepts it as a declared loss and requires the integration test below to
exercise the case on the live server before merge: three requests with
tools active, `tool_choice: "auto"`, a 256-token budget, on a prompt that
invites a tool call; the test records what came back, passes if every
reply was either a parseable tool call, a text reply, or a malformed call
the loop's existing path handles, and fails on anything else. If the
live test fails, `reasoning_budget` fields are sent only when
`tool_choice == "none"` (a one-line gate, named in the test), and the
spec is amended to say so.

Constants (module level, formatted into the launch note from the
constants, never duplicated): `REPLY_RESERVE_TOKENS = 2048`,
`THINK_FLOOR_TOKENS = 512`, `THINK_UNRESTRICTED_ROOM_TOKENS = 32768`,
`ESTIMATE_MARGIN_TOKENS = 12000`, `SOFT_THRESHOLD_FRACTION = 0.8`.

### 2. Context results: a typed projection, deep-copied, and admission

`build_event_envelope(event, context_results, run_id, operational_notes,
*, policy: ContextPolicy | None = None)` never mutates its argument. With a
policy that has a limit, it builds a projection of `context_results` by
deep copy in which:

- any `result` that is a state dict (a `recall` by cycle or record id, a
  `walk` element) is rendered lean (§3's rule applied to
  `_activity_log`), so a recalled state carries no `parameters`;
- any `result` whose serialisation exceeds `CONTEXT_RESULT_CAP_CHARS =
  policy.result_cap_chars // 2` (an eighth of the window in chars, 32,768
  for a 65,536 window) is replaced by a typed object
  `{"truncated": true, "chars": <full>, "chars_kept": <n>, "head":
  <first n chars of the serialisation>, "why": "context result cap"}`, a
  dict, not a JSON string; results under the cap stay the objects they
  were.

The event store's `context_results` (completed and failed records) keep
the full structured results: `_context_error_count`,
`EventPolicy.branch_visible_context_results` and every other reader of
records see what they see today. Tests cover a small result (object,
unchanged), a large one (typed object), a completed and a failed record
after a capped envelope (full), and the argument's identity after the call.

**Admission.** With a tokenizer, after the envelope is built the runner
counts the whole turn-zero prompt (`/apply-template` + `/tokenize` over
system + envelope + tools). If it exceeds `ADMISSION_TARGET_FRACTION =
0.5` of the limit, the projection's context results are re-projected with
the cap halved, repeatedly, until the count is under the target or every
result is a stub; each pass is logged as `budget_pressure /
envelope_admission` with the counts. Without a tokenizer, admission is
skipped (the cap alone applies). The state itself is never cut by the
harness: if a lean state alone exceeds the target, the wake goes ahead
and §1 decides at the request.

### 3. The activity log is rendered lean into the prompt

`_build_messages(..., lean_activity_log: bool = False)`: when true and
`prior_state` (or a memory, or a recalled state via §2) carries
`_activity_log`, the copy rendered into the prompt keeps for each entry
only `cycle`, `timestamp`, `tool`, `reason`, `result_summary`. The
rendering works on a JSON deep copy (`json.loads(json.dumps(...))`); the
caller's state is byte-identical after the call, and a test asserts it.
The state on disk and every record are unchanged. The session passes
`lean_activity_log = policy.limit is not None`. A one-line note under the
state heading says: `"(_activity_log is shown without parameters; the
record has them)"`. The test parses the rendered state section back to
JSON and asserts on the structure, not on the whole prompt string.

### 4. Truncated output is captured (universal)

`TruncatedReply(RuntimeError)` is raised where `finish_reason=length` is
detected today, after the truncated turn's usage has been added to the
wake's totals. It carries a complete snapshot: `text` (the flattened
content, think included), `message` (the raw `choices[0].message` as
returned), `turn_index`, the turn's `prompt_tokens` and
`completion_tokens`, and the wake's cumulative `input_tokens`,
`output_tokens`, `cache_read_tokens`, `cache_creation_tokens`,
`responses` (for cost accounting through `_cost_kwargs`) and
`interim_text` of the earlier turns.

The session's `api_call` failure path, on a `TruncatedReply`, writes
`failure_classification["truncated_reply"] = {"text", "message",
"turn_index", "prompt_tokens", "completion_tokens", "trusted": false}`,
fills `usage` from the cumulative counts (today the record says
`input_tokens: 0, output_tokens: 0`) including cost fields, and sets
`interim_text` to the earlier turns' text only: the truncated text appears
once, under `truncated_reply`, never in `interim_text`. A multi-turn test
asserts the earlier turns' usage and text are retained exactly once.

This applies to every door. A no-ceiling wake that truncates today loses
its text and records zero usage; after this change its failure record
gains `truncated_reply` and real `usage`. That is a record migration,
declared here, and the golden fixture for it is captured before the
change (see Testing).

### 5. The launch note and the launch record

With a limit, the launch note adds one clause formatted from the
constants: `"; window: limit {limit} ({source}), count {server|estimate},
reserve reply {REPLY_RESERVE_TOKENS} floor {THINK_FLOOR_TOKENS}, think
unrestricted above {THINK_UNRESTRICTED_ROOM_TOKENS} of room, reasoning
budget {probed|unsupported|not_probed}"`. The launch record carries
`context_policy` as a dict. Without a limit, note and record are
unchanged.

## What stays byte-identical

With `policy.limit is None`: every request payload, the rendered system
prompt, the envelope, the launch note and the launch record, and every
**completed** wake record. The one declared exception is a failed wake's
record on `finish_reason=length` (§4), which gains fields. Golden
fixtures captured from commit `0aeb0674` before implementation pin the
first list; a second fixture pins the no-ceiling length failure and the
test asserts the new record differs from it only in the named fields.

## Testing

Unit (`tests/test_context_ceiling.py`, extended, and
`tests/test_context_policy.py`), against a scripted `_post_chat` and a
scripted tokenizer:

1. Turn 0 at or above the soft threshold withdraws perception tools before
   the first request; the note cites the count and its source.
2. With tokenizer and `reasoning_budget == "probed"`: a request with `room
   - overhead < THINK_UNRESTRICTED_ROOM_TOKENS` carries `max_tokens ==
   min(configured, room - overhead)`, `reasoning_budget_tokens ==
   max_tokens - REPLY_RESERVE_TOKENS`, the message; one with more room
   carries only `max_tokens`; `reasoning_budget == "unsupported"` carries
   only `max_tokens`; every sent payload satisfies `prompt_tokens +
   max_tokens <= limit` (the assertion is in the loop; the test also
   checks it on the recorded payloads).
3. Count fallback: a tokenizer that errors once yields `count_source ==
   "estimate"` with the margin applied, and a `count_unavailable` event.
4. `room - overhead < REPLY_RESERVE + THINK_FLOOR` fails before any
   request (no payload recorded), with the error and event.
5. Envelope projection: small result unchanged as an object; large result
   a typed dict; recalled state lean; argument not mutated (identity and
   equality); completed and failed records carry full results;
   `_context_error_count` and `branch_visible_context_results` unchanged
   on a capped wake. Admission: a scripted count above the target halves
   the cap until under; the state is never cut.
6. Lean activity log: rendered state parsed back to JSON has entries with
   exactly the five keys; the note is present; the caller's state is
   byte-identical; without the flag, byte-identical prompt.
7. `TruncatedReply` on turn N of a three-turn script: record carries
   `truncated_reply` (text once), `interim_text` of turns < N, `usage`
   equal to the sum over all N turns, cost fields present.
8. Golden: with no limit, the payloads of a two-turn tool wake, the
   system prompt, the launch note and a completed record equal the
   fixtures from `0aeb0674`; the no-ceiling length-failure record differs
   from its fixture only in `failure_classification.truncated_reply`,
   `usage` and `interim_text`.
9. `ContextPolicy.for_launch` with a scripted `/props` and probe: the four
   `(tokenizer, reasoning_budget)` outcomes; `apply_context_limit`
   replaces the policy the backend and runner see.
10. Launch note and record: the clause is formatted from the constants and
    absent without a limit.

Integration (`tests/integration/test_local_window.py`, skipped unless
`http://127.0.0.1:8081/props` answers): (a) `/apply-template` +
`/tokenize` on a real payload equals the `prompt_tokens` the server then
reports for that request, within 8 tokens; (b) the probe classifies the
live server as `"probed"`; (c) the budget-with-tools case described in §1
(three requests; records the replies in the test output; passes only on
the named outcomes). These run before the merge, on the live server,
outside any door's wake, and their output goes into the review record.

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
has (`take_position`); it asks for nothing. That message is the wake that
can repair the assembly outcome (finding 4, second part); whether the door
replaces its position is the door's.

## Not in this change (declared)

- The resident's state size. Cycle 11 doubled it; that is its curation.
  The harness renders it lean, admits the envelope, and tells the
  resident the numbers; it does not cut the state.
- Server-wide flags (`--reasoning-budget`, `-c`). Per-request budgets
  leave every other client of the server alone and are recorded per turn.
- Streaming with an idle timeout for the local transport (the 9-16 note's
  "unbuilt real fix" for the ReadTimeout class). Separate.
- Retrying a truncated turn. A retry re-thinks from the same prompt and
  costs the same minutes; the reserve is the fix, the capture is the record.
- Any change to the Anthropic backend.

## Cost

Two extra HTTP calls per request to the local server (render and tokenize,
about 50 ms each on a 30K prompt) and one probe of under a second at
launch. Zero API cost. GPU time per failed wake drops from up to 19
minutes to zero for the exhausted-before-request case and to at most
`max_tokens` otherwise, and the text is kept.
