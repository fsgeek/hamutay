## Dispositions

- **1 — RESOLVED.** Revision 4 limits the exact-count invariant to doors having both a limit and tokenizer and explicitly retains the legacy estimate-based behavior elsewhere ([design.md:94](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:94)).

- **2 — RESOLVED.** Budget fields are now restricted to `tool_choice == "none"`, while the reply reserve is explicitly a one-think target rather than a guarantee ([design.md:222](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:222)).

- **4 — RESOLVED.** The design no longer promises completion: its acceptance criterion permits terminal failure when resident-owned state alone cannot fit ([design.md:453](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:453)).

- **9 — PARTIAL.** The Testing section now covers exact boundaries, all four paths, retry, close, preparation, and policy replacement, but omits the orphan-per-run and torn two-line transition cases identified below ([design.md:486](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:486)).

- **12 — RESOLVED.** Exactness is now claimed only for tokenizer-backed policies; a ceiling without a tokenizer is expressly not window-aware ([design.md:94](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:94)).

- **14 — PARTIAL.** Payload construction has correctly moved behind backend-owned `prepare`/`call_prepared`, but the stated interface lacks the `model` needed to construct the actual OpenAI payload and does not fully specify continuation state ([design.md:305](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:305)).

- **16 — RESOLVED.** Each qualifying first failure now creates one compact pending retry, while failure of that compact run is explicitly terminal ([design.md:402](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:402)).

- **17 — RESOLVED.** The probe separately records request acceptance, template tags, and observed forcing, and an inconclusive result leaves budgeting disabled ([design.md:166](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:166)).

- **20 — PARTIAL.** The nondeterministic tool-grammar and forced-sequence experiments are properly downgraded to observational evidence, but the new recovery and admission gaps below still lack tests ([design.md:565](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:565)).

- **22 — PARTIAL.** Positions are now classified by `(event_id, run_id)`, but “`running_at_cutoff` is computed per run” does not account for orphaned runs that recovery deliberately leaves without a terminal row ([design.md:433](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:433)).

- **23 — PARTIAL.** Typed `WindowFailure` subclasses and the locked failed-plus-pending transition address normal execution, but one filesystem write is not crash-atomic and there is no recovery for a partial transition ([design.md:406](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:406)).

- **24 — PARTIAL.** The backend now owns exact payload preparation and the final envelope is recorded, but the proposed `Prepared` contract is insufficient as written for the four existing path implementations ([design.md:314](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:314)).

- **25 — RESOLVED.** The floor is checked against `min(self._max_tokens, room)`, including configured maxima below the minimum ([design.md:212](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:212)).

- **26 — RESOLVED.** Capability now requires accepted fields, template tags, and observed forcing rather than merely finding two visible tags in a response ([design.md:170](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:170)).

- **27 — RESOLVED.** The unsafe tool-grammar combination is excluded from the mechanism, and its live experiment is explicitly non-gating observational evidence ([design.md:222](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:222)).

- **28 — RESOLVED.** A limit without a tokenizer is excluded from the exact-count property and retains the 9-06 estimate/recovery path ([design.md:101](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:101)).

- **29 — PARTIAL.** Terminal failure is now honestly allowed, but “at most two attempts” and “every attempt recorded in full” remain false under the unchanged orphan-recovery behavior ([design.md:453](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:453)).

- **30 — RESOLVED.** Revision 4 declares single-thread ownership and records the policy `invocation_id`, while reserving locking for a future shared-session model ([design.md:624](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:624)).

## Blocking

31. **Attempt-aware `running_at_cutoff` will permanently resurrect recovered orphan runs**

`recover_orphaned_running` copies the latest pending record and appends a new pending row, but never terminalizes or supersedes the abandoned `run_id` ([heartbeat.py:111](/home/tony/projects/hamutay/src/hamutay/heartbeat.py:111)). Consequently, a close implementation that computes `running_at_cutoff` per run will continue seeing the old pre-cutoff run as running even after its recovered successor completes. That can delay closing and later apply a false `running_at_cutoff` cap.

Minimal change: define a per-run lifecycle index in which a pending row’s `recovered_from_run_id` marks that run as superseded, and exclude superseded runs from `running_at_cutoff`; add a test for running → boot recovery → replacement completion before close.

