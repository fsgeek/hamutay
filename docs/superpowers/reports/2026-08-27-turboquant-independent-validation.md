# TurboQuant R1 Independent Validation Report

Date: 2026-08-28

**Terminal status: `blocked`.**

Registered execution (Task 9) is not permitted on this record. This report is
the Task 8 Step 5 terminal artifact required by
`docs/superpowers/plans/2026-08-27-turboquant-algorithm-qualification.md`.

Author: Claude Opus 5 (`claude-opus-5`), the independent validation instance.
Principal investigator: Tony Mason. Implementation author: a Codex instance.
Review of this validation: a second Codex instance, invoked directly by the
validation author (`codex exec`), findings committed verbatim at
`codex-review-findings.md`.

## Summary

The independent suite runs clean against the implementation, and no
implementation defect was found. That is not sufficient to pass this gate, for
two independent reasons:

1. **The independence protocol was not met.** The validation author read the
   full qualification plan, which embeds implementer-authored test code, and
   reproduced some of it. Task 8 forbids prescribing test cases to the
   independent author. No prompt or material hashes were retained, so the
   exposure cannot be bounded from the record.
2. **R1 does not exist yet.** No Task 9 registered run has been executed. There
   is no million-pair evidence, no three-execution determinism artifact, no
   terminal five-gate record, and no qualification report. Passing unit and
   adversarial tests is a precondition for R1, not R1.

A third finding is material on its own: the frozen suite **weakened a
registered gate**, in a direction the specification explicitly forbids.

## Implementation under review

| Item | Value |
|---|---|
| Implementation commit | `b9227ce4b94374fc26167fc1357e0e9cc145af66` |
| OTS stamp of that tree | `e8de8bfa68656decc798bd9291b9c4adb1603e39` |
| Frozen independent suite | `86b896b116f507ef4a71a815ab7c3822a5238d86` |
| Correction 1 (post-access) | `4848272` |
| Retraction (model identity) | `910ae79` |
| Correction 2 (after Codex round 1) | `3f899f5` |
| Correction 3 (after Codex round 2) | `a3ba5aa` |

All commits are signed with the project key `01193FA2...` and each is followed
by an OpenTimestamps stamp commit.

## Test provenance

"193 tests pass" is **not** a statement about 193 independent tests. Accurate
accounting:

| Category | Count |
|---|---|
| Frozen at `86b896b` | 186 collected cases |
| — failed on first replay | 3 |
| Removed post-access (invalidly weakened gate, F4) | 1 |
| Added post-access (corroborative, **not** sealed) | 8 |
| Currently collected | 193 |

`186 - 1 + 8 = 193`. The eight additions comprise seven new test functions
(six in `test_artifact_contract.py`, one in `test_qualification_gates.py`) plus
one new parameter instance of an existing function in
`test_product_algorithm.py`.

"Failed on first replay = 3" is **not** the count of defective frozen cases.
F2 (a vacuous frozen test), F4 (an invalidly weakened frozen gate), F5
(provenance invalidated for the known copied cases), and F9 (further frozen
assertion defects) are all frozen-suite defects that did not appear as
failures. See those findings.

Per-file **collected cases** (not function counts):

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

Task 8 permits correcting invalid frozen tests in a new signed commit by their
author. It does not make post-access additions part of the sealed arm.

## Findings and dispositions

### F1 — Three frozen tests failed; all three were test defects

**Disposition: accepted (test defects, not implementation defects).**

Reported by the implementer: 183 passed, 3 failed.

| Test | Cause |
|---|---|
| `test_registered_profile_freezes_all_scientific_counts` | Omitted `--author-qjl-checkout`, required for registered runs by Task 7 |
| `test_registered_profile_uses_a_divisible_batch_size` | Same omission |
| `test_all_five_registered_gates_are_reported` | Asserted five gates from `evaluate_algorithm_gates`; Task 5 assigns it four, Task 7 joins the fifth at the CLI layer |

