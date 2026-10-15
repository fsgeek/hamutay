# Codex review of the proposed TurboQuant R1 disposition

Date: 2026-08-28

## Bottom line

**Block acceptance of internal R1 on the current evidence.**

The current state is a useful development/prequalification checkpoint. It is not R1 as that term is defined by the approved plan and specification. There is no Task 8 terminal validation report, no registered one-million-pair run, no three-execution evidence set, no terminal five-gate artifact, and no R1 qualification report in the current tree. Passing unit and adversarial tests is a precondition for that evidence, not a substitute for it.

I also disagree with the proposal's characterization of the independence problem as only an extra `CLAUDE.md`. The frozen suite contains near-verbatim copies of test code prescribed in the implementer-authored qualification plan, while the README says only the plan's public-interface sections were supplied. The freeze commit itself says the "qualification plan" was supplied. With no retained prompt or material hashes, that conflict cannot be resolved from the record. It is material because Task 8 expressly says not to prescribe test cases to the independent author.

The proposed second suite is worthwhile, but it is remediation and prospective replication, not a valid post-hoc experimental arm capable of answering whether weight decorrelation is necessary for independence.

## 1. R1 disposition

### Decision

**Blocked, not accepted with conditions in its present state.** Conditions can define how to unblock it, but the R1 label should not be granted now.

The approved plan makes the sequence explicit:

1. Task 8 ends in a separately committed terminal validation report with status `passed` or `blocked`, complete commands and outcomes, every disposition, and PI approval where a finding is rejected.
2. Task 9 may begin only after that report says `passed` and both suites pass with the pinned author checkout in a clean worktree.
3. R1 then requires the registered one-million-sample execution, three fresh worker executions, all five gates, immutable artifacts, independent artifact inspection, and a signed qualification report.

None of the required Task 8 or Task 9 report/evidence files exists in `HEAD`. In particular, the paths named by the plan under `docs/superpowers/reports/` and `experiments/turboquant/qualification/r1-initial/` are absent. Therefore the proposal's inference from “193 tests plus 182 tests” to “internal R1” changes the meaning of R1 after seeing development results.

Part (3) of the proposal states the correct scope of a passing R1: it authorizes writing the second implementation plan, not claiming a cache-path result. But that scope restraint does not cure the absence of the R1 run itself.

### Precise conditions to unblock R1

1. Run a genuinely fresh validation session with a sanitized, immutable bundle containing exactly the approved specification, an extracted public-interface contract, arXiv 2504.19874 v1, and the pinned Task 7 author-QJL contract. Do not supply the full qualification plan, `CLAUDE.md`, repository history, khipus, logs, review documents, implementation tests, or implementation source before freeze.
2. Retain hashes of every supplied file, the complete prompt, the provider-reported exact model identifier, the implementation commit under review, and the session identifier. The validator model must be from a family different from the implementer, as the specification requires. Being different only from Claude Opus 5 is insufficient if it is from the implementer's family.
3. Freeze the new suite in a separately signed and timestamped commit before any implementation access. Do not count tests added after access as sealed independent tests. Corrections to invalid frozen tests may remain in later signed commits, but new post-access coverage must be labeled corroborative.
4. Correct the concrete suite defects listed below. The current suite may remain as corroborating evidence, but the clean suite should not be coached with these specific test cases before its own freeze.
5. Produce the Task 8 terminal validation report required by the plan. It must include the frozen implementation and test commits, complete original and corrected outcomes, all dispositions, the protocol deviations, the distinction between frozen and post-access tests, and the PI's written disposition. “Written in signed commit messages” is not the report the plan requires.
6. On the target GPU/CUDA environment, rerun both suites with the pinned clean author checkout and no unexpected skip. Preserve the complete output.
7. Only after Tasks 1-8 are clean and committed, run the exact Task 9 registered command in a clean worktree. Verify the one-million-pair metrics, all three execution hashes, the author differential, every gate, and every artifact hash independently; then commit and timestamp the R1 report and evidence.

If the PI instead chooses to waive the independence protocol for internal engineering purposes, that should be a prospective plan amendment and the result should be called a development or prequalification result, not R1 and not a sealed-envelope validation.

## 2. The proposed “second arm”

### The useful part

A clean suite from another model family can find coverage holes and provide useful triangulation. If it finds a defect, that is actionable evidence that the first suite missed something. If it converges, that modestly strengthens confidence in the implementation and in the clarity of the public contract.

### The unsound part

Calling it a second experimental arm rather than remediation is motivated reasoning. The first run violated its materials protocol, recorded a false model identity, lacked retained prompt/material hashes, copied plan-prescribed test structures, and later accumulated post-access tests. A new run would differ simultaneously in model family, prompt hygiene, supplied materials, recordkeeping, and likely test-author instructions. Those differences are confounded.

