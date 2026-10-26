# Board v0 independent validation plan

Date: 2026-10-15.

Goal: validate the observable board contract without importing private board APIs
or reading its implementation. Authority: `docs/superpowers/specs/2026-10-15-board-v0-contract.md`;
r2 design is background only. All fixtures live below pytest's temporary root;
no real community home, credential, model, or service is used. No commits.

Architecture: CLI subprocesses exercise human writes/reads; the documented
`run_board_tool` and `run_board_pass` exercise door operations; real EventStore,
`run_next_event`, summary, and heartbeat exercise delivery. A session double
records JSON envelopes and returns a synthetic result, or raises deliberately.
Session tool/prompt tests intercept the public backend call before inference.
Pre-board constitution and complete dormant system-prompt SHA-256 values were
captured from this implementation-free worktree on 2026-10-15. The full prompt
replaces only the temporary project path with `<PROJECT_ROOT>` before hashing;
two independently rooted sessions produced identical bytes after substitution.
Fixture records are constructed independently from the contract, never using a
board builder, validator, reducer, renderer, matcher, or constants. No fallback,
skip, xfail, or fake board implementation masks a missing entry point.

Execution tasks:

- [x] Read the two authorized specifications and integration interfaces.
- [x] Create isolated fixtures and independent record/event constructors.
- [x] Write record/CLI, filters/tools, reconciliation, and wake integration tests.
- [x] Audit clause coverage and ambiguity decisions below.
- [x] Run `uv run pytest tests/validation_board -q`; record exact results.

## Contract coverage

The test names below are in the indicated module; parametrized cases include
valid endpoints, overflows, malformed types, and negative controls.