In each case the implementation was **stricter** than the test assumed.
Corrected in `4848272`. The intent was preserved at the correct layers rather
than deleted.

### F2 — A masked vacuous test (found while fixing F1)

**Disposition: accepted, corrected in `4848272`.**

`test_registered_profile_rejects_scientific_count_overrides` passed for the
wrong reason: the parser rejected its command for the missing checkout before
reaching the override guard. Six parametrized cases, all green, none
exercising the named behavior.

### F3 — Private-helper reach and non-discriminating assertions

**Disposition: accepted (Codex round 1), corrected in `3f899f5`.**

A test asserted the five-gate requirement by calling
`qualify._terminal_certification`, outside the black-box surface. Replaced
with end-to-end assertions through the public entry point. Refusal tests
asserting only a nonzero exit now assert the specific message.

Fixing this surfaced a defect in the tests themselves: they wrote run
directories into `experiments/turboquant/development/`, the project's evidence
namespace, and left them there. Now removed in a `finally` block.

### F4 — The frozen suite weakened a registered gate

**Disposition: accepted (Codex round 2), corrected in `a3ba5aa`. Most serious
*correctable technical* defect in this record. The most serious finding overall
is F5, the uncorrectable chain-of-custody failure.**

The frozen suite excluded four total bits from the `published_qjl_distortion`
15% assertion and substituted a 50%-wide diagnostic band. The stated
justification was a pre-freeze simulation showing ~15.4% relative error.

That simulation used a hand-rolled reference implementation, not the
implementation under review. Measured against the real quantizer:

| pairs | seed | observed | target `0.047/d` | relative error |
|---:|---:|---:|---:|---:|
| 20,000 | 34 | 0.0004136921 | 0.0003671875 | 12.67% |
| 100,000 | 34 | 0.0004119568 | 0.0003671875 | 12.19% |
| 200,000 | 34 | 0.0004169594 | 0.0003671875 | 13.55% |
| 200,000 | 7 | 0.0004146673 | 0.0003671875 | 12.93% |

All inside the registered 15% band.

**Correction to an earlier draft of this report.** The draft presented three
rows as one procedure at increasing sample size, but its 200,000 row silently
used seed 7 while the others used seed 34. The seed-34 value at 200,000 pairs
is 0.0004169594 (13.55%), not 0.0004146673 (12.93%). Both are inside the band,
so the disposition is unchanged, but the draft misdescribed its own procedure.
Caught by the Codex report check.

**Attribution.** The earlier Codex review (`codex-review-findings.md`)
independently reproduced the 20,000- and 100,000-pair values only. The
200,000-pair rows were produced by the validation author; the seed-34 value was
independently reproduced by the Codex report check.

The exclusion was also **forbidden**. The specification designates *the
analytic scalar residual and its `pi/2` scaling* as the non-gating
diagnostics — not the four-bit QJL distortion — and states that "the
registered 15% tolerance is not adjusted after observation." Task 5 directs
that the four-bit rounding be called out "without changing its gate."

A validator loosening a registered scientific tolerance to accommodate a
defect in its own scaffolding is the failure this gate exists to prevent.
Restored at all four bit widths; the suite passes at full strictness.

### F5 — Exposure to plan-prescribed test cases (independence defect)

**Disposition: accepted (Codex round 2). Not disclosed by the author before
review. Not correctable within this record.**

The suite README claimed the author received "the qualification plan's
'Interfaces' sections (public names only)." Inaccurate: the author read the
entire plan, which embeds complete implementer-authored test code.

Verified overlaps:

- `test_values_inside_every_boundary_pass` reproduces the plan's constructor
  shape and its constants `1.0049`, `1.0049 / 1.149`, `1.149`, `0.1`,
  `0.00199` — reverse-engineered boundary values, not independently derivable.
- `test_registered_workers_are_three_fresh_processes` reproduces the plan's
  mock-subprocess structure, command slicing, execution indices, and expected
  output tuple nearly verbatim.

