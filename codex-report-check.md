# Codex check of the Task 8 terminal validation report

Date: 2026-08-28

## Decision

**Do not commit the report as written. It may be committed after the specific
corrections below are made.**

The terminal status `blocked` is correct. The report also gets the central
independence failure and the absence of Task 9 evidence right. It is not yet an
accurate or complete Task 8 terminal artifact, however. It contains a wrong
four-bit measurement, mixes test-function counts with collected-case counts,
attributes verification to Codex that Codex did not perform, overstates several
corrections, omits one entire methodological finding, and states insufficiently
precise conditions for passing the later gates.

## Required corrections

### 1. Correct and label the test-provenance counts

The top-line collected-case arithmetic is correct:

- frozen: 186 collected cases;
- one frozen collected case removed: the loose four-bit diagnostic;
- eight post-access collected cases added: six in
  `test_artifact_contract.py`, one in `test_qualification_gates.py`, and the
  new four-bit parameter instance in `test_product_algorithm.py`; and
- current: 193 collected cases.

Thus `186 - 1 + 8 = 193` is correct. This is also consistent with the earlier
finding that seven currently present *test functions* were added after access:
the eighth added collected case is a new parameter instance of an existing
function.

The report's per-file numbers at lines 64-67 are not collected-case counts.
They are test-function counts and sum to 153 frozen and 159 current. In the
context of a table headed by `186 collected` and `193 collected`, leaving them
unlabeled is misleading. The actual pytest-collected per-file counts are:

| File | Frozen | Current |
|---|---:|---:|
| `test_conventions.py` | 18 | 18 |
| `test_codebook_math.py` | 39 | 39 |
| `test_mse_algorithm.py` | 21 | 21 |
| `test_product_algorithm.py` | 32 | 32 |
| `test_qualification_gates.py` | 31 | 32 |
| `test_artifact_contract.py` | 30 | 36 |
| `test_author_contract.py` | 15 | 15 |
| **Total** | **186** | **193** |

Replace the reported per-file line with this table, or explicitly label the
existing numbers as function counts and add the collected-case table.

The row `of which invalid as written | 3` must also be narrowed. Three is the
number of cases that **failed the first frozen-suite replay**, not the total
number of defective frozen cases. F2 was a vacuous frozen test; F4 was an
invalidly weakened frozen gate; F5 invalidated independent provenance for at
least the known copied cases; and F9 records further frozen assertion defects.
Calling only three cases invalid makes the suite's failure history look much
smaller than the report itself establishes. Use `failed on first replay | 3`
and refer separately to F2, F4, F5, and F9.

I independently collected both trees under Python 3.14 from isolated temporary
clones. The totals were exactly 186 and 193.

### 2. Correct the four-bit table and the attribution to Codex

The target is correct: `0.047 / 128 = 0.0003671875`.

The 20,000- and 100,000-pair rows reproduce with the frozen/current test's seed
and procedure:

| pairs | observed | relative error |
|---:|---:|---:|
| 20,000 | 0.0004136921 | 12.6651% (12.7%) |
| 100,000 | 0.0004119568 | 12.1925% (12.2%) |

The 200,000-pair row does not. Repeating the same deterministic procedure with
seed 34 gives:

| pairs | observed | relative error |
|---:|---:|
| 200,000 | **0.0004169594** | **13.5549% (13.6%)** |

The draft's `0.0004146673` and `12.9%` are wrong for that procedure. The
correct value still passes the 15% gate, so the scientific disposition does
not change.

The sentence `All inside the registered band. Independently reproduced by
Codex.` is also false as written. `codex-review-findings.md` records Codex
reproduction only of the 20,000- and 100,000-pair values. It contains no
200,000-pair reproduction. State exactly which values the earlier Codex review
reproduced; if the corrected 200,000 result is retained, attribute it to this
report check or reproduce and record it separately without rewriting the
history of the earlier review.

### 3. Add the complete commands and outcomes required by Task 8

Task 8 Step 5 requires the report to include `complete commands and outcomes`.
The draft provides only prose summaries. Add the exact commands, execution
environment, and outcomes for at least:

