# Independent viewer validation plan

Authority: the contract in viewer/state.py, viewer/__main__.py, the page footer,
and the user's review request. Modify only this new validation package; leave
production code untouched; never run git. Known defects must fail normally,
without xfail or assertions that bless the current incorrect behavior.

1. Construct a temporary community with members, guests, valid plaza messages
   and delivery records, assembly records, event and billing logs, and private
   home files containing distinct secret sentinels (`conftest.py`).
2. Test gathering, metadata and billing, privacy (including forbidden reads),
   filesystem immutability, tolerant JSONL reads, plaza errors, and assembly
   extension rounds (`test_state.py`).
3. Exercise actual HTTP request dispatch using an in-memory connection, test
   the endpoint allowlist and unsupported writes, and intercept server startup
   to assert the sole bind address is 127.0.0.1 (`test_http.py`).
4. Execute page.html's actual script in Node's VM with a minimal document and
   disabled networking/timers. Inspect rendered HTML with Python's HTMLParser
   for injected elements/attributes, and pin public assembly/error content
   (`render_page.js`, `test_page.py`). This is script execution and HTML parsing,
   not a full browser integration test; Node must be available.
5. Run `PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -p no:cacheprovider
   tests/validation_viewer -q` and report the actual failures with production
   file:line references. Add no production fixes and hide no failures.

## Narrowed mail contract validation

Use the writing-plans workflow within this existing validation package.
Only a completed wake joined to Tony's pending event may expose its reply.
All other wake response text remains private. Leave `src/` untouched and
never run git; defects must fail normally, without xfail.

- [x] Add `test_replies.py` using the existing temporary community, real HTTP
  handler, and page script harness. Cover exact sender matching, pending to
  completed joins without sender on outcomes, reflection/orphan responses,
  failed/running states, recovery duplicates, conflicting duplicate senders,
  and event IDs reused across doors.
- [x] Exercise literal reply XSS, long replies, waiting status and current
  timed quiet with the existing Node VM/HTML parser; extend only the harness
  operation allowlist to call `renderReplies` directly.
- [x] Run `uv run pytest tests/validation_viewer` and report Blocking/Should/Nit
  findings with references and the actual pass/fail totals.

Result: 102 passed, 6 failed. The failures expose the conflicting-pending
privacy leak in state/HTTP/page (3), expired/suppressed status rendering (2),
and shared-door event ID collisions in reply controls (1). The initial uv
invocation could not write its default cache; the completed invocation used
`UV_CACHE_DIR=/tmp/hamutay-viewer-uv-cache` with the requested pytest command.

## 2026-10-13 — Sections navigation, refresh counts, and older replies

Contract review: no Blocking findings. The supplied new contract is the
authority; the checked-out page is deliberately old. Write only within
`tests/validation_viewer/`, leave `src/` untouched, and make no commits.
The user's explicit test-writing process takes precedence over skill steps
that would request another design approval, production implementation, or
files outside this package. Failures remain ordinary assertions, never xfail.

- [x] Extend `render_page.js` with optional initial localStorage values,
  recorded textContent/innerHTML assignments, successive refresh snapshots,
  and dispatch of long-message clicks through the page's real event listener.
  Keep execution of the actual page script and existing harness inputs intact.
- [x] Add `test_navigation.py`: parse static HTML for the Sections nav,
  header/nav/doors ordering, exact ordered fragment links, unique existing
  section targets, heading text, and counter elements within the nav. Check
  the stylesheet for a nav-matching `position: sticky` rule.
- [x] Exercise real refreshes with hand-derived reply, plaza, and assembly
  counts: empty data, all completed and all unanswered statuses, counts over
  folded replies, strict cursor comparison, sparse sequences, last-row seq,
  and missing stored cursor. Observe textContent writes and forbid any
  innerHTML assignments to counter elements, including adversarial seq text.
  Successive refreshes must clear stale counts and retain the cursor read at
  page load even after localStorage is written.
- [x] Parse rendered reply structure to verify the minimum three open rows,
  strict seven-day cutoff (including one second either side), leading-prefix
  stop rule, single closed `details.older`, retained order and rows, no fold
  for short/all-recent input, and singular/plural summary with last-row age.
  Folded rows must preserve literal escaping, long-message controls (including
  expand/collapse and the opened state across re-renders), and waiting/failed/
  quiet messages and per-row markup. Reply fixtures respect newest-first order.
- [x] Run `uv run pytest tests/validation_viewer -q` with cache/bytecode
  artifacts directed outside production files, read the exact totals and
  failure names, and record which expected new-contract failures the old
  page exhibits. Report any existing-suite failure separately.

Scope of verification: Node VM script execution plus HTML parsing, not a
browser layout test. Sticky positioning is checked from stylesheet text as
the contract permits. Fixtures use valid timestamps and valid stored numeric
cursors; malformed timestamps/cursors have no specified new behavior.


Validation result: **44 failed, 113 passed in 6.82s** (157 tests). All 108
pre-existing tests passed. Of 49 added cases, 44 failed as expected against
the old page; five passed (`empty`, `one-old`, `two-old`, `three-old`, and
`all-recent` in the folding boundary test), since they require no folding.