| Clause | Tests |
|---|---|
| §0 documented CLI, tools, pass, EventStore | All modules; no private board interfaces |
| §1 file paths, lock, ignore rules | `test_records::test_paths_and_gitignore`, `test_cli_concurrent_writers` |
| §2 absent gate no writes / cached gate invalidation | `test_filters::test_dormant_pass_and_tool_gate`, `test_gate_checked_each_call` |
| §2 tools and prompt offered exactly with send_message prerequisites | `test_offering` gate/prerequisite matrix and prompt restoration tests |
| §2 pending parked; summary, claim, restore | `test_wakes::test_parked_events_and_unparking` |
| §2 CLI works dormant, note in JSON | `test_records::test_cli_dormant_and_overview` |
| §3 exact field sets, physical seq, UUID4, timestamps | `test_records::test_record_shapes`, strict corruption matrix |
| §3 field limits, kinds, canonical labels/tags | `test_records` writer boundaries and strict corruption matrices |
| §3 opening uniqueness, follow opening, owner-only, closed final | `test_records::test_owner_and_closed_final`, strict structural matrix |
| §3 strict whole-file reader; writer/pass no side effects on error | `test_records::test_corruption_fails_closed_everywhere` |
| §3 tolerated unterminated final line; next append overwrites | `test_records::test_torn_final_line_repaired` |
| §3 writer normalization/default owner | `test_records::test_writer_normalization` |
| §3 20/day, all types together, UTC, duplicates free | `test_records::test_daily_record_cap_and_duplicates`, `test_utc_record_cap` |
| §3 5 currently open per poster / reopening / taken frees slot | `test_records::test_five_open_cap_and_reopen`, `test_cap_belongs_to_poster` |
| §3 dedup openings/notes/latest status; first open status writes | `test_records::test_dedup_and_first_open_status`, `test_closed_opening_can_be_reposted` |
| §3 admitted guests only | `test_records::test_guest_admission` |
| §4 CLI grammar, errors, JSON, door refusal, defaults, read id/all/since/50 | `test_records` CLI/read tests; `test_filters::test_board_read_closed_and_since_projection` |
| §5 storage, generations 0→1→2→3, clear null, per-door | `test_filters::test_generation_storage_and_isolation` |
| §5 NFKC/casefold/trim, dedup first order, four keys | `test_filters::test_filter_normalization` |
| §5 blanks/types/unknowns/16 limit/kinds/tags/owners/keywords | `test_filters::test_invalid_filter_is_atomic`, `test_filter_limits_accept_endpoints` |
| §5 AND between, OR within, no constraint empty, empty matches none, substring | `test_filters::test_matching_truth_table`, `test_empty_filter_matches_nothing` |
| §5 immediate queue / scan_error and persisted valid filter | `test_filters::test_set_scans_immediately`, `test_set_scan_error_keeps_filter` |
| §6 event fields, exact id formula, distinct plaza namespace | `test_reconciliation::test_event_shape_and_ids` |
| §6 open current status only, self never matches, unseen only | `test_reconciliation::test_openings_eligibility`, wake coverage tests |
| §6 subscriptions / first-shown snapshot boundary / foreign updates / close | `test_wakes::test_subscription_snapshot_and_updates`, `test_self_updates_are_excluded` |
| §6 supersession on generation, clear, pass | `test_reconciliation::test_generation_rescan_and_supersession`, `test_clear_supersedes`, `test_pass_supersedes_updates` |
| §6 repair failed lineages / attempt 3 abandoned | `test_reconciliation::test_repair_missing_successor` |
| §6 no filter only onboarding/supersession | `test_reconciliation::test_no_filter_no_matches` |
| §6 32 append bound, continuation, idempotence, memo invalidation | `test_reconciliation::test_bounded_pass_continues`, `test_reconcile_idempotent_and_memo_invalidates` |
| §6 board/store unreadable error writes nothing | corruption tests; `test_reconciliation::test_bad_event_store_is_atomic` |
| §6 heartbeat every step after plaza | `test_wakes::test_heartbeat_reconciles_after_plaza` |
| §7 parked/superseded/held/deferred distinctions | wake parking, supersession, daily cap, and quiet tests |
| §7 2 distinct running run_ids / UTC / retries / crashes / onboarding excluded | `test_wakes::test_daily_cap_counts_batches_and_resets`, `test_retries_and_crashes_count_attempts`, `test_onboarding_does_not_use_daily_cap` |
| §7 held summary waiting at next UTC midnight, no spinning | `test_wakes::test_held_summary_and_heartbeat_sleep` |
| §7 oldest created_at, board batch, shared run/time/snapshot, non-board separate | `test_wakes::test_coalesced_completion`, `test_non_board_ordering_and_separation` |
| §7 superseding at claim moves on to other events | `test_wakes::test_claim_supersedes_and_reaches_other_event` |
| §7 only rendered entries claimed | `test_wakes::test_envelope_bounds_and_uncovered_remainder` |
| §8 completion shared cycle/result, primary last/response once | `test_wakes::test_coalesced_completion` |
| §8 coverage completed only, title-only counts | `test_wakes::test_only_completion_confers_coverage`, envelope bounds test |
| §8 failure all rows, successor ids/metadata, attempt 3 abandoned, new gen | `test_wakes::test_failure_retry_and_abandonment` |
| §8 failed batch operational note once/run with retry/terminal counts | `test_wakes::test_failed_batch_surfaced_once` |
| §8 boot recovery same id/attempt | `test_wakes::test_crash_recovery_preserves_lineage` |
| §9 JSON envelope, current entry, full fields, clause/retry/update reasons | `test_wakes::test_full_envelope_current_state`, `test_retry_and_update_explanations` |
| §9 10 full/20 titles/12000 chars/6000 entry/notes omission/at least one | envelope bounds and long-entry tests |
| §9 unique entry for many events, coverage and remainder counts | `test_wakes::test_multiple_updates_render_entry_once`, envelope bounds test |
| §9 corrupt board at claim still wakes with error/id/seq | `test_wakes::test_corrupt_board_still_claims` |
| §10 input identity/store cannot spoof, read response, refusal prefix and no writes | `test_filters::test_tool_identity_and_store_are_bound`, record refusals |
| §10 board_pass idempotent; read does not confer coverage | `test_reconciliation::test_pass_supersedes_updates`, `test_wakes::test_read_does_not_confer_coverage` |
| §10 writes survive failed wake | `test_wakes::test_write_during_failed_wake_stands` |
| §11 notice once/door ever; deterministic id, fields, ≤20 list/count, choice/tools/limits | `test_reconciliation::test_onboarding_once_per_door`, `test_onboarding_content_and_limit` |
| §12 claimed labels, no editable coverage, board_text-only bound | no authentication assertion; tool spoof/refusal and envelope tests |

## Ambiguities and chosen readings

1. “All three paths” in §3 names only CLI and door tool; r2 mentions guest MCP.
   Test CLI guests and door tools only. No unspecified MCP entry point is invented.
2. §5 removes normalized duplicates; §3 on-disk tags must already be unique.
   Writer tag duplicates normalize to one tag; supplied >8 tags is tested with
   distinct values. Filter >16 is rejected *before* deduplication.
3. `since_seq` inclusion is unspecified. Choose inclusive (the plaza convention);
   an entry qualifies if any of its opening/note/status records is at/after N.
