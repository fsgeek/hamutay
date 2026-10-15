# Second verification of the Task 8 terminal validation report

Date: 2026-08-28

## Decision

**Do not commit the report as-is.** The scientific recount, four-bit
recomputation, finding severities, unblocking conditions, and method note have
been repaired. Two recordkeeping/attribution corrections remain partial, and
the rewrite introduces a false claim that `codex-report-check.md` is committed.

## Verification of the seven required corrections

### 1. Test-provenance counts — APPLIED

The new distinction between collected cases and test functions is correct.
I collected both trees again, using the frozen test files from
`86b896b116f507ef4a71a815ab7c3822a5238d86` and the current tree. My independent
per-file counts were:

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

This exactly matches report lines 75-86. The apparent zero net change in
`test_product_algorithm.py` is also correct: the loose four-bit diagnostic was
removed and a fourth parameter instance was added to the existing strict test.
Together with six new artifact-contract cases and one qualification-gate case,
the arithmetic is `186 - 1 + 8 = 193`, as lines 58-67 state.

The misleading `invalid as written | 3` row is gone. Lines 59 and 69-73 now
correctly call three the number that failed on first replay and separately name
the non-failing frozen defects F2, F4, F5, and F9.

### 2. Four-bit table and reproduction attribution — APPLIED

The seeds are now explicit, and I recomputed all four rows from the actual
`ProductQuantizer` procedure. The target and results were:

| pairs | seed | observed | relative error |
|---:|---:|---:|---:|
| 20,000 | 34 | 0.0004136921 | 12.66507356% |
| 100,000 | 34 | 0.0004119568 | 12.19249531% |
| 200,000 | 34 | 0.0004169594 | 13.55490210% |
| 200,000 | 7 | 0.0004146673 | 12.93067178% |

The target is exactly `0.047 / 128 = 0.0003671875`. Thus report lines 144-151
are numerically correct and all four values are inside 15%. Lines 153-163 also
correctly explain the earlier silent seed change and distinguish the earlier
Codex reproduction of 20,000/100,000 pairs from the report check's reproduction
of the seed-34 200,000-pair value.

### 3. Commands and outcomes — PARTIAL

The requested section now exists at lines 295-333. It does three important
things correctly:

- explicitly admits that complete original output was not retained and calls
  that a recordkeeping defect (lines 297-301);
- gives the CUDA environment and suite commands, plus outcomes for `4848272`,
  `3f899f5`, `a3ba5aa`, the frozen replay, and the 182-pass implementer run
  (lines 303-325); and
- later labels the GPU outcomes author testimony rather than independent
  reproduction (lines 337-340).

It is still not a complete-command record. The Task 8 Step 1 freeze commands
`git status --short` and `git rev-parse HEAD` and their outcomes are absent; the
frozen replay's command is only inferable from the general independent-suite
block; and `codex exec ... - < <prompt>` at line 330 is a schematic placeholder,
not an exact reproducible command. That is acceptable only if it is labeled
schematic and the exact invocation/prompt is explicitly recorded as not
retained. It must not be presented as a complete command.

There is also a new factual error at lines 332-333: the report says both Codex
outputs are committed. Git currently reports `?? codex-report-check.md`.
`codex-review-findings.md` is committed in `a3ba5aa`; `codex-report-check.md` is
not.

### 4. What was verified, and by whom — PARTIAL

Most of this correction is applied correctly:

- author GPU claims are explicitly testimony, not independent verification
  (lines 337-340);
- the four-bit attribution is split correctly by sample count (lines 348-349);
- all five validation-history commits are named, with `a3ba5aa` and stamp
  `0db1996` attributed to the report check (lines 342-346);
- the no-GPU limitation and 169-pass/two-failure/one-skip implementer outcome
  are retained (lines 359-362); and
- absence of a Task 8/9 artifact is properly qualified as the pre-report-commit
  state (lines 350-351).

The round chronology is not yet internally consistent. Lines 332 and 342 call
the work “two rounds”; line 45 calls `3f899f5` the result of Codex round 1, line
46 calls `a3ba5aa` the result of round 2, and the method table then records a
separate Codex report check. More concretely, F11 says it was accepted in
“Codex round 1 and 2” (line 268), while the chronology table says F11 was found
in round 2 (line 447). The available round-1 record in the `3f899f5` commit
message describes two objections—private-helper reach and non-discriminating
parser assertions—and does not establish that round 1 raised F11.