Task 8: the task "intentionally does not prescribe test cases: doing so would
make the implementer the independent-test author." For these cases, it did.

The two verified overlaps establish a **minimum**, not a maximum. The record
cannot both say the exposure "cannot be bounded" and certify the remainder as
clean. Accurately: the known direct overlaps are in the gate-logic and CLI
tests; the numerical oracles pass and are consistent with arXiv 2504.19874 as
independently derived mathematics; but with no prompt or material records
retained, **no independent provenance claim can be made for the remainder of
the suite.**

### F6 — False model identity in two signed commits

**Disposition: retracted in `910ae79`; underlying chain-of-custody gap not
correctable within this record.**

Commits `86b896b` and `4848272` record `Model: claude-fable-5`. The author is
Claude Opus 5. The identifier was inherited from the task instructions and
never checked against the author's own system prompt. Corrected only after the
PI pointed it out.

The signatures authenticate PI-controlled commits, not model identity. With
the required identity field wrong twice and no retained session record, model
provenance for the freeze rests on testimony, not evidence.

### F7 — CLAUDE.md supplied before freeze

**Disposition: RESOLVED 2026-08-28. Recorded as a disclosed, non-material
protocol deviation. Accepted by the principal investigator (Tony Mason).**

`CLAUDE.md` (116 lines, nine sections) was supplied to the validation author
before the freeze and was declared in the freeze commit's materials list from
the outset. It was not an undisclosed exposure.

**Evidence.** A case-insensitive search of `CLAUDE.md` for every relevant
term — `turboquant`, `qjl`, `lloyd`, `codebook`, `quantiz`, `rotation`,
`sketch`, `distortion`, `bootstrap`, `gate`, `128`, `0.047`, `1.57` — returns
zero matches. This is not "no implementation details were identified"; it is
the absence of any occurrence.

```
grep -in "turboquant\|qjl\|lloyd\|codebook\|quantiz\|rotation\|sketch\|\
distortion\|bootstrap\|gate\|128\|0.047\|1.57" CLAUDE.md   # no output
```

The document's sections are: git signing and OpenTimestamps stamping
(process — and the reason the file was supplied, the task having named it as
the source of the signing identity); running experiments and the chat
interface (process); and four sections of methodological guidance about
**tensor projection**, a different subsystem — `max_tokens` truncation, the
`Projector` comparability rule, tensor capture, and batch size as confound.

**The strongest argument against non-materiality, and why it fails.** The four
methodological sections are not empty of transferable disposition: they concern
silent truncation, stripped-down schemas producing structurally different
results, and controlling confounds. One could argue that reading them primed an
adversarial testing posture.

That argument proves too much — any exposure to sound methodology would then
count as contamination, making independence unattainable rather than merely
difficult. It also points the wrong way. This validator's actual failures (F2,
F9, and the first version of the F8 tolerance test) were three silently vacuous
assertions. `CLAUDE.md`'s central lesson is that silent failure is worse than a
crash. Had that transferred, those are precisely the defects it would have
prevented. It did not.

**Contrast with F5.** F5 is a specific numeric value (`1.0049 / 1.149`)
appearing byte-identical in the implementer's plan and the validator's test —
a demonstrated channel carrying implementer test design to the validator. F7
has no such channel, because the document contains nothing about this
algorithm.

**PI disposition.** The principal investigator reviewed the evidence and
judged the deviation non-material, accepting it for this record. The
specification requires a written technical disposition for findings that are
not treated as blocking; this is that disposition.

**What this resolution does not do.** It does not unblock the gate. F5 and F6
keep this record `blocked` regardless of how F7 resolves. Non-material is not
harmless: F7 independently prevents describing this record as a clean
sealed-envelope validation, and the suite README states that.

**Forward condition (new, condition 13).** The clean re-freeze must receive the
signing identity as a bare identity string in its prompt rather than the whole
`CLAUDE.md` file, removing the deviation entirely from the next round rather
than re-litigating it.