- the implementer suite used to freeze the implementation;
- the original frozen independent-suite run, including the three failures and
  complete preserved failing output;
- every corrected-suite rerun relevant to a disposition; and
- the current implementer and independent-suite GPU runs with the pinned clean
  author checkout and no unexpected skip.

If complete original output was not retained, say that explicitly as another
recordkeeping defect. Do not describe summaries as satisfying the plan's
`complete commands and outcomes` requirement.

For comparison, my isolated replays produced:

- current independent suite: `192 passed, 1 skipped` in the no-GPU sandbox;
- frozen `86b896b` suite: `182 passed, 3 failed, 1 skipped`, with exactly the
  three failures named in F1; and
- current implementer suite collection in this environment: 171 collected,
  with the CUDA module unavailable at collection time. This is consistent with
  the earlier Codex account of 169 passes, two CUDA-preflight failures, and one
  CUDA module skip, and does not independently verify the author's GPU-host
  claim of 182 passes.

### 4. Correct the `what was verified` section

The section is accurate about the central sandbox limitation: Codex could not
see a GPU, did not run the CUDA author differential, and therefore did not
independently reproduce the 182-pass implementer run. Keep that limitation.

Make these additional corrections:

- Distinguish **author-reported GPU results** from independently preserved or
  reproduced evidence. In the absence of complete retained output, `verified
  by the validation author` is testimony by the author, not independent
  verification.
- Do not say Codex reproduced all `four-bit Monte Carlo values`; the committed
  findings reproduce only 20,000 and 100,000 pairs.
- `all four validation commits` is stale and ambiguous. The table now contains
  five validation-history commits: `86b896b`, `4848272`, `910ae79`, `3f899f5`,
  and `a3ba5aa`. The earlier Codex review verified signatures and stamp commits
  for the first four. This check also verified that `a3ba5aa` has a good
  signature from primary fingerprint
  `01193FA2631C8AE8E4DF266E216D3C9B920813A1` and is followed by stamp commit
  `0db1996f0472d7af540d085c7595f7ceb81559fd`.
- Qualify `the absence of any Task 8 or Task 9 artifact in HEAD` as a historical
  observation about the pre-report `HEAD`. Once this report is committed,
  `HEAD` will contain a Task 8 artifact, making the present-tense wording false.

The hashes in the implementation table are correct. I also verified the full
history: implementation `b9227ce4b94374fc26167fc1357e0e9cc145af66`
is followed by stamp commit
`e8de8bfa68656decc798bd9291b9c4adb1603e39`; the five validation-history
commits are signed by the same project key and each is followed by its own OTS
stamp commit. As the report correctly says elsewhere, this does not authenticate
the model identity or establish external Bitcoin anchoring.

### 5. Restore findings that were softened, overstated, or omitted

F5 is softened by lines 163-166. The record cannot both say that pre-freeze
exposure `cannot be bounded` and then certify that all mathematical tests `are
unaffected` and that the defect is `concentrated` in gate/CLI tests. The two
direct overlaps establish a minimum, not a maximum. Replace that claim with:
the known direct overlaps are in gate/CLI tests; the numerical oracles pass and
are consistent with the paper; but missing prompt/material records prevent an
independent provenance claim for the remainder of the suite.

The severity labels should preserve the earlier review rather than overwrite
them. `codex-review-findings.md` called F5 the most important **undisclosed
independence defect**. If F4 is called the most serious technical test defect,
say that; do not unqualifiedly call the correctable F4 the most serious finding
in the whole record while demoting the uncorrectable chain-of-custody failure.