4. `posted_at` is named but not explicitly typed. Choose a timezone-bearing ISO
   instant, like `created_at`. Corrected 2026-10-16: §3 defines any unterminated
   final line as torn, even complete valid JSON. Readers ignore it and the next
   append overwrites it; malformed JSON terminated with newline is refused.
5. No oldest/newest order is promised for full/title allocation, nor exact full
   count under character pressure. Assert ceilings, accounting, nonempty progress,
   and rendered-id/pending correspondence, not a particular selection algorithm.
6. “6,000 characters per full entry” has no machine-readable span marker. As
   clarified by r1, opening fields, the explanation and the newest note are never
   cut; older notes fill the 6,000-character budget. The long-entry test checks
   these protected fields and the exact global 12,000 bound. A strict per-entry
   span assertion awaits a rendering delimiter contract.
7. Dedup versus closed-final: closing an entry wins; repeating its final status or
   note is refused. Dedup versus daily/open caps: an otherwise valid repeat is
   returned even at the caps. Duplicate status compares only the *latest status*.
8. A shown entry's subscription survives nonempty filter changes and a taken
   status; clearing the filter stops all board wakes. `board_pass` suppresses
   updates; it does not erase completed coverage. An unrelated door's pass has
   no effect. Self-written notes/status never queue, including on foreign posts.
9. At claim, a queued opening that has since closed is rendered as closed, per
   r2 and §9 current-state requirement; it is not silently discarded. Onboarding
   is excluded from board batches and board-triggered attempt accounting.
10. Pass `appended` counts every newly appended store record (including notice,
    suppression, abandonment), with a strict total ≤32. An enabled unchanged
    no-op may return either documented no-op shape; dormant shape is exact.
11. Failure note prose and summary per-event listing are not prescribed. Assert
    board failure notes once/run and numeric retry/terminal facts via text, and
    next-midnight `not_before` in the public summary, without fixed prose.
12. Unknown identity keys supplied to board tools may be refused or ignored, but
    may never select another actor/store/root. Unknown coverage-edit tools must
    be refused. Error wording is otherwise unconstrained beyond required prefix.
13. Onboarding text must state the specified numeric limits and opt-in choice;
    its exact wording is unspecified. CLI overview text likewise has no fixed
    prose. No assertion about an implementation header absent from the contract.

14. Resolved by r1: `entries_full`, `entries_titles`, `remaining_entries`,
    `remaining_events`, and `coverage_after_this_wake` are integer counts;
    `generation` and `snapshot_seq` are integers too. `entries_full_ids` and
    `entries_titles_ids` list opportunity ids in rendering order;
    `batch_event_ids` is a list of event ids.
15. Runtime gate checking is explicit for an exchange's offered tools. The session
    test changes the gate between exchanges of an existing session and expects
    both prompt and offerings to change, then restore exactly. This rules out a
    launch-only cached constitution clause.

Additional cross-checks: `test_daily_attempt_date_is_utc`,
`test_daily_board_cap_is_per_door`, `test_envelope_groups_all_events_of_rendered_entry`,
`test_failed_wake_does_not_subscribe`, `test_update_arriving_during_wake_is_not_lost`,
`test_nonowner_cli_refusals_are_atomic`, `test_writer_refuses_unknown_opportunity`,
`test_dedup_is_scoped_to_poster`, `test_duplicates_do_not_use_open_cap`, and
`test_bounded_pass_counts_supersession_and_repair`,
`test_cli_and_door_writers_share_lock`, `test_cli_label_normalization`,
`test_limits_count_characters_not_bytes`,
`test_full_dormant_system_prompt_is_preboard_baseline`, and
`test_enabled_executor_dispatches_bound_writer` strengthen the clauses above.

## Review and execution evidence

Final run on 2026-10-15:

```text
uv run pytest tests/validation_board -q
250 failed, 8 passed in 12.96s
```

258 test cases; exit status 1; zero collection errors, zero skips and zero xfails.
The failures are missing `hamutay.board` imports/CLI module, the absent
`ToolExecutor(board=...)` interface, and board-specific behavioral assertions
against the existing event/session/heartbeat paths. Existing `run_next_event`
tries its reflection context resolver for a board event and raises
`ValueError: requested_context must be a non-empty list`; this is an expected
missing dedicated board-envelope behavior, not a mocked resolver.
The eight passing cases are dormant/precondition negative controls and frozen
pre-board prompt checks. No NameError, AttributeError, SyntaxError, or
UnboundLocalError appeared in the final run.