### F8 — The independent suite never exercises the author differential

**Disposition: accepted (Codex round 2). CLOSED 2026-08-28 as corroborative
post-access coverage; see the note below on what that does and does not
satisfy.**

`test_author_contract.py` verifies the pinned commit and file hashes, the
declared zero-sign convention difference, and CUDA preconditions. It never
compiles the author kernels, performs a byte comparison, or compares scores.
The end-to-end tests run development mode and assert the fifth gate is
`not_run`, so `author_code_differential` is never observed passing.

One of five mandatory R1 gates had no independent coverage. Implementer
coverage exists but is not independent coverage.

**Closure.** `TestAuthorDifferentialExecution` now compiles the pinned author
kernels, runs the real differential on CUDA, and observes the gate reach
`passed` rather than asserting `not_run`. Measured on the GPU host:

| quantity | observed | pinned tolerance |
|---|---:|---:|
| max absolute score error | 3.814697265625e-06 | 1e-5 |
| max relative score error | 3.85266366720316e-06 | 1e-4 |
| inlier packed sign bytes equal | true | — |
| dummy outlier norms exact zero | true | — |

Suite total 193 → 197 collected; 197 passed with no skips.

**This is corroborative coverage on a compromised suite.** Per condition 6 it
does not supply sealed independent coverage: the new frozen suite must carry
its own author-differential execution.

**Defect found while closing this finding.** The first version of
`test_frozen_tolerance_is_not_widened_by_the_oracle` iterated the comparison
records and asserted only where `max_absolute_error` was present, with an
`or passed is True` escape clause. Three of five comparisons contributed no
assertion. That is the exact label-stronger-than-evidence shape named below,
reproduced inside the test written to close a finding about it, and caught by
the author only because the reviewer had just named the pattern. Rewritten to
assert the gate's observed values directly.

### F9 — Smaller assertion/description mismatches

**Disposition: accepted, partially corrected in `a3ba5aa`. Two items remain
open — see F10.**

`test_each_worker_receives_the_same_frozen_inputs` built its set only from
commands containing `--resolved-inputs` then asserted `len <= 1`, which an
empty set satisfies — the third instance of the F2 defect class in this suite.
Now requires the option on every command and pins its value. Also: `OWNDATA`
asserted where the test name promised it; codebook immutability asserted
alongside rotation; CLI exit code asserted.

### F10 — Two harness items

**Disposition: accepted. CLOSED 2026-08-28 as corroborative post-access work.**

1. `TestTerminalEvidence` claimed to exercise the public console entry point
   but imported and called `main()` in-process. An in-process call shares the
   test's interpreter, its imported modules, and its initialized NumPy state,
   and would pass even if the installed `turboquant-qualify` script were broken
   or absent. It now invokes the installed console script as a subprocess in a
   fresh interpreter. A guard test, `test_console_script_runs_in_a_fresh_
   interpreter`, fails if a future refactor reverts to an in-process call.
2. Those tests wrote into the real evidence namespace and relied on `finally`
   cleanup, so abrupt process death could leave residue. Cleanup is now
   belt-and-braces: the run directory is removed in a `finally`, **and** any
   residue from a previously killed process is swept on entry. Verified after
   a full suite run: `experiments/turboquant/development` contains no run
   artifacts. The namespace directory itself is retained when it pre-existed,
   which is correct — the tests must not delete a namespace they did not
   create.

**Defect found while closing this finding.** The rewritten helper captured the
subprocess's `stderr` and never asserted it — the same recorded-but-unasserted
shape as the `_exit_code` defect corrected earlier. Now asserted: a development
run must not emit a traceback even when its gates fail. This is the second
consecutive finding whose closure reproduced, in miniature, the defect being
closed.

Suite total 197 → 198 collected; 198 passed with no skips.

### F12 — The F5 remediation shipped F5

**Disposition: accepted (Codex bundle check, condition 2). Corrected.**

