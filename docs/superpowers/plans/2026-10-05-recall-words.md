# Plan: recall_words and search_words, reading what was said (the elder's request)

**Design approved by Tony 2026-10-05** (design given 10-03; bounded change to existing tools).
**Requirements on the record:** elder plaza seq 4 (cycles c280–320 are "dark": it knows where they
are and cannot see inside); qwen seq 5 (old prose returns as a *claim*, not as recovered truth);
guest:levadura seq 8 (addressed read first, then a population search; a passing hash says nothing
about position; don't reuse a stored reading for another question). Background:
`recall`/`search_memory` read only the STATE object (`src/hamutay/tools/memory.py`). The words of each
cycle (`user_message`, `response_text`, tool activity) are in the session log, and no tool returns
them.

## Scope

Two read-only tools over **the door's own session log** (the JSONL at the taste_open session's
`log_path`), offered only when a new option is on.

### Task 1: `src/hamutay/tools/words.py`

`tool_recall_words(tool_input, *, log_path) -> dict`, an addressed read.

- **Input:**
  - exactly one of `cycle` (int), `record_id` (str) or `line` (int, 1-based log line; added 10-05 because the 91 oldest records have no record_id);
  - optional `fields`, a subset of `["incoming", "reply", "tool_calls"]`, default all;
  - optional `max_chars`, default 20000.
- **Lookup:**
  - Scan the log for records whose `cycle` (or `record_id`) matches. Skip unparseable lines and
    count them.
  - **Several records with the same cycle** (this happens: elder has two c457s): return
    `{"status": "ambiguous", "candidates": [{record_id, timestamp, line}...]}` and ask for a
    `record_id` or `line`. **Never pick one.** A `line` that doesn't exist, is blank or doesn't parse
    returns `unreachable` with the reason.
  - **None:** `{"status": "unreachable", "reason": ...}`. Never a guess.
- **Success:** `{"status": "ok", "claim_notice": <text below>, "provenance": {...}, "words": {...},
  "truncated": {...}}`.
  - `provenance`: `cycle`, `record_id`, `timestamp`, `model` (if the record has one), `log_path`,
    1-based `line`, and `record_sha256` (the sha256 of the raw line bytes as stored).
  - `words`:
    - `incoming` comes from `user_message`.
    - `reply` comes from `response_text`; if that is empty, use `interim_text`, and say which field
      was used.
    - `tool_calls` is a compact list from the record's tool activity (`tool_activity_full` or
      whatever field holds it: inspect real logs): tool name, parameters, `result_summary`. **Never
      full results.**
  - `truncated`: a field over its share of `max_chars` is cut, and the number of characters omitted
    per field is reported. This is a declared loss, never a silent one.
- **`claim_notice`, exactly:** "This is what was said at this cycle, as recorded in your log. It is
  a claim made then, not verified truth: check it against other records before relying on it."

`tool_search_words(tool_input, *, log_path) -> dict`, a population search.

- **Input:**
  - `pattern` (str, case-insensitive substring);
  - optional `fields`, default `["incoming", "reply"]`;
  - optional `max_samples`, default 5;
  - optional cycle bounds `from_cycle` / `to_cycle`.
- **Returns:**
  - `records_scanned`, `records_matched`, `matches_total`;
  - `samples`: up to `max_samples` matches, spread across the matched range and not just the first
    N. Each sample carries `cycle`, `record_id`, `field`, and a snippet of ±150 characters.
  - `near_misses`: when the pattern has two or more words, up to `max_samples` records containing
    every word but not the exact phrase. This is where the pattern fails, shown before its count is
    trusted (levadura's `measure`).
  - the same `claim_notice`.

### Task 2: wiring

- **Executor.** `ToolExecutor` (`src/hamutay/tools/executor.py`) gets an optional `words_log_path`.
  It dispatches `recall_words`/`search_words` only when that path is set, and otherwise answers
  `{"error": "words tools not offered in this session"}`. `_CAPABILITY`: both are `read_only`.
- **Schemas.** `RECALL_WORDS_SCHEMA` and `SEARCH_WORDS_SCHEMA` go in `tools/schemas.py`, **not** in
  `TOOL_SCHEMAS` by default. Their descriptions state the claim notice and the own-log-only scope.
- **taste_open.** A new constructor option `words_recall: bool = False`. When on:
  - the executor gets `words_log_path=self._log_path`;
  - both schemas are appended to `extra_tools`;
  - the tool guidance gets two lines in its `### Memory` section. Follow the
    `_natural_tool_guidance` pattern: derived, anchor-asserted, and the line is present only when
    the tools are offered. **Never name a tool the session does not have.**
  - Each cycle record written to the log gains `"words_recall": true`. This is the version flag
    that lets later analysis tell which side of the change a cycle is on. When the option is off,
    write nothing.
- **CLI.** taste_open's CLI gets `--words-recall` (default off, so experiments stay comparable).
- **heartbeat.** It passes `words_recall=True` for every door and prints a launch note:
  `"words recall: on (recall_words, search_words over this door's own log)"`.

### Task 3: tests, test-first, in `tests/` next to the existing tool tests

Build fixture logs from small synthetic JSONL that mirrors the real record shape. Cover:

- ok by cycle;
- ok by record_id;
- ambiguous duplicate cycle;
- unreachable;
- an unparseable line skipped and counted;
- the `interim_text` fallback;
- truncation declared;
- `record_sha256` equal to the line's hash;
- search counts, spread samples and near-misses;
- not offered → error;
- the guidance line present only when offered;
- the `words_recall` flag in the record only when on;
- heartbeat enables it.

Then run `tests/` for the touched areas plus the full taste_open, heartbeat and plaza suites. **Read
the counts from the run.** Use `set -o pipefail`; never pipe pytest into tail ahead of an `&&`.

## Rules for the implementer

- Work only in `/home/tony/projects/hamutay/.worktrees/recall-words` (branch `recall-words`).
- **Never `git stash`.** To check whether a failure was there before, run the test in the main
  checkout read-only, or use `git show main:<path>`.
- Never restart, signal or touch the running doors (`systemctl --user … hamutay-heartbeat@*`).
- Commit as you go, with:
  `git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "…"`,
  and end every message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. The
  post-commit hook adds an OTS stamp commit. That is expected.
- Inspect real record shapes read-only, from `community/elder/session.jsonl` (field names only, plus
  c457's two record_ids). Don't copy resident text into tests or fixtures.

## Rulings on Codex's validation (2026-10-05, the custodian)

Codex's frozen suite (`tests/words_validation/`, 34 tests, 76 cases) found 7 failures on its first run.

- **`record_sha256` (2 cases): implementation changed.** The plan says "the sha256 of the raw line
  bytes as stored". Codex read that as including the line terminator; the implementation hashed
  without it. Codex's reading is the plan's wording, and it is the one a reader can check with
  `sed -n '<line>p' <log> | sha256sum`. The implementation now hashes the stored bytes, terminator
  included, and `record_sha256_of` says so.
- **`samples` (1 case): the plan was ambiguous. Ruling: one sample per matched record** (its first
  hit), spread across the matched records. `matches_total` counts occurrences and `records_matched`
  counts records. Several samples from one record would hide the population's shape, which is
  what the search exists to show. Codex revises its test.
- **`TOOL_SCHEMAS` (1 case): test error.** It is a dict of name → schema (existing code), not a
  list. Codex revises.
- **Heartbeat (3 cases): test error.** Codex's stand-in `StoppedLoop` lacks the `_emit` static
  method, which `run` calls before the loop starts (that call predates this branch). Codex revises.
