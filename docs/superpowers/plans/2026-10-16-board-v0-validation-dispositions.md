# Board v0: dispositions of Codex's black-box validation run

Date: 2026-10-16. Suite: `tests/validation_board/` (258 cases, written by Codex from
`docs/superpowers/specs/2026-10-15-board-v0-contract.md` alone, committed unmodified).
First run against the build: 18 failed, 240 passed
(`/home/tony/projects/hamutay/tmp/boardv0-codex-run.txt`).

Classes: **A** implementation defect against the contract (code fixed); **B** Codex
misread an unambiguous clause (test unchanged, clause quoted); **C** contract
ambiguous or silent (behavior decided on the merits, contract revised as r1, code
fixed if needed). No file under `tests/validation_board/` was edited.

Tally: **A 6, B 1, C 11** (18).

| # | Test | Class | Evidence | Action |
|---|---|---|---|---|
| 1 | `test_filters.py::test_board_read_response_and_coverage_not_editable` | A | An unknown tool name returned `{"error": "unknown board tool 'set_board_coverage'"}`; §10: "Every refusal is `{"error": "<tool>: <reason>"}`". | `run_board_tool` now returns `"<name>: not a board tool"`. Passes. |
| 2 | `test_offering.py::test_enabled_executor_dispatches_bound_writer` | C | A ToolExecutor with binding, wake context and `board=True` but no `scheduled_by_record_id` refused with "assembly tools need a cycle record_id". §0 names only binding and wake context; it was silent on the record id. On the merits a board write binds to no cycle, so requiring a cycle id was an accident of reusing the assembly's readiness check. | Board tools now need binding + wake context only; §0 says so (r1). Passes. |
| 3 | `test_records.py::test_writer_normalization` | C | `kind=" ＲＥＶＩＥＷ "` refused. §3 said `kind` is "trimmed and case-folded" (fullwidth survives case-folding), while §5 NFKC-normalizes the same kind values in a filter: the contract disagreed with itself. On the merits one normalization for one vocabulary is right. | Writer normalizes `kind` with NFKC + case-fold + trim, on every path; §3 revised (r1). Passes. |
| 4 | `test_records.py::test_opening_writer_rejects_invalid_fields[why-None]` | C | Codex expects `why: null` to be refused; the contract only said "0–1000 chars" and did not say what `null` means for an optional writer field. On the merits `null` for an optional field means absent: that is how §5 already treats a `null` filter field, a model often sends `null` for an omitted optional, and refusing gains nothing (the field defaults to empty). Required fields given `null` are still refused, and so is any other non-string. | No code change; §3 now states the rule (r1). **Test stays red by decision.** |
| 5 | `test_records.py::test_update_writer_limits[status-reason-None]` | C | Same question for a status `reason: null`. Same reasoning as #4. | As #4; §3 r1. **Test stays red by decision.** |
| 6 | `test_records.py::test_complete_unterminated_json_is_not_discarded` | B | Codex's PLAN ambiguity 4 reads a complete JSON final line without a newline as not torn. §3: "One torn (unterminated) final line is tolerated and is overwritten by the next append." The parenthesis defines torn as unterminated, whether or not the bytes parse. That is also the shared ledger's deliberate rule (a parseable unterminated tail is a cut write; Codex's third plaza review, 2026-09-16). | None. Test stays red. |
| 7 | `test_records.py::test_cli_label_normalization` | A | `post --kind " REVIEW "` was refused by argparse `choices` before the writer ran; §3 r0 already required `kind` "trimmed and case-folded" on all writer paths, so `" REVIEW "` had to be accepted. (`--by " ＴＯＮＹ "` and tags were already normalized.) | CLI `--kind` passes its value to the writer, which normalizes and validates. Passes. |
| 8 | `test_wakes.py::test_envelope_bounds_and_uncovered_remainder[1]` | C | Failed on `1 <= meta["entries_full"]`: the build emitted lists of ids, Codex read counts (PLAN ambiguity 14). §9 named the keys without types. On the merits a key without `_ids` reads as a count, as `remaining_entries` / `remaining_events` already were, and `batch_event_ids` shows the list convention. | `entries_full` / `entries_titles` are now integers; the id lists moved to `entries_full_ids` / `entries_titles_ids`; §9 declares every type (r1). Passes. |
| 9 | `…::test_envelope_bounds_and_uncovered_remainder[10]` | C | As #8. | As #8. Passes. |
| 10 | `…::test_envelope_bounds_and_uncovered_remainder[11]` | C | As #8. | As #8. Passes. |
| 11 | `…::test_envelope_bounds_and_uncovered_remainder[30]` | C | As #8. | As #8. Passes. |
| 12 | `…::test_envelope_bounds_and_uncovered_remainder[35]` | C | As #8. | As #8. Passes. |
| 13 | `test_wakes.py::test_long_entry_preserves_latest_notes_and_progress` | C | An entry at the field limits with 19 notes of ~1,000 chars showed **no** note, because even the newest did not fit under the 6,000-character entry cap. §9 said only "newest first kept if they do not fit" and did not say whether the newest is guaranteed. On the merits the newest note is the entry's current word and must not be the casualty of a cap; the 12,000-character envelope bound is what protects the wake, and it still holds (an entry that does not fit is listed by title). | The newest note is always shown; older notes fill the 6,000 cap newest first; §9 revised (r1). Passes. (Also hit the type question of #8 at its last line.) |
| 14 | `test_wakes.py::test_subscription_snapshot_and_updates` | A | `coverage_after_this_wake` was 2 for one entry. §8: "An opportunity is shown once any board_match for it completed". The count read `board.opportunity_id` from `completed` rows, which do not carry the `board` block, so every completed event counted as an extra "None" opportunity. | Shown opportunities are resolved through each event's pending record. Passes. |
| 15 | `test_wakes.py::test_multiple_updates_render_entry_once` | C | Failed at `meta["entries_full"] == 1` (a list): the type question of #8. It would next have hit #14's defect (`coverage_after_this_wake == 1`). | Covered by #8 and #14. Passes. |
| 16 | `test_wakes.py::test_failed_batch_surfaced_once[1]` | A | The note said "3 will be offered again" and left out the zero terminal count. §8: the note "says … how many will be offered again, and how many reached the 3-attempt limit". | The note now states both counts, as numerals, zero included; §8 says so explicitly. Passes. |
| 17 | `test_wakes.py::test_failed_batch_surfaced_once[3]` | A | Mirror of #16: the zero retry count was omitted. | As #16. Passes. |
| 18 | `test_wakes.py::test_envelope_groups_all_events_of_rendered_entry` | A | `coverage_after_this_wake` was 31, not 35, with 35 previously completed entries. Same defect as #14 (completed rows have no `board` block). | As #14. Passes. |

## After the fixes

`uv run pytest tests/validation_board tests/board -q -p no:cacheprovider`:
3 failed, 313 passed. The three failures are #4 and #5 (C, behavior decided against
Codex's reading) and #6 (B).

Full suite `uv run pytest -q -p no:cacheprovider`: 3 failed (the same three), 4036
passed, 23 skipped, 21 deselected, 1 xfailed.

The contract's r1 changes are marked `[r1]` in its text: §0 (board tools need no
cycle record id), §3 (kind normalization, `null` for optional fields), §8 (both
counts, zero included), §9 (types and `_ids` keys, the newest note is never cut).