The sanitized bundle builder written to prevent F5 wrote its dropped-lines
audit log **into the delivery directory**. That log quotes the exact
implementer test code that caused F5 — `1.0049`, `1.0049 / 1.149`, `1.149`,
`0.00199`, `def test_values_inside_registered_gate_boundaries_pass`,
`def test_registered_workers_are_three_fresh_processes`, `monkeypatch.setattr`,
the mock structure, and hundreds of further assertion prefixes. Sixty-character
truncation does not sanitize a design.

Handing that directory to the clean validator as a unit would have reproduced
F5 exactly, through the artifact built to prevent it.

The author's own leak audit passed because it grepped `interface-contract.md`
rather than the directory. The delivered set was never audited as a set. This
is the same negative-space failure as F2, F9, and the F8 and F10 closures: the
check examined the object the author was thinking about, not the object that
would actually be handed over.

Corrected: the audit log is written outside the bundle, prefixed
`VERIFIER-ONLY`, named in the manifest as excluded from delivery, and the leak
audit now runs over every file in the delivery directory.

**This is the third consecutive finding whose remediation reproduced the defect
being remediated** (F8's tolerance test, F10's stderr capture, and now the
bundle builder). The recurrence is recorded as data, not as contrition.

### F13 — The first bundle was over-stripped

**Disposition: accepted (Codex bundle check). Corrected.**

Over-stripping manufactures false findings as surely as leakage manufactures
false confidence. The first bundle omitted public contract a clean validator
needs and cannot obtain from the paper or specification:

- the `QualificationResult`, `QualificationMetrics`, and `GateResult` field
  contracts — the exact area where the contaminated round copied a plan
  constructor, because the schema was otherwise unavailable;
- the row-vector convention (`x @ rotation.T`), zero-vector handling, the
  transparent `+1` zero-sign rule against the kernel's `-1`, little-endian bit
  packing, the `derive_seed` wire format, and the `b-1` bit accounting;
- the public CLI and evidence behavior needed to test the five gates as a
  black box.

Without these a clean validator can reasonably choose a column-vector
convention, the opposite zero-sign rule, or a different bit order, and produce
false failures against a correct implementation.

All are now declared in the contract as behavior, with no worked values, test
names, assertions, or implementation steps.

### F14 — The sanitized contract stated two facts that were false

**Disposition: accepted (Codex final delivery audit). Corrected.**

The delivery set and chain of custody passed the final audit. The contract did
not: two of its declarations were wrong in ways that would have manufactured
false findings against a correct implementation.

1. **"All-zero codes and sketches" for a zero vector.** Verified against the
   implementation: a zero vector's `packed_signs` is `[255, 255]` — every
   in-range bit set — because a zero projected value maps to `+1`. What is
   all-zero is the indices and the norms, and the zero norm is what forces
   exact-zero reconstruction. A clean validator reading the original wording
   would have asserted all-zero bytes, observed `255`, and filed a false
   finding.
2. **"The author-differential gate additionally carries `status`."** False.
   `status` is a field of every `GateResult`. A validator could have asserted
   the first four gates lack it and manufactured a failure.

Also corrected: `QualificationMetrics` publicly carries 23 fields, not the 10
declared — the omitted ones carry the sensitivity arm, sample accounting, the
analytic diagnostic, and the block-bootstrap evidence. `QualificationResult`
carries eight, not two. The CLI declaration named no concrete options or
artifact filenames, leaving a pre-access validator to guess both, and omitted
the enforced output namespaces and the development exit-status behavior. Two
representation boundaries — the midpoint tie direction and the non-broadcasting
query/key shape rule — were undeclared, and either could be reasonably guessed
wrong.

All are now declared and were verified programmatically before commit: every
public dataclass field, every CLI option in `--help`, and every artifact
filename appears in the contract.

**The pattern, again.** The first contract was written from what the author
remembered of the interfaces rather than from the implementation's actual
public surface. Reading is not verifying. This is the same shape as F12: the
author checked the artifact he was thinking about rather than the artifact
that would be handed over.