The 44 failures comprise:

- 8 static navigation checks: no Sections nav, no heading fragment ids,
  and no static counter elements. The sticky test fails first on the missing
  nav landmark; the old stylesheet also has no sticky nav rule.
- 19 refresh-counter checks: the old script never writes any `nav-*` counter,
  including empty-state, literal-text, and successive-refresh cases.
- 17 folding checks: the old renderer places every reply outside details,
  so all cases needing a fold, its summary, or folded row controls/status
  fail because `details.older` is missing. Existing per-row escaping, status
  markup, and expand/collapse assertions pass before the fold assertion.

The first plain uv launch failed before collection because it tried to
create a fresh environment and fetch unavailable dependencies. The temporary
`.venv` it created was removed. The successful test invocation used the
existing environment, disabled syncing, and explicitly loaded this worktree's
source; no production files were edited and no commits were made:

```sh
UV_CACHE_DIR=/tmp/hamutay-viewer-uv-cache UV_PROJECT_ENVIRONMENT=/home/tony/projects/hamutay/.venv UV_NO_SYNC=1 PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' uv run pytest tests/validation_viewer -q
```

Exact failing tests (all in `tests/validation_viewer/test_navigation.py`,
copied from the final pytest run):

```text
test_sections_nav_follows_header_precedes_doors_and_links_in_order
test_static_section_heading_is_a_unique_fragment_target[replies-h-Replies to you]
test_static_section_heading_is_a_unique_fragment_target[plaza-h-The plaza]
test_static_section_heading_is_a_unique_fragment_target[assembly-h-The assembly]
test_counter_exists_in_static_sections_nav[nav-replies]
test_counter_exists_in_static_sections_nav[nav-plaza]
test_counter_exists_in_static_sections_nav[nav-assembly]
test_sections_nav_has_sticky_position_in_stylesheet
test_refresh_counts_all_replies_and_every_noncompleted_status[empty]
test_refresh_counts_all_replies_and_every_noncompleted_status[one-completed]
test_refresh_counts_all_replies_and_every_noncompleted_status[counts-folded-rows]
test_refresh_counts_all_replies_and_every_noncompleted_status[all-noncompleted-statuses]
test_refresh_counts_all_replies_and_every_noncompleted_status[one-unanswered]
test_refresh_plaza_uses_last_row_seq_and_counts_rows_above_loaded_cursor[empty]
test_refresh_plaza_uses_last_row_seq_and_counts_rows_above_loaded_cursor[strict-gapped-cursor]
test_refresh_plaza_uses_last_row_seq_and_counts_rows_above_loaded_cursor[all-seen]
test_refresh_plaza_uses_last_row_seq_and_counts_rows_above_loaded_cursor[cursor-ahead]
test_refresh_plaza_uses_last_row_seq_and_counts_rows_above_loaded_cursor[missing-cursor]
test_refresh_plaza_uses_last_row_seq_and_counts_rows_above_loaded_cursor[zero-cursor]
test_refresh_plaza_uses_last_row_seq_and_counts_rows_above_loaded_cursor[last-row-not-maximum]
test_refresh_assembly_counts_only_questions_without_closing[empty]
test_refresh_assembly_counts_only_questions_without_closing[one-open]
test_refresh_assembly_counts_only_questions_without_closing[all-closed]
test_refresh_assembly_counts_only_questions_without_closing[mixed]
test_refresh_counters_use_textcontent_even_for_html_in_state
test_successive_refreshes_clear_stale_counts
test_successive_refreshes_keep_cursor_read_at_page_load
test_reply_folding_keeps_leading_three_or_recent_rows_without_dropping_any[four-old]
test_reply_folding_keeps_leading_three_or_recent_rows_without_dropping_any[one-second-inside]
test_reply_folding_keeps_leading_three_or_recent_rows_without_dropping_any[exact-cutoff]
test_reply_folding_keeps_leading_three_or_recent_rows_without_dropping_any[one-second-outside]
test_reply_folding_keeps_leading_three_or_recent_rows_without_dropping_any[many-old]
test_older_summary_uses_folded_count_and_last_rows_relative_age[singular]
test_older_summary_uses_folded_count_and_last_rows_relative_age[plural-last-row]
test_older_summary_uses_folded_count_and_last_rows_relative_age[many-last-row]
test_folded_replies_preserve_row_markup_escaping_and_long_message_controls
test_folded_long_reply_toggle_expands_collapses_and_survives_rerender
test_folded_unanswered_rows_keep_waiting_failed_and_quiet_texts[pending]
test_folded_unanswered_rows_keep_waiting_failed_and_quiet_texts[elapsed-quiet]
test_folded_unanswered_rows_keep_waiting_failed_and_quiet_texts[future-quiet]
test_folded_unanswered_rows_keep_waiting_failed_and_quiet_texts[running]
test_folded_unanswered_rows_keep_waiting_failed_and_quiet_texts[failed]
test_folded_unanswered_rows_keep_waiting_failed_and_quiet_texts[expired]
test_folded_unanswered_rows_keep_waiting_failed_and_quiet_texts[suppressed]
```
