## Dispositions

- **22 — RESOLVED.** Revision 6 defines per-run lifecycles, recognizes recovery’s top-level `recovered_from_run_id`, and excludes superseded runs from `running_at_cutoff` ([design.md:469](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:469)).
- **24 — RESOLVED.** `PreparedInputs` retains every path input, and every later send on every path must be rebuilt and passed through `_count_and_bound` immediately before `_post_chat` ([design.md:316](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:316)).
- **31 — RESOLVED.** The supersession rule now reads the top-level recovery marker written by `recover_orphaned_running`, while retaining nested-marker compatibility ([design.md:474](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:474)).
- **34 — RESOLVED.** The expanded preparation contract carries the complete continuation inputs and explicitly routes all subsequent path sends through rebuilding and exact recounting ([design.md:316](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:316)).
- **35 — RESOLVED.** Revision 6 requires recounting after every later payload mutation, including both tool-set changes and the single-tool malformed-argument feedback mutation ([design.md:337](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:337)).
- **36 — RESOLVED.** The design now reads top-level `recovered_from_run_id`, matching exactly what `recover_orphaned_running` writes ([design.md:476](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:476), [heartbeat.py:133](/home/tony/projects/hamutay/src/hamutay/heartbeat.py:133)).
- **37 — RESOLVED.** Revision 6 expressly requires the single-tool malformed-argument resend to be rebuilt and recounted, covering `_call_single_tool`’s current message mutation and loop-back ([design.md:337](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:337), [taste_open.py:1427](/home/tony/projects/hamutay/src/hamutay/taste_open.py:1427)).
- **38 — RESOLVED.** Candidate mode is now unambiguous: it suppresses only `ExhaustedBeforeRequest`, while an unavailable count raises `CountUnavailable` immediately ([design.md:327](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:327)).
- **39 — RESOLVED.** Commit `b7ab196` contains the substantive design revision, whose header identifies revision 6 and whose normative sections contain the three promised corrections ([design.md:3](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:3)).

## Blocking

None.

## Significant

None.

## Minor

None.

## Verdict

Yes. Revision 6 is safe to implement as written.

1. Count the exact final payload before every send, including malformed-response resends, and assert `prompt_tokens + max_tokens < limit`.
2. Fail closed with `CountUnavailable`; candidate mode may suppress only `ExhaustedBeforeRequest`.
3. After any tool or message mutation, rebuild first, then recount, bound, assert, and send.
4. Preserve byte-identical legacy behavior when no tokenizer-backed policy exists, except for the declared truncation-record migration.
5. Capture response accounting before raising `TruncatedReply` on all four OpenAI paths.
6. Read recovery supersession from the top-level marker while accepting the nested form for compatibility.
7. Keep compact retry bounded to one deliberate retry and preserve both attempts’ records.