### F11 — The proposed "second arm" framing was unsound

**Disposition: accepted (Codex round 2; its omission from the first draft of
this report was caught by the report check). The author's proposal is
withdrawn.**

The validation author proposed that a clean cross-family re-freeze be treated
as a second experimental arm testing whether "independent" requires
decorrelated weights or merely a separate session, rather than as remediation.

That framing is motivated reasoning. The old and new runs would differ
simultaneously in model family, prompt hygiene, supplied materials,
recordkeeping, and test-author instructions, with one session per condition.
Confounded conditions with n=1 per cell cannot answer the methodological
question. Model-family labels are also only proxies for weight decorrelation;
shared training data and published artifacts remain uncontrolled.

Answering the methodological question would require a prospective design:
multiple fresh sessions within and across families, identical hashed prompts
and bundles, the same frozen implementation, blinded disposition rules, and
predefined outcomes such as unique valid defect yield and overlap.

The clean run is **remediation of a failed chain of custody**, plus a
prospective cross-model replication that may yield exploratory evidence. It
does not retroactively convert this record into a controlled first arm.

The author notes for the record that it advanced this proposal after
explicitly flagging its own conflict of interest in doing so, which did not
prevent the error.

## Commands and outcomes

Task 8 Step 5 requires "complete commands and outcomes". **Recordkeeping
defect: complete original output was not retained** for the pre-freeze
simulation or the implementer's first frozen-suite replay. The commands and
summary outcomes below are what the record supports; the absence of full
preserved output is itself a defect of this record.

Task 8 Step 1 freeze state (validation author): `git status --short` reported a
clean tree; `git rev-parse HEAD` reported
`e8de8bfa68656decc798bd9291b9c4adb1603e39`. **Raw output not retained.**

Independent suite, GPU host (validation author):

```
CUDA_HOME=/usr/local/cuda-12.8 PATH=/usr/local/cuda-12.8/bin:$PATH \
  QJL_AUTHOR_CHECKOUT=/tmp/hamutay-turboquant-author/QJL \
  uv run pytest tests/turboquant_independent -q
```
Outcome at `a3ba5aa`: `193 passed`. At `3f899f5`: `193 passed`. At `4848272`:
`189 passed`.

Implementer suite, GPU host (validation author):

```
CUDA_HOME=/usr/local/cuda-12.8 PATH=/usr/local/cuda-12.8/bin:$PATH \
  QJL_AUTHOR_CHECKOUT=/tmp/hamutay-turboquant-author/QJL \
  uv run pytest tests/turboquant -q
```
Outcome: `182 passed`. **Author-reported; not independently reproduced** (see
below).

Frozen suite replay, GPU host (validation author, at `86b896b`): `183 passed,
3 failed` — the three named in F1. Reported independently by the implementer
with the same result.

Codex review invocations (validation author). **Schematic, not an exact
reproducible command** — the prompt files were written to a session scratchpad
that is not retained, and the exact invocations are therefore not recoverable:

```
codex exec --sandbox workspace-write -C . - < <prompt-file>
```

Explicit chronology of external review:

| Round | Raw output | Preserved as |
|---|---|---|
| Round 1 (two objections: private-helper reach; non-discriminating parser assertions) | **not retained** | Summarized in the `3f899f5` commit message only |
| Round 2 (full disposition review) | retained | `codex-review-findings.md`, committed in `a3ba5aa` |
| Report check (this report, pre-commit) | retained | `codex-report-check.md` |
| Verification of corrections | retained | `codex-verify-2.md` |

**Recordkeeping defect:** round 1's raw output was not preserved. Its findings
survive only as the author's summary in a commit message.

## What was verified, and by whom

**Author-reported, GPU host, not independently reproduced** (testimony, not
independent verification, in the absence of retained full output): the 193
independent passes; the 182 implementer passes; the frozen-suite 183/3 replay;
the four-bit measurements at 200,000 pairs.

