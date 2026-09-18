# TurboQuant R1 clean validation remedy

Date: 2026-09-18. Status: in progress; **does not authorize registered R1 execution**.

This continues the remedy recorded in the blocked 2026-08-27 independent
validation report. Tony asked to finish that remedy on the way to qualifying
R1 and requested the newer Antigravity CLI (`agy`) for the third-family author.

## Materials and independence boundary

Implementation under review: `b9227ce4b94374fc26167fc1357e0e9cc145af66`.
At preparation, the numerical implementation and author CUDA adapter still
match that commit. Existing tests and earlier review findings are available
to the coordinating Codex session, **not** to the clean validation author.

The prior bundle audit had unresolved public-contract omissions. A separate
Codex reviewer checked the rebuilt bundle, then rechecked the additions:
constructor types/defaults, import locations, CUDA adapter public boundary,
and the distinction between complete and terminal-error artifact sets.
The re-review caught an incorrect output-path declaration in the coordinator's
first amendment; the adapter accepts a directory and writes fixed JSON/NPZ
filenames. That declaration was corrected before delivery.

Builder amendment: signed commit `3eaf0fb788558d6ea4c58d1e811be07c4ef29426`,
with OTS receipt committed at `828201a`. This is an OTS calendar submission,
not a claim of an already confirmed Bitcoin anchor.

The separate reader `/root/bundle_audit` approved the final materials and
transport. It checked all material hashes, the actual arXiv version inside
the PDF, exact correspondence of extracted paper text, and the absence of
implementer test names, worked cases, or mock constructs in the delivery.
Its report is verifier-only and is not supplied to the author.

| Artifact | SHA-256 |
| --- | --- |
| Public contract | `019459f97094f8ea72181045b1fc1bdb32e651f1457cec842a13ce283d8a13d0` |
| Final material manifest | `6148e5eaa9e21054a737168fb50ee2e8dd1db126840c7a36c64573407194333b` |
| Exact author prompt | `11877a62ba350133263d58e2dd1c05beb2c3d7b734cc9e0849177ceb3334a00b` |
| arXiv 2504.19874v1 PDF | `431eb13926e10491f5fbd0bebd0813c51bd6c1e884426a1500c5db640b2997ab` |

## Authoring transport

Fresh `agy --new-project` session, from an empty directory outside the
repository, with slash-command expansion disabled and sandbox enabled.
All permitted subject-matter input is inline: specification, public contract,
manifest, and the exact `pdftotext -layout` paper extraction. The original PDF
is retained. The complete prompt, NDJSON input, output schema, and hashes are
retained, not reconstructed from recollection.

The author is instructed to use no tools and return complete pytest file
contents as structured output. No implementation imports or executions are
allowed before the signed and timestamped suite freeze. The emitted event
stream will be checked for compliance, rather than taking the instruction as
proof that it was followed.

Requested CLI model: `gemini-3.1-pro-high`, effort high, present in the
live `agy models` catalog. The CLI initialization event reports that model
and conversation ID `6a8754d4-3d8f-421c-9d60-dfec89d7788a`. These are
transport metadata, not the author's self-identification; no stronger claim
about underlying model weights is made. The earlier transport-only probe
was a different conversation and is not resumed.

Working evidence directory (not yet the final archive):
`/home/tony/projects/hamutay/tmp/turboquant-remedy-20260918/`.

## Preliminary execution, not clean validation

The coordinator ran the implementer suite excluding the dedicated author-CUDA
module while clean authorship was pending. Result: 169 passed, 1 skipped,
1 failed in 73.81 seconds. That command omitted the declared CUDA_HOME/PATH
selection: a test expecting the missing-checkout error instead encountered
the earlier compiler-environment refusal. The output is preserved as
`implementer-cpu-first.txt`; it is not supplied to the author. A focused
rerun with the prescribed environment is recorded separately.

## Remaining work

### First clean attempt: retained, insufficient

Suite freeze: signed `11b06936b2834954923307a3fbcb6a570c0b8e5a`,
OTS receipt commit `fa32d68`. The event stream records no author tool calls.
The first CPU replay returned **13 passed, 3 failed, 2 deselected** in 90.39 s.
The two excluded tests were the dedicated CUDA check and the test that would
attempt registered execution before the Task 8 gate. They are not passes.
The unchanged suite is retained under the first session archive's
`frozen-tests/`; its original paths and bytes remain in the freeze commit.

Failures: arbitrary temporary output roots violate the repository-relative
namespace rule; a single synthetic run cannot establish three-process
determinism; and the sign-packing function accepts Boolean input, which the
public contract had omitted. Independent review also found vacuous refusal
assertions and missing verification of gate decisions and CUDA artifact
contents. Therefore passing only corrected versions of the three failing
cases would not establish Task 8.