Environment for the command: `UV_CACHE_DIR=/tmp/hamutay-board-validation-uv`,
`UV_PROJECT_ENVIRONMENT=/home/tony/projects/hamutay/.venv`, `UV_NO_SYNC=1`,
`PYTHONPATH=<this-worktree>/src`, and `PYTHONDONTWRITEBYTECODE=1`. This uses the
already installed dependencies, avoids the read-only default uv cache and
network dependency synchronization, and overrides the shared environment's
editable install of the main checkout. Verified `hamutay.__file__` resolves into
this worktree. The initial uv-created local environment was removed.

Self-review checked all plan test references and parsed every test module.
No board implementation was read or supplied; no residents' homes were read;
no commits were made. All authored files are under `tests/validation_board/`.
The suite intentionally stays red on main without board v0; that does not
establish how it will perform against the unseen implementation. The per-full-entry
6,000-character span remains only indirectly tested (ambiguity 6); the global
12,000-character limit and claim/coverage accounting are asserted exactly.

## 2026-10-16: r1 review and revision plan

Reviewed the complete r1 contract and all 18 dispositions before editing tests.
No decision warrants stopping on the merits. The 11 class-C cases are disposition
#2 (no cycle record id), #3 (kind normalization), #4–5 (optional nulls),
#8–12 and #15 (envelope counts), and #13 (newest note). These are eleven failing
cases covering five clarifications, not eleven independent policy changes.
The class-B newline decision also follows §3's explicit definition of torn.
The six class-A fixes remain implementation obligations; their assertions stay.

Only this directory may change; no implementation inspection and no commits.

- [x] Review dispositions and contract r1 before any test edits.
- [x] Update `test_records.py`: replace the complete-JSON-tail preservation
  expectation with ignore/overwrite/retry assertions, with and without committed
  preceding records (§3: newline is the commit boundary).
- [x] Update `test_records.py`: accept null for every optional opening field and
  status reason, assert canonical persisted defaults and deduplication against
  omission; retain required-null and other non-string refusal coverage (§3 r1).
- [x] Extend CLI kind normalization coverage to fullwidth Unicode and assert the
  persisted kind; retain door normalization and executor-without-cycle-id checks
  already aligned with §3 and §0 r1. Add a comment explaining the latter.
- [x] Update `test_wakes.py`: assert all declared integer/list types, new `_ids`
  keys, list/count agreement, rendering order and correspondence to claimed
  events (§9 r1). Keep existing coverage and pending-remainder assertions.
- [x] Update the long-entry test to preserve complete opening fields and the
  complete newest note, trim only older notes, and enforce the global 12,000
  bound; remove the old indirect 7,000 bound that could cut protected text
  (§9 r1). Update ambiguity 6 accordingly.
- [x] Require numeric zero in the failed-batch note, rather than accepting
  "zero" or "none", alongside the retry and terminal facts (§8 clarification).
- [x] Correct the superseded ambiguity readings 4 and 14 in this plan.
- [x] Run `uv run pytest tests/validation_board -q` and record observed counts,
  exit status and environment here; missing board implementation is expected.

Observed run on 2026-10-16 (counts read from the command output):

```text
uv run pytest tests/validation_board -q
265 failed, 8 passed in 13.84s
```

273 cases; exit status 1; zero collection errors, skips or xfails. The suite grew
by 15 cases: seven optional-null acceptance cases, five additional opening-field
refusals, one required-null status refusal, a second complete-JSON-tail case,
and a second CLI normalization case. The two former optional-null refusal cases
now exercise non-null invalid types.

The environment is the same as the 2026-10-15 run documented above:
`UV_CACHE_DIR=/tmp/hamutay-board-validation-uv`,
`UV_PROJECT_ENVIRONMENT=/home/tony/projects/hamutay/.venv`, `UV_NO_SYNC=1`,
`PYTHONPATH=<this-worktree>/src`, `PYTHONDONTWRITEBYTECODE=1`.
Full output: `/tmp/hamutay-board-v0-r1-validation.txt`.

All Python test files parse. Failure output contains no NameError,
AttributeError, SyntaxError or UnboundLocalError. Expected missing-board failures
remain: `hamutay.board` imports/CLI, the absent `ToolExecutor(board=...)`
interface, and existing event/session/heartbeat behavior without board support
(including the reflection resolver's `requested_context` refusal). This run
cannot establish whether the revised tests pass against the unseen build.
Only `test_records.py`, `test_wakes.py`, `test_offering.py` and this plan were
edited. No board implementation was read and no commits were made.