**Independently verified by Codex** (round 2, the report check, and the
corrections verification; isolated clones, no GPU):
the Task 8/Task 9 requirements and the five gate definitions; good signatures
and OTS stamp commits on all five validation-history commits (`86b896b`,
`4848272`, `910ae79`, `3f899f5`, `a3ba5aa` — the last verified in the report
check, with stamp `0db1996`); collected-case totals of exactly 186 and 193 and
the per-file breakdown; replay of the frozen suite (`182 passed, 3 failed,
1 skipped`, same three failures); the four-bit values at 20,000 and 100,000
pairs (round 1) and at 200,000 pairs seed 34 (report check); the
plan-prescribed test overlap; the absence of any Task 8 or Task 9 artifact in
`HEAD` **as observed before this report was committed**.

**Not verified by anyone:** the author CUDA differential through the
independent suite (F8); any registered million-pair result (none exists); the
pre-freeze prompt, material bundle, fresh-session status, or provider-side
model identity (no records retained); external Bitcoin anchoring of the
timestamp proofs.

Codex could not reproduce the implementer GPU run — its sandbox has no GPU,
reaching 169 passed with two CUDA-preflight failures and one CUDA module skip
(171 collected). Those outcomes reflect the unavailable GPU and are not
evidence against the GPU-host result, but they also do not confirm it.

## Conditions to unblock

These are necessary and, taken together, intended to be sufficient. A rerun
alone does not satisfy them.

1. Build a sanitized bundle: the approved specification, an extracted
   interfaces-only contract with **all worked test examples stripped**, arXiv
   2504.19874 v1, and the Task 7 author-QJL contract. Nothing else — not the
   full plan, CLAUDE.md, repository history, khipus, logs, review documents,
   implementer tests, or implementation source.
2. Verify the stripping independently. The author of F5 is not competent to
   certify the absence of the defect it failed to notice.
3. Retain hashes of every supplied file, the complete prompt, the
   provider-reported model identifier, the session identifier, and the
   implementation commit hash.
4. The clean validator freezes its suite in a **separately signed and
   OpenTimestamps-stamped commit before any implementation access**, with the
   complete freeze and first-run output preserved.
5. Use a **third** model family. Codex implemented; Claude validated. Note that
   the existing suite already satisfies "different family from the implementer"
   literally — the reason to re-run is the broken chain of custody (F5, F6),
   **not** family. Per F11, the clean run is remediation plus prospective
   replication, not a controlled experiment on model-family independence, and
   must not be described as one.
6. The new frozen suite must independently cover the public terminal behavior
   of **all five** mandatory gates, including execution and successful
   observation of `author_code_differential` on the target CUDA environment.
   Post-access F8 coverage added to the present suite is corroborative only and
   cannot supply sealed independent coverage.
7. Resolve F7 with a written PI disposition. Every rejected or waived finding
   requires the written technical disposition and PI approval the specification
   demands.
8. Close F8 and F10 in the present suite as corroborative work.
9. Rerun, on the target GPU with the pinned clean author checkout and no
   unexpected skips, with full output preserved: **the implementer suite
   (`tests/turboquant`) and the new frozen independent suite**. State
   separately whether the present suite, retained as corroboration, must also
   pass.
10. Retain the present suite as **corroborating** evidence only. Do not seed
    the new validator with its test cases.
11. Produce a replacement Task 8 terminal report containing the full commands
    and outcomes and stating `passed`. A blocked or merely existing report does
    not authorize Task 9.
12. Only then execute Task 9: the exact registered command in a clean worktree,
    one million registered pairs, three fresh-process execution records with
    matching hashes, independent inspection of all five gates and every
    artifact hash and value, complete implementer and independent reruns with
    the author differential active, and a signed, timestamped R1 evidence and
    report commit. **Only a passing Task 9 record authorizes writing the second
    model/cache-path plan; a passing Task 8 alone does not.**
