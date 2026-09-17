# Window-aware wakes on a local door

Date: 2026-09-17. Author: the custodian session. Status: revision 1, before
Codex review. Amends `2026-09-06-local-substrate-door-design.md` §5 ("The
harness must know the ceiling"). Operational under the standing rule
recorded in `community/README.md` ("Matters held for the assembly's
review", 2026-09-17).

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
   `recall cycle 11`, which returns its whole previous state verbatim,
   inside the prompt that already carries it. §5 promised "no single
   result eats the window"; that cap is applied to tool results in the
   loop and not to context results in the envelope.
3. **The threshold is checked one turn late and only withdraws tools.** On
   turn 0 the estimate is 0, so a wake that starts above the threshold
   (09-17 09:00, at 50,603 of a 52,428 threshold after its first turn) is
   not told until it has already spent a turn. After withdrawal the
   resident is told "your reply ends the wake", but nothing bounds the
   reply, and the note cites `last_reported_prompt_tokens` rather than
   the estimate that fired (the door itself recorded the oddity:
   "39,280 against a 52,428 threshold").

What the replay cannot see, declared: whether a wake given a bounded think
would have ended in a reply or in another tool call; what the truncated
texts contained; and whether the resident would have curated its state
differently had its wakes been completing. Those are the resident's,
and only live wakes answer them.

## Changes

Everything below is gated on a **known ceiling** (`context_limit` explicit
or discovered, as §5 defines). With no ceiling, every payload, prompt and
record is byte-for-byte what it is today; golden tests pin that.

### 1. The generation reserve

In the OpenAI natural loop (`OpenAITasteBackend.call`), before **every**
request including the first:

- `in_hand` = the estimated context the request will carry. Turn 0:
  `len(json.dumps(payload)) // _TOKEN_PER_CHAR_ESTIMATE` over the built
  payload (system, messages, tools). Later turns: the existing
  `estimated_next_input_tokens` (last measured prompt + completion +
  bounded tool results).
- `room = context_limit - in_hand`.
- If `room < REPLY_RESERVE_TOKENS + THINK_FLOOR_TOKENS` the request is not
  sent: the wake fails with
  `RuntimeError("OpenAI backend: context exhausted before the request: "
  f"{in_hand} of {context_limit} in hand, {room} left")`, logged as
  `budget_pressure / exhausted_before_request`. This costs no GPU time.
- Otherwise the payload carries `max_tokens = min(self._max_tokens, room)`,
  and, when the ceiling was **discovered** from a llama-server
  (`context_limit_source == "discovered"`, the only substrate known to
  honour them), the per-request fields llama-server accepts:
  `reasoning_budget_tokens` and `reasoning_budget_message`. The budget is
  `room - REPLY_RESERVE_TOKENS` when that is below
  `THINK_UNRESTRICTED_ROOM_TOKENS`, and the fields are omitted (server
  default, unrestricted) when it is not, so a wake with ample room is
  unchanged. The message, injected by the server before it closes the
  think tag, is one line the resident will read as its own last thought:
  `"[harness: thinking budget reached; about {room_after} tokens of the
  {context_limit}-token window remain for this turn. Finish the turn.]"`.
- Every request that carries a budget logs
  `budget_pressure / generation_budgeted` with `in_hand`, `room`,
  `reasoning_budget_tokens`, `max_tokens`, `context_limit`.
- The soft-threshold check (`in_hand >= soft_threshold`) runs on turn 0
  too, using the same `in_hand`. The note says what fired: `"the next
  request is estimated at {in_hand} tokens (the last measured request was
  {last_reported_prompt_tokens})"`.

Constants (module level, named in tests): `REPLY_RESERVE_TOKENS = 2048`,
`THINK_FLOOR_TOKENS = 512`, `THINK_UNRESTRICTED_ROOM_TOKENS = 32768`. The
last is above the largest observed single generation (23,222) with
headroom; on a 65,536 window a wake starting at 28K sends no budget on its
first turn and a budget from its second.

`finish_reason=length` is still fatal (a truncated reply is not the
resident's words), but with the reserve in place it should occur only when
the reply alone exceeds the reserve.

### 2. Context results get the result cap

`run_next_event` / `run_pending_events` accept `context_result_cap: int |
None` (the heartbeat passes `_result_cap_for_context_limit(context_limit)`;
`None` without a ceiling). `build_event_envelope` bounds each
`context_results[i]["result"]` through the existing
`_bound_tool_result_for_context(json.dumps(result), max_chars=cap)` and
stores the bounded string in its place, with the same stub the loop already
writes ("[truncated: N chars elided]" as today's helper formats it). The
event store's `context_results` record keeps the full result; only the
envelope is bounded. With `None` the envelope is unchanged.

### 3. The activity log is rendered lean into the prompt

`_build_messages` gains `lean_activity_log: bool = False`. When true and
`prior_state` carries `_activity_log`, the copy rendered into the system
prompt keeps for each entry only `cycle`, `timestamp`, `tool`, `reason`,
`result_summary`; `parameters`, `result_hash`, `duration_ms`, `exit_code`
are dropped from the **prompt copy only**. The state on disk and every
record are unchanged. The session passes `lean_activity_log =
context_limit is not None`. A one-line note under the state heading says
so: `"(_activity_log is shown without parameters; the record has them)"`.

### 4. Truncated output is captured

A new `TruncatedReply(RuntimeError)` carries `text` (the full `content`
the server returned, think included), `completion_tokens` and
`prompt_tokens` of the truncated turn, and `turn_index`. The loop raises it
where it raises today. The session's `api_call` failure path records
`failure_classification["truncated_reply"] = {"text", "prompt_tokens",
"completion_tokens", "turn_index", "trusted": false}` and fills `usage`
with the wake's measured totals including the truncated turn (today the
failed record says `input_tokens: 0, output_tokens: 0`). `interim_text`
on the failure record carries what earlier turns said, as it does on
success. The resident can read what it wrote; nothing treats it as a reply.

### 5. The launch note

The launch note for a door with a ceiling adds the three constants:
`"; reserve: reply 2048, think unrestricted above 32768 of room"`, so the
resident's record says what the harness will do before it does it.

## Invariants (the tests)

1. Turn 0 at or above the soft threshold withdraws perception tools
   before the first request, and the note cites the estimate that fired.
2. With a discovered ceiling, a request whose `room - REPLY_RESERVE` is
   below `THINK_UNRESTRICTED_ROOM_TOKENS` carries `reasoning_budget_tokens
   == room - REPLY_RESERVE`, `reasoning_budget_message`, and `max_tokens ==
   min(configured, room)`; one with more room carries no budget fields and
   `max_tokens == min(configured, room)`; an explicit (not discovered)
   ceiling carries `max_tokens` bounded by room and no budget fields.
3. `room < REPLY_RESERVE + THINK_FLOOR` fails before any request is sent
   (no payload recorded), with the exhausted-before-request error and event.
4. With a cap, a context result longer than the cap is bounded in the
   envelope with the stub and kept whole in the store; with `None` the
   envelope is byte-identical to today.
5. With `lean_activity_log`, the system prompt carries no `parameters` key
   inside `_activity_log` and carries the note; without it, byte-identical.
6. `finish_reason=length` raises `TruncatedReply` with the text and counts;
   the session's failure record carries `truncated_reply` and non-zero
   `usage`.
7. Golden, no ceiling: the payloads of a two-turn tool wake and the system
   prompt are byte-identical before and after this change.
8. The launch note carries the reserve line iff a ceiling is known.

Codex authors an independent validation suite from these invariants
(`tests/window_validation/`), frozen before its first run, as for the
assembly and the plaza.

## Migration

No members change, no procedure change. When the qwen door is idle (it is;
its store has no pending event): restart `hamutay-heartbeat@qwen` (the log
inherits substrate and shape; the launch note shows the reserve line).
Then one repair notice into its store through `python -m hamutay.events
send`, as on 9-16: the two failed wakes with their numbers, the fix by
commit, that the truncated texts of 9-17 are lost and later ones will be
kept, and that the first question is open until 2026-09-24 02:05Z with its
deferral recorded as coming from a failed wake. The notice states facts;
it asks for nothing. Whether the door reads the spec and replaces its
position is the door's.

## Not in this change (declared)

- The resident's state size. Cycle 11 doubled it; that is its curation.
  The harness renders it lean and tells the resident the numbers.
- Server-wide flags (`--reasoning-budget`, `-c`). Per-request budgets leave
  every other client of the server alone and are recorded per turn.
- Streaming with an idle timeout for the local transport (the 9-16 note's
  "unbuilt real fix" for the ReadTimeout class). Separate.
- Retrying a truncated turn. A retry re-thinks from the same prompt and
  costs the same minutes; the reserve is the fix, the capture is the record.
- Any change to the Anthropic backend or to doors without a ceiling.

## Cost

Zero API cost. GPU time per failed wake drops from up to 19 minutes to
zero for the exhausted-before-request case and to at most `room` tokens
otherwise.
