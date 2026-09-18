## Dispositions

- **22 — PARTIAL.** The per-run lifecycle remains specified, but supersession still reads nested `detail.recovered_from_run_id` ([design.md:463](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:463)).
- **24 — PARTIAL.** `PreparedInputs` retains the continuation inputs, but recounting still applies only to later payloads of a “multi-turn path,” excluding the single-tool malformed retry ([design.md:320](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:320)).
- **31 — PARTIAL.** Superseded runs are excluded from `running_at_cutoff`, but recovery writes `recovered_from_run_id` at the row’s top level while the design reads it from `detail` ([design.md:470](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:470), [heartbeat.py:133](/home/tony/projects/hamutay/src/hamutay/heartbeat.py:133)).
- **34 — PARTIAL.** The expanded `Prepared` contract remains sufficient for continuation state, but it still does not route every path’s resend through `_count_and_bound` ([design.md:334](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:334)).
- **35 — PARTIAL.** Tool-set changes are explicitly rebuilt and recounted, but the rule still does not cover message-only mutations such as malformed-response feedback ([design.md:339](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:339)).
- **36 — NOT RESOLVED.** The design still expects `detail.recovered_from_run_id`, whereas `recover_orphaned_running` writes top-level `recovered_from_run_id` ([design.md:471](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:471), [heartbeat.py:133](/home/tony/projects/hamutay/src/hamutay/heartbeat.py:133)).
- **37 — NOT RESOLVED.** The design still limits later recounting to multi-turn paths, while `_call_single_tool` mutates `payload["messages"]` and immediately loops back to `_post_chat` without recounting ([design.md:334](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:334), [taste_open.py:1442](/home/tony/projects/hamutay/src/hamutay/taste_open.py:1442)).
- **38 — NOT RESOLVED.** The design still says `candidate=True` “never raises,” contradicting its requirement that tokenizer failure raises `CountUnavailable` ([design.md:329](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:329), [design.md:544](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:544)).

## Blocking

39. **Commit 29489ed contains no revision-6 design**

The design blob is identical to its parent, still identifies itself as revision 5 ([design.md:3](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:3)), and commit 29489ed adds only the round-five review file; consequently none of the commit message’s three claimed corrections exists in the normative design.

## Significant

No new significant findings.

## Minor

No new minor findings.

## Verdict

No. Revision 6 is **not safe to implement as written**, because the repository contains the unchanged revision-5 design.

1. Commit the actual revision-6 design text.
2. Read recovery’s top-level `recovered_from_run_id` and test close with a row produced by `recover_orphaned_running`.
3. Require every resend on every path—including `_call_single_tool`’s malformed-response retry—to rebuild, recount, bound, and assert immediately before `_post_chat`.
4. State that `candidate=True` suppresses only `ExhaustedBeforeRequest`; tokenizer/count failures must still raise `CountUnavailable`.