13. Supply the clean validator with the signing identity as a bare string
    (email, name, key fingerprint) in its prompt. Do not supply `CLAUDE.md`.
    This removes F7's deviation from the next round at negligible cost.

## Disposition requested from the principal investigator

- **F7 (CLAUDE.md): RESOLVED.** Recorded as a disclosed, non-material
  deviation and accepted by the PI on 2026-08-28. Condition 13 removes it from
  the next round.
- **F8, F10: CLOSED** 2026-08-28 as corroborative post-access coverage. Per
  condition 6 neither supplies sealed independent coverage; the new frozen
  suite must carry its own.
- **F5, F6:** the author does not recommend waiving these. They are the reason
  this report is `blocked` rather than `passed`.
- If the PI elects to proceed for internal engineering purposes despite F5 and
  F6, that should be a prospective plan amendment, and the result must be
  labeled a development or prequalification result — not R1, and not a
  sealed-envelope validation.

## Note on method

An earlier draft of this section claimed that every substantive defect was
found by a second position and none by the validator's own care. That is
false, and flattering in a way that should be recorded rather than quietly
fixed. F1 survived into the frozen commit and was exposed only when the frozen
suite was run against the implementation. F2 was found by the validator itself
while correcting F1. F7 was disclosed by the validator in the original freeze
record. The pre-freeze simulation caught two proposed assertions, but neither
was F1 or F2.

The accurate chronology, without the moral:

| Defect | Found by | When |
|---|---|---|
| Two bad proposed assertions | Validator, simulating against its own reference | Pre-freeze |
| F7 (CLAUDE.md) | Validator, self-disclosed | At freeze |
| F1 (three failing tests) | Execution against the implementation | First replay |
| F2 (vacuous test) | Validator, while correcting F1 | Post-access |
| F6 (false model identity) | Principal investigator | Post-access |
| F3, F9 | Codex, round 1 and 2 | Post-access |
| F4, F5, F8, F11 | Codex, round 2 | Post-access |
| Seed misdescription, count errors, softened findings, omitted findings | Codex report check | Pre-commit |

The defensible reading is narrower than "a second position always wins."
Repeated self-review did not prevent the frozen failures, the invalid
tolerance change, the materials misdescription, or the vacuous assertions —
and in two cases the validator produced confident written arguments defending
what was wrong (the README paragraph justifying the weakened gate, and the
materials list misdescribing what had been read). Execution, correction work,
the PI, and external review each found different defects at different times.

This is recorded because it is the operative finding about the method, and
because a validator reviewing only itself would have shipped every one of
F3-F5, F8, and F11.

### The defect shape, named by the reviewer

Asked whether this validator has a defect pattern it cannot see unaided, the
Codex report check answered, and the answer is reproduced because it predicts
the failures better than any account the validator produced about itself:

> The validator repeatedly treats a label or surviving code path as proof that
> the named behavior was actually exercised.

The instances are the same shape at four different layers:

| Instance | The label | What was actually exercised |
|---|---|---|
| F2 | "rejects scientific count overrides" | An earlier parser error on a missing checkout |
| F9 | "each worker receives the same frozen inputs" | A set built only from commands that had the option; empty passes |
| F3/F10 | "executes the public console entry point" | An in-process `main()` call |
| This report | "outputs committed at ..." | One committed file and one untracked file |

In each case the description was stronger than the evidence the harness or the
record actually selected. The validator repairs each named instance once
someone points at it, and does not then audit the negative space: what was
filtered out, which earlier failure short-circuited the intended check, whether
the claimed boundary was crossed, whether the recorded state exists.

A validator with this defect cannot be trusted to certify its own coverage,
which is an argument for conditions 2 and 6 rather than a confession.

*If this report has drifted from the artifacts, believe the artifacts:
`tests/turboquant_independent/`, `codex-review-findings.md`, and commits
`86b896b`, `4848272`, `910ae79`, `3f899f5`, `a3ba5aa`.*
