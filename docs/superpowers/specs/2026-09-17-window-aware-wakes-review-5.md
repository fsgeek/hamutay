## Dispositions

- **9 — RESOLVED.** Revision 5 adds recovered-orphan close coverage, failed-without-retry persistence, admission ordering, and no-tokenizer compatibility tests ([design.md:581](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:581)).
- **14 — RESOLVED.** Admission now occurs through backend-owned `prepare(model, ...)`, after the session has assembled the wake, and reuses the resulting exact payload ([design.md:306](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:306)).
- **20 — RESOLVED.** The deterministic suite now covers the central invariants, while the model-dependent grammar and forced-sequence experiments are explicitly observational rather than gating ([design.md:620](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:620)).
- **22 — PARTIAL.** The per-run lifecycle and supersession rule are correct in principle, but the revision looks for `detail.recovered_from_run_id` although recovery writes `recovered_from_run_id` at the row’s top level ([design.md:463](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:463)).
- **23 — RESOLVED.** Revision 5 retains typed failures and a locked two-row write while explicitly accepting the non-atomic crash outcomes instead of claiming they cannot occur ([design.md:429](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:429)).
- **24 — PARTIAL.** `PreparedInputs` now retains the model, tools, executor, terminal surface, and policy, but the recount wording covers “later payload[s] of a multi-turn path” without explicitly covering `_call_single_tool`’s malformed-response retry ([design.md:315](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:315)).
- **29 — RESOLVED.** Acceptance is honestly limited to two terminalised window-failure attempts, excluding at-least-once orphan re-executions and allowing terminal failure ([design.md:491](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:491)).
- **31 — PARTIAL.** Superseded runs are excluded from `running_at_cutoff`, but the specified nested marker does not match recovery’s existing top-level marker ([heartbeat.py:133](/home/tony/projects/hamutay/src/hamutay/heartbeat.py:133)).
- **32 — RESOLVED.** The revision now requires one buffered write with flush, fsync, and verified growth while expressly declaring the residual partial-write and torn-tail behavior ([design.md:440](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:440)).
- **33 — RESOLVED.** Section 3 is now gated by `policy.window_aware`, requiring both limit and tokenizer and preserving no-tokenizer rendering ([design.md:365](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:365)).
- **34 — PARTIAL.** The expanded `Prepared` contract supplies the missing model and continuation inputs, but does not explicitly route the single-tool malformed retry through `_count_and_bound` ([design.md:316](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:316)).
- **35 — PARTIAL.** Candidate admission and tool-change rebuild ordering are specified, but the recount rule’s “multi-turn path” wording leaves the current single-tool retry loop uncovered ([design.md:326](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:326)).

## Blocking

36. **Recovery and close disagree on the marker’s schema**

`recover_orphaned_running` already writes `recovered_from_run_id` at the top level of the pending row ([heartbeat.py:129](/home/tony/projects/hamutay/src/hamutay/heartbeat.py:129)), while revision 5 requires `_runs_by_event` to inspect `detail.recovered_from_run_id` ([design.md:470](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:470)); implemented literally, recovered orphan runs remain unsuperseded and can still produce the false `running_at_cutoff` cap.

Minimal change: specify that close reads the existing top-level `recovered_from_run_id`—optionally accepting the nested form for compatibility—and make the close test use an actual row returned by `recover_orphaned_running`.

## Significant

37. **The single-tool malformed retry is not explicitly recounted**

`_call_single_tool` mutates `payload["messages"]` and sends again after malformed arguments ([taste_open.py:1442](/home/tony/projects/hamutay/src/hamutay/taste_open.py:1442)), but revision 5 expressly routes only “later payload[s] of a multi-turn path” through `_count_and_bound`; state that every resend, including this malformed retry, is rebuilt, recounted, bounded, and tested before `_post_chat`.

38. **`candidate=True` has contradictory count-failure semantics**

The interface says candidate preparation “never raises” and returns an integer `prompt_tokens`, while the fail-closed test requires a tokenizer failure to raise `CountUnavailable` ([design.md:318](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:318), [design.md:544](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:544)); clarify that `candidate=True` suppresses only `ExhaustedBeforeRequest`, while count failures always raise immediately.

## Minor

No new minor findings.

## Verdict

No. Revision 5 is **not safe to implement as written**.

1. Align orphan supersession with the existing top-level `recovered_from_run_id` marker and test close using recovery-produced records.
2. Require `_count_and_bound` before `_call_single_tool`’s malformed-response resend, not only the named multi-turn paths.