32. **The failed-plus-retry transition is not crash-atomic, and the stated acceptance criterion is therefore inconsistent**

A single buffered write containing two JSON lines can be partially persisted by power loss, I/O failure, or a short write; unlike the assembly ledger, `EventStore._append_unlocked` neither fsyncs nor verifies growth, and its reader does not tolerate a torn final line ([events.py:595](/home/tony/projects/hamutay/src/hamutay/events.py:595)). The revision’s statement that a crash between rows “cannot happen” is therefore too strong. Separately, an arbitrarily repeated crash of a compact run can produce arbitrarily many recovered `run_id`s, and each killed execution has only its `running` row—not a full attempt record. Thus “at most two attempts per event, every attempt recorded in full” is not compatible with unchanged orphan recovery.

Minimal change: either add a recoverable transaction format/torn-tail recovery for the two logical rows, or narrow the contract to “at most two terminalized window-failure attempts; orphan re-executions remain at-least-once and retain their running records.” The latter is the smaller change but must replace the current acceptance wording.

## Significant

33. **The no-tokenizer compatibility requirements contradict §3**

The property section says a ceiling without a tokenizer keeps the 9-06 behavior “exactly,” and test 3 requires its payloads to equal the 9-06 golden ([design.md:101](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:101), [design.md:502](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:502)). But §3 activates lean state, memory, and curator rendering whenever `policy.limit is not None`, including the no-tokenizer case, which changes both payload contents and the legacy estimate that controls tool withdrawal ([design.md:345](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md:345)).

Minimal change: gate §3 on the full window-aware predicate as well, or explicitly abandon golden payload equality and specify which 9-06 behaviors—not payloads—must remain. Given the stated compatibility requirement, the former is safer.

34. **`Prepared` does not contain enough information to implement the four paths as specified**

Every current OpenAI path receives `model`, while the proposed `prepare(system, messages, extra_tools, terminal_surface, policy)` does not; nevertheless the model is a required payload field ([taste_open.py:1336](/home/tony/projects/hamutay/src/hamutay/taste_open.py:1336)). `call_prepared` must also resume materially different state machines: malformed-call retries in `_call_single_tool`, tool execution in `_call_multi_turn`, withdrawal/recovery in `_call_natural`, and terminal parsing in `call_terminal_surface`. `Prepared(payload, prompt_tokens, path)` alone does not define which immutable inputs and mutable loop state are retained.

Minimal change: add `model` to `prepare` and define `Prepared` as the exact first payload plus path-specific continuation inputs, including the tool executor; state that only the first send is consumed verbatim and every subsequent payload is rebuilt and recounted through the same backend helper.

35. **Admission and turn-zero withdrawal need an explicit count–rebuild–recount sequence**

Admission may first count an envelope that leaves less than the generation floor but would fit after cap reduction. The revision does not say whether `prepare` returns that count for admission or raises `ExhaustedBeforeRequest` immediately. Likewise, turn-zero soft-threshold detection must remove tools, rebuild the payload, and recount before sending; otherwise the request sent is not the candidate that triggered withdrawal. Tests assert the desired endpoints but not this ordering.

Minimal change: specify that candidate preparation may return an unsendable count during admission; only the final candidate is floor-validated. For soft or near-wall transitions, require rebuilding and recounting after every tool-set change before the invariant is asserted and the request is sent.

## Minor

No new minor findings.

## Verdict

Revision 4 is **not safe to implement as written**.

Its normal, non-crash path is close: typed failures, the grammar-free budget gate, effective-`max_tokens` floor, exact tokenizer-backed invariant, compact retry, and attempt-bound position classification are coherent. The stopping blockers are narrower:

1. Treat recovered `run_id`s as superseded in the attempt-aware close pass.
2. Replace the false two-line crash-atomicity and “every attempt” claims with either recoverable storage mechanics or explicitly scoped terminal-attempt semantics.
3. Resolve the no-tokenizer §3/golden contradiction.
4. Complete the `Prepared` contract and specify count–rebuild–recount ordering.

The Testing section must then add recovered-orphan close coverage, partial transition recovery or the narrowed crash contract, oversized-first-admission-then-fit coverage, and no-tokenizer payload compatibility.