One session in each condition cannot test whether “independent” requires decorrelated weights rather than a separate session. It can only compare the outputs of two particular sessions under different conditions. Model-family labels are also only proxies for weight decorrelation; shared training data, published artifacts, and convergent scaffolding remain uncontrolled.

To investigate the claimed methodological question, the study would need a prospective design with multiple fresh sessions within the same family and across different families, identical hashed prompts and bundles, the same frozen implementation, blinded disposition rules, and predefined outcomes such as unique valid defect yield and overlap. Even that would estimate robustness across the sampled systems, not establish a general necessary condition for independence.

The clean run should therefore be described as:

- remediation of the failed chain of custody for the current Task 8 gate; and
- a prospective cross-model replication that may provide exploratory evidence about reviewer diversity.

It should not be described as retroactively converting the current run into a controlled first arm.

## 3. Material independence defects beyond `CLAUDE.md`

### 3.1 Exposure to prescribed test cases

This is the most important undisclosed defect.

Task 8 permits the plan's frozen public interfaces but says the task intentionally does not prescribe test cases. The README says the validator received “The qualification plan's ‘Interfaces’ sections (public names only).” The freeze commit instead records “qualification plan” without that limitation.

The frozen tests contain highly specific code from outside the interface declarations. Two examples are decisive:

- The plan's `test_values_inside_registered_gate_boundaries_pass` and the frozen suite's `test_values_inside_every_boundary_pass` use the same constructor structure and the same peculiar constants: `1.0049`, `1.0049 / 1.149`, `1.149`, `0.1`, and `0.00199`.
- The plan's `test_registered_workers_are_three_fresh_processes` and the frozen suite's test of the same name use the same mock-subprocess structure, command slicing, execution indices, and expected output tuple, nearly verbatim.

These are not merely tests naturally implied by public symbol names. They are implementer-plan test designs. Either the validator saw more of the plan than the README admits, or the supplied “interface” bundle itself included prescribed tests. In either case, those copied cases are not independently authored. The current record cannot determine the exposure because no prompt or material hashes were retained.

The extra `CLAUDE.md` is comparatively minor: its current contents contain no TurboQuant implementation detail. It is a formal protocol deviation and prevents a clean-envelope claim, but the plan-test exposure is scientifically more material.

### 3.2 Post-access tests are counted as independent

The frozen suite had 186 collected cases. The current suite has 193 because seven test functions now present were added after implementation access. The additions include checkout/profile assertions and the four `TestTerminalEvidence` cases. They may be useful tests, but they are not sealed independent tests.

Thus “193 independent tests pass” is false as a provenance statement. A fair accounting is: 186 frozen cases, three of which were invalid as written and later corrected, plus seven post-access corroborative cases. The corrections are allowed by Task 8 when documented, but they do not turn newly designed post-access tests into part of the original sealed arm.

### 3.3 The authorship record is not independently authenticated

I verified that commits `86b896b`, `4848272`, `910ae79`, and `3f899f5` have good signatures from the repository's Tony Mason key, and each is followed by an OpenTimestamps proof commit. That authenticates the PI-controlled commits, not the model identity or the exact materials seen by the model.

The repository verifies that `910ae79` retracts the two false Fable identifiers. It does not independently prove that Claude Opus 5 authored the freeze. I accept the Opus identity only from the supplied context and the retraction, not from cryptographic evidence. Given that the required identity field was wrong twice, the missing prompt/session record is material chain-of-custody evidence, not cosmetic paperwork.

Reading implementation, history, khipus, and logs after the freeze does not retroactively alter frozen test bytes. It does affect the independence of failure dispositions, corrections, and newly added tests. Those later products should be labeled post-access analysis, not part of the sealed arm.

## 4. Remaining defects and gaps in the suite

### 4.1 The suite incorrectly weakens the four-bit QJL gate

`test_product_algorithm.py` excludes four total bits from the 15% published-distortion assertion and replaces it with a loose `0.5 * expected < observed < 1.5 * expected` diagnostic. The README likewise says four-bit QJL distortion is not a gate.