Decision: retain this whole attempt and start a fresh authoring session with
the clarified public contract and a more explicit administrative coverage
remit. Supply no previous tests, replay output, or review-designed cases.
This is a new authored suite, not a claim that post-feedback additions were
present in the original sealed suite. Original implementation remains intact.

### First GPU customer

Lease `929aa26f-2c32-4dca-992a-ced812f87b09` failed to start pytest because
the coordinator passed an unquoted PATH containing spaces as an `env`
argument. This is a launch-command error, not a CUDA or orchestrator defect.
The scope exited before registration was confirmed; the supervisor returned
6, cleared its lease, and the heartbeat restarted Qwen's server.

Retry lease `0d1c0f0e-ed9b-4140-9419-ab15c42569d0` used an explicit Linux
PATH and a 15-minute workload timeout inside a renewing 30-minute lease.
The implementer's author-CUDA module returned **11 passed in 132.41 s**.
After release the lease was absent and Qwen's server was active, invocation
`e23b37a3f3a24a5a8b61f8db9489aab1`. No manual service stop/start or forced
release was needed. This verifies this bounded handoff, not all orchestration
failure cases. Logs are retained under the first session archive.

The earlier environment-only implementer failure passed its focused rerun
with CUDA_HOME/PATH selected: **1 passed in 3.19 s**.

### Still required

Second fresh Gemini 3.1 session: `b61645f0-622b-4bf5-9dd6-e8c135d46be4`.
Its prompt was independently audited and contained no first-attempt tests,
outcomes, or review text. The only emitted tool event was `finish`, carrying
structured output; there was no file access or command execution. The suite
was signed at `b5df0ae13f260137b01b5fd917eb7d5b0e270aba`, OTS `1ead2da`,
before replay: **20 passed, 4 failed in 3.54 s**. It too is archived unchanged.
Review found no real successful CUDA call and insufficient terminal gate
coverage. Its coverage prose was stronger than its assertions. It does not
satisfy Task 8 even independently of the four failures.

Remaining public-boundary ambiguities were clarified before another fresh
author: per-sample block-ID return shape, direct main return vs process exit,
CLI namespace enforcement vs the generic directory helper, and required
nonempty gate text fields. These are declarations, not worked cases.
The next author uses the live-catalog Gemini 3.8 Flash High model through
agy, with no previous attempt's tests or outcomes supplied.

The CUDA-active implementer plus old corroborating suites completed with
**379 passed, 1 skipped in 232.53 s**. The skip was the read-only nvidia-smi
availability check: the coordinator's explicit Linux PATH omitted
`/usr/lib/wsl/lib`. The next full run will include that directory; this run
alone is not the required no-unexpected-skips record. The CUDA differential
tests themselves executed. Lease: `76d80951-cfa9-455c-b668-1791b2122919`.

- Receive and retain the complete author output and check its access trace.
- Freeze the unchanged authored suite and complete provenance before replay.
- Run the frozen suite and preserve its first outcome before any repairs.
- Acquire the shared 4090 through the current main checkout's lease tool;
  verify acquisition, bounded workload, release, and return of Qwen's server.
- Complete CUDA-active implementer and independent validation with no
  unexpected skips; retain the old independent suite as corroboration.
- Resolve failures with attribution and separate signed amendments; never
  silently alter a frozen test or scientific gate.
- Produce a replacement Task 8 terminal report. Registered Task 9 and the
  later model/cache-path experiment remain gated on the required evidence.

### Third clean attempt and revised handoff

The Gemini 3.8 session `09e5150c-e7b2-4a1d-bf79-ee693eb93437` emitted no
tool steps. Its unchanged suite was signed at `7b73ee2`, timestamped at
`84a0dde`, before replay: **30 passed, 9 failed in 21.60 s**, no skips.
The full original output and generated development evidence are archived
in `2026-09-18-turboquant-clean-r3`. It has meaningful scientific core gate
checks but lacks successful fifth-gate incorporation; its standalone CUDA
case fails before actual execution. This attempt does not establish Task 8.

The coordinator's incomplete handoff and the author's guesses both
contributed. An independent review documented the complete observable
public evidence schemas and constructor constraints, including the public
author gate-conversion function. The declarative supplement is separately
reviewed and hashed; it contains no source bodies or worked test cases.
The next clean author receives no previous suite/outcome/review, and will
review its own draft against only the approved materials before final
pre-execution freeze. This changes the handoff process; it does not
retroactively improve the three sealed attempts. Numerical implementation
remains unchanged.