The report should give one explicit chronology: round 1 led to `3f899f5` (and
say if its raw output was not retained); round 2 is the review preserved as
`codex-review-findings.md` in `a3ba5aa`; the later report check is preserved in
the currently uncommitted `codex-report-check.md`. F11 should be attributed to
round 2, with its omission from the draft caught by the report check, unless a
retained round-1 artifact demonstrates otherwise.

### 5. Findings F4-F11 — APPLIED

The requested substantive repairs are all present:

- F4 is now the most serious *correctable technical* defect, while F5 is
  explicitly the most serious overall finding (lines 133-135).
- F5 no longer certifies the unobserved remainder as unaffected. Lines 196-202
  say the overlaps establish only a minimum and that no independent provenance
  claim can be made for the rest of the suite.
- F7 now says only that no TurboQuant detail was identified in the supplied
  `CLAUDE.md`; it expressly rejects “cannot have shaped an assertion” and keeps
  the PI disposition open (lines 218-227).
- F9 is `partially corrected`, not blanket-corrected (lines 242-252).
- F10 exists and accurately records the in-process entry-point test and
  real-namespace cleanup risk as open (lines 254-264).
- F11 exists and correctly explains why the proposed second-arm interpretation
  is confounded and why the clean run is remediation plus prospective
  replication (lines 266-293).

The F11 round label still needs the attribution fix described under correction
4; the content and disposition themselves are restored.

### 6. Twelve unblocking conditions — APPLIED

The conditions at lines 369-413 are sufficient in combination. They require a
sanitized and independently checked bundle; retained prompt/session/material
records; a separately signed and timestamped pre-access freeze; sealed coverage
of all five public terminal gates including an actually passing author
differential; PI disposition of F7 and all rejected/waived findings; closure of
F8/F10 in the corroborative suite; named GPU reruns with the pinned clean author
checkout and no unexpected skips; a replacement Task 8 report that says
`passed`; and the full Task 9 registered execution, inspection, reruns, signed
evidence, and timestamp before the second model/cache-path plan is authorized.

Condition 5 also correctly states that using a third family is a remediation
control, not the causal variable that repairs this record. A rerun alone cannot
satisfy these conditions.

### 7. Note on method — APPLIED

Lines 426-460 replace the flattering account with a substantially accurate
chronology. They correctly say F1 survived freeze and was exposed by running
against the implementation, F2 was found during correction work, F7 was
self-disclosed, and the two pre-freeze simulated assertions were neither F1 nor
F2. The table then separates execution, validator correction work, the PI,
Codex review, and the report check instead of relabeling all detection as a
single superior “second position.”

The note's assignment of F11 to round 2 is consistent with the retained review;
the conflicting F11 heading elsewhere should be made to match it.

## What still must change before commit

1. Correct lines 332-333: `codex-report-check.md` is uncommitted. Do not call it
   committed unless it is actually added and committed.
2. Replace the ambiguous “Two rounds” account with the explicit round-1,
   round-2, and later report-check chronology above, including which raw outputs
   were not retained.
3. Change F11's disposition attribution from “Codex round 1 and 2” to round 2
   plus the report check that restored the omitted finding, unless documentary
   evidence for a round-1 F11 finding is supplied.
4. Either provide the exact Codex invocation and freeze-state commands/outcomes,
   or label the placeholder and reconstructed suite summaries as such and state
   exactly what command/prompt/output was not retained.

These are record-integrity corrections; they do not change the terminal status
`blocked` or any scientific disposition.

## Defect pattern still not recognized unaided

Yes: **the validator repeatedly treats a label or surviving code path as proof
that the named behavior was actually exercised.** Concretely, F2's override
test passed on an earlier parser error; F9's worker-input assertion silently
dropped commands missing the option; F3/F10 called an in-process `main()` call
the public console entry point; and the present report calls a placeholder
redirection an invocation and an untracked file “committed.”

These are the same defect shape: the description is stronger than the evidence
selected by the harness or record. The validator repairs each named instance
when another reviewer points it out, but still does not systematically audit
the negative space—what was filtered out, which earlier failure short-circuited
the intended check, whether the claimed boundary was crossed, and whether the
recorded state actually exists.