That directly contradicts the approved specification and plan. Both require `published_qjl_distortion` at all bit widths 1 through 4 to remain within 15%, explicitly call the analytic four-bit residual a non-gating diagnostic, and explicitly say the registered 15% tolerance is not adjusted after observation. The [paper itself reports all four product-distortion targets, including `0.047/d`](https://arxiv.org/html/2504.19874).

The weakening is not needed for the suite's current seed. I reproduced normalized four-bit errors of `0.0004136921` at 20,000 pairs and `0.0004119568` at 100,000 pairs against the target `0.0003671875`, relative errors of about 12.7% and 12.2%. Both pass the frozen 15% rule. More importantly, the current tests would not catch an implementation that selectively exempted bit width four in gate evaluation: the generic boundary test uses only a one-bit metric, while the actual four-bit Monte Carlo test accepts a 50% band.

This must be corrected and the README retracted on this point.

### 4.2 The independent suite never runs the author-code differential

`test_author_contract.py` checks commit/file pins, the zero-sign convention, CUDA precondition reporting, and whether `nvidia-smi` sees a device. It contains no call to the author QJL oracle, no CUDA kernel compilation, no byte comparison, and no score comparison. On a GPU, its only GPU-sensitive test merely confirms device visibility.

The current end-to-end tests deliberately run development mode without an author checkout and assert that the fifth gate is `not_run`. Therefore the independent suite never observes `author_code_differential` pass through the public CLI. This is a material coverage gap around one of the five mandatory R1 gates. The implementer suite has a substantial CUDA differential test, but implementer coverage is not independent coverage.

### 4.3 A worker-input test passes if the argument is missing entirely

`test_each_worker_receives_the_same_frozen_inputs` builds the set of `--resolved-inputs` arguments only for commands that contain the option, then asserts `len(resolved_arguments) <= 1`. If all three commands omit `--resolved-inputs`, the set is empty and the test passes, contrary to its name and docstring.

It should require every command to contain the option and require the set to equal `{str(resolved)}`.

### 4.4 Smaller assertion/description mismatches

- `test_rotation_is_c_contiguous_and_owns_its_memory` checks C-contiguity but never checks `owndata`.
- `test_frozen_rotation_and_codebook_are_not_writable_through_the_quantizer` verifies isolation/read-only behavior for the rotation but does not verify that the quantizer's codebook resisted mutation of the constructor input or direct writing.
- `TestTerminalEvidence` says it executes the public console entry point, but it imports and calls `main()` in-process. It does not test the installed `turboquant-qualify` command or a fresh interpreter, and it stores `_exit_code` without asserting it.
- Those terminal tests still write into the real evidence namespace and rely on `finally` cleanup. Normal failures clean up, but process termination can leave residue. This is less serious than the defects above, but it is avoidable harness risk.

These smaller issues do not independently block R1, but they show that the suite should not be accepted based on test count alone.

## What I verified and what I did not

### Verified directly

- The exact Task 8 and Task 9 requirements in the approved plan and the five R1 gate definitions in the approved specification.
- The contents and history of `tests/turboquant_independent/`.
- Good repository signatures on all four cited commits and the existence of their follow-on timestamp proof commits.
- The retraction text in `910ae79` and the later README disclosure.
- Replay of the frozen `86b896b` suite against the current implementation: 182 passed, the same three named tests failed, and one GPU-visibility test skipped because this sandbox cannot see the GPU. The author's reported 183 passes is consistent with that skipped visibility test passing on its GPU.
- Current independent suite in this sandbox: 192 passed and one GPU-visibility test skipped. No evidence-namespace residue remained.
- The independent quadrature/codebook tests passed, and the reported dimension-128 analytic values are reproduced by those FP64 oracles.
- The targeted four-bit Monte Carlo values reported above.
- No Task 8 validation report or Task 9 registered evidence/report exists in the current `HEAD`.
- The frozen/current test counts and the seven post-access additions.
- The direct overlap between plan-prescribed tests and frozen-suite tests.

### Not independently verified

- I could not reproduce the claimed 182 implementer-test passes because GPU access is blocked in this sandbox. With the pinned checkout supplied, the local run reached 169 passes, two CUDA-preflight-dependent failures, and one CUDA module skip; those outcomes reflect the unavailable GPU and are not evidence that the target GPU run failed.
- I did not execute or verify the author CUDA differential.
- I did not verify a registered one-million-pair result because none exists in the tree.
- I did not verify the actual pre-freeze prompt, complete material bundle, fresh-session status, or provider-side model identity because their hashes/records are absent.
- I inspected the timestamp proof structures but did not establish external Bitcoin anchoring for them.

## Final judgment on the proposal

Part (1) is wrong: the current evidence does not establish internal R1, and the independence deviation is neither fully disclosed nor limited to `CLAUDE.md`.

Part (2) proposes a useful action but gives it an unsound causal interpretation. Run the clean suite before R1 acceptance and describe it honestly as remediation plus prospective cross-model replication.

Part (3) is correct but incomplete. Nothing should describe the current run as a clean sealed-envelope result, and no cache-path claim may be made. In addition, the second implementation plan should not be authorized under the approved gate until the clean Task 8 checkpoint and the actual registered Task 9 R1 evidence pass.