F7 is also overstated in the author's favor. The evidence supports `no
TurboQuant implementation detail was identified in the supplied CLAUDE.md`,
not `it cannot have shaped an assertion`. Keep the earlier severity: less
material than F5, but a formal protocol deviation that independently prevents
a clean-envelope claim. Its PI disposition is still pending and must be listed
as an unresolved disposition/unblocking item.

F3 and F9 are not fully corrected. The current `TestTerminalEvidence` imports
and calls `main()` in-process. It does not execute the installed
`turboquant-qualify` console command or a fresh interpreter despite claiming
to exercise the public console entry point. It also still writes into the real
evidence namespace and relies on `finally` cleanup, so abrupt process death can
leave residue. The exit-code, `OWNDATA`, codebook, and worker-input assertions
were corrected, but these two lower-severity harness issues remain open. Record
them rather than giving F9 the blanket disposition `corrected`.

The earlier review's finding about the proposed `second arm` is missing as a
finding/disposition. Add it explicitly: a clean cross-family rerun is
remediation plus prospective replication, not a post-hoc controlled arm and
not evidence that weight decorrelation is a necessary condition for
independence. The old and new runs would differ simultaneously in model,
prompt hygiene, materials, recordkeeping, and instructions, with one session
per condition. Condition 4 gestures at this but does not record the finding or
its reasoning.

### 6. Strengthen the unblocking conditions

`Blocked` is the only correct terminal status. F5/F6 break the Task 8 chain of
custody; F8 leaves a mandatory gate without independent coverage; F7 lacks a PI
disposition; and Task 9 has not occurred.

The draft's conditions are necessary but not sufficient. Amend them so a later
reader cannot infer passage from a mere rerun:

1. Require the clean validator to freeze its suite in a **separately signed and
   timestamped commit before any implementation access**, with the exact clean
   prompt, session/model record, supplied-file hashes, implementation hash, and
   complete freeze/run output retained.
2. Require the genuinely frozen new suite—not only a post-access patch to the
   compromised old suite—to cover the public terminal behavior of all five
   mandatory gates, including execution and successful observation of the
   author-code differential on the target CUDA environment. Post-access F8
   coverage in the old suite is corroborative only and cannot supply sealed
   independent coverage.
3. Resolve F7 with a written PI disposition. More generally, every rejected or
   waived finding needs the written technical disposition and PI approval
   required by the specification.
4. Replace ambiguous `rerun both suites` with exact suite names. At minimum,
   the implementer suite and the new frozen independent suite must pass on the
   target GPU with the pinned clean author checkout and no unexpected skips.
   If the old suite is retained as corroboration, state separately whether it
   must also pass.
5. State that the replacement Task 8 report must itself contain the full
   commands/outcomes and say `passed` before Task 9 is permitted. A blocked or
   merely existing report is not enough.
6. Do not end with merely `execute Task 9`. Require the exact registered command
   in a clean worktree, one million registered pairs, three fresh-process
   execution records and matching hashes, independent inspection of all five
   gates and every artifact hash/value, complete implementer and independent
   test reruns with the author differential active, and a signed and timestamped
   R1 evidence/report commit. Only a passing Task 9 record authorizes writing
   the second model/cache-path plan; passing Task 8 alone does not.

The proposed use of a third model family is a defensible remediation control,
but it should not be presented as the variable that repairs this record. The
actual defects are the contaminated materials and missing chain-of-custody
records. The clean run remains remediation, not a retrospective experiment on
model-family independence.

### 7. Replace the inaccurate and self-serving `Note on method`

Lines 279-282 are factually wrong. F1 and F2 were not caught by pre-freeze
simulation against an independent reference:

- F1 survived into the frozen commit and was exposed only when the frozen suite
  ran against the implementation; the report itself says it was reported by
  the implementer.
- F2 was found by the validator while correcting F1 after implementation
  access.
- F7 was disclosed by the validator in the original freeze record, so it also
  contradicts the categorical claim that every substantive defect was found by
  a second position.

The pre-freeze simulation discussed in the README found two different proposed
assertions; it did not find F1 or F2. Calling all later detection `a second
position` turns ordinary failure exposure, implementation feedback, and
external review into a flattering methodological story. The defensible lesson
is narrower and less self-serving: repeated self-review did not prevent the
frozen failures, the invalid tolerance change, the materials misdescription,
or the vacuous assertions; implementation execution, correction work, the PI,
and external Codex review found different defects at different times. State
that chronology plainly.

## Bottom line

The report should remain `blocked`, and Task 9 must remain prohibited. The draft
is salvageable, but it should be committed only after all corrections above are
made. In particular, the numeric and provenance errors, the missing complete
commands/outcomes, the false verification attributions, the softened/open
findings, and the insufficient gate conditions are material defects in a
terminal validation record.
