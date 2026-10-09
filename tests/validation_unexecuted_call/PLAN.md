# Independent unexecuted-call validation

Contract: `docs/superpowers/specs/2026-10-08-unexecuted-tool-call-note-design.md`
at r5, including commits `0ce2361` (repair exceptions) and `cc623fd`
(overflow grammar) since `8ddf47e`. Only this directory is authored; no
implementation or commits. No further `src/` inspection.

| Spec test | Validation |
| --- | --- |
| 1 | Detector: empty think, standalone/prose, malformed/empty input, fenced example and honest note. |
| 2 | Runner and EventStore: optional fields, exact parameter-free shape, natural vs non-natural. |
| 3 | Rule (d): repeat until clean completion; preserve (a)–(c), append (d) last. |
| 4 | Viewer: names on wakes/last_wake/replies; execute actual page JavaScript for both marks. |
| 5 | Exact cause clause from the completed row alone; disregard earlier activity, repair and mismatch. |
| 6 | Old completed rows with XML but no field produce no notes or viewer marks. |
| 7 | Real OpenTasteSession/backend loop, scripted chat transport: full/perception withdrawal, previous-run evidence; successful/invalid repair, clean-before-repair, repair exception. Persist and rebuild notes from disk; inspect evidence before repair. |
| 8 | Interim XML with structured calls; complete/incomplete XML with length; real compact retry sharing event ID; repeated names retained. |
| 9 | Mixed leak/failure/completion sequences, post-completion failure in one run, invalid/missing dates, newest five in append order and overflow count. |
| 10 | Distinctive parameter sentinel absent from new fields, notes, card and API mark payload; unchanged in Tony's full reply. |

Use local fixtures and lazy imports of the missing detector so the whole suite
collects. Use the existing viewer Node helper unchanged. Run once after review:
`uv run pytest tests/validation_unexecuted_call -q`.

Interpretations: malformed XML means incomplete outer/function delimiters or a
missing function name; parameter grammar beyond that is unspecified. Multiple
names must use `calls to` and preserve names/order, but plural pronoun wording
is unspecified and not constrained. False/absent withdrawal evidence uses the
unknown-cause clause. Empty optional fields are omitted; a populated final_turn
whose two booleans are false is retained. A repair exception completes the wake
with the original reply and pre-repair pair; the session logs
`state_validation.status: repair_failed`, and rule (d) reports the leak.
Viewer marks are asserted by visible text, without imposing tags,
CSS classes, or Markdown backticks in the DOM.
Overflow uses `earlier wake ... is not listed` for one omitted wake and
`earlier wakes ... are not listed` for multiple omitted wakes.

## R5 revision plan

- [x] Revise all three test 7 repair-exception cases to assert completion,
  original reply, persisted pre-repair pair, rebuilt rule (d) note, no failed
  event row or rule (c) note, and session `repair_failed` data. Keep the
  accepted-request check on the natural request when the repair raises.
- [x] Correct test 9's overflow oracle for singular and plural (counts 6 and 8).
- [x] Use the same explicit receiving event for rule (c) and combined notes
  in the completed-then-failed test; cover both matching and different event
  IDs and check the existing same-event suffix accordingly.
- [x] Review the revisions, run the entire suite once, and record counts here.

## Single revision run (2026-10-09)

Command (use the existing environment, disable bytecode/pytest cache writes,
and avoid source excerpts in failure output):

```bash
PYTHONDONTWRITEBYTECODE=1 UV_CACHE_DIR=/tmp/hamutay-validation-uv-cache uv run --offline --no-sync pytest tests/validation_unexecuted_call -q -p no:cacheprovider --tb=line
```

Result: **77 collected; 3 passed, 74 failed, 0 skipped, 0 collection errors**
in 1.29 seconds, exit status 1. This checkout lacks the detector module,
natural-final-turn attribute, completion fields/keywords, rule (d) builder and
limit, and viewer projections/marks. The same-event suffix checks passed for
both receiving-event variants before the combined-note assertion failed on
the missing rule (d) note. The full/perception repair-exception cases completed
before failing on the missing persisted `final_turn`; the stale case stopped
at the previous exchange's missing evidence attribute. No rerun or
implementation edits were made.
