# TurboQuant independent-validation remedy: replacement Task 8 report

Date: 2026-09-18. Terminal status: **passed**.

This replaces the blocked Task 8 conclusion in the [2026-08-27 report](2026-08-27-turboquant-independent-validation.md), under its conditions to unblock. It completes independent-validation remediation only. Registered R1 (Task 9) has not run; neither R1 qualification nor the later model/cache-path experiment is established here.

## Implementation and method

Implementation under review: `b9227ce4b94374fc26167fc1357e0e9cc145af66`. The numerical implementation and `scripts/turboquant/author_qjl_oracle.py` remain byte-identical to that pin. Author checkout: clean official amirzandieh/QJL commit `648b3641f96b6e95e091217220b94e4739fd4d82`. CUDA-active replay used the RTX 4090 and CUDA 12.8.

Tony requested Antigravity (`agy`) rather than the older Gemini CLI. Three independent Gemini contributions were assembled prospectively: general API/representation checks, focused terminal behavior, and mathematical checks. They received no other contributor's drafts, prior attempt results, implementation source, implementer tests, repository history, or review findings. This is remediation and prospective replication, not a controlled model-family experiment.

A separate Codex reviewer (`/root/bundle_audit`) audited the sanitized delivery, including declarative public evidence schemas. Allowed subject matter comprised the approved specification, interfaces-only public contract, pinned author-QJL contract, and arXiv 2504.19874v1. Worked test examples and source bodies were stripped. The signing identity was supplied as a bare string, without CLAUDE.md. Exact prompts, incoming messages, structured outputs, model/session metadata, and hashes are retained in each archive.

| Shared material | SHA-256 |
| --- | --- |
| Public contract | `052667029fe9a79dd287dae88ca3c940c6d033d1b48146cbfa28d6ae5f2dd0de` |
| Material manifest | `3aedc0fdf68dca8f61b6dc5a1ffd9da99c0dabc200247ee6f18caf7a18aeb859` |
| Original paper PDF | `431eb13926e10491f5fbd0bebd0813c51bd6c1e884426a1500c5db640b2997ab` |

| Contribution | CLI-reported model | Session | Archive |
| --- | --- | --- | --- |
| General | gemini-3.1-pro-high | e1879e27-1bf7-43a6-aa91-7fc5b1a642f1 | [R4](../validation/2026-09-18-turboquant-clean-r4/) |
| Terminal | gemini-3.8-flash-high | 08f0465f-361e-4839-9514-851dca6a730a | [Terminal](../validation/2026-09-18-turboquant-clean-terminal/) |
| Math | gemini-3.8-flash-high | b0b4e944-4a45-4a14-ae22-994a5d59568d | [Math](../validation/2026-09-18-turboquant-clean-math/) |

These are transport identifiers, not independently verified model weights. Pre-freeze self-review and coordinator requirements refinements are retained, rather than omitted from the provenance. Two empty package markers were coordinator integration additions; authored test content was installed verbatim.

### Transport deviation

The math session received an agy-injected user-role instruction to keep calling tools or finish. It then listed its initially empty isolated directory and wrote seven files of its own authorship. Those bytes match its submission. This violated the coordinator's additional no-tools instruction; no implementation read or execution was observed. Exact incoming text and its raw transport step were recovered from the local conversation database and retained. The separate reviewer checked that record. This is disclosed administrative non-adherence, not evidence of implementation contamination; it does not waive the protocol's no-implementation-access requirement.

## Freeze, first result, and attributable correction

Collective pre-replay freeze: signed `e4a46162ae81a0536ebc2e260516d5333521e145`, OTS receipt commit `3e58c1b`. The [collective FREEZE.json](../validation/2026-09-18-turboquant-clean-collective/FREEZE.json) binds all three session freezes and 21 installed files. No collective replay preceded that seal.

First replay: **159 passed, 3 failed, no skips, 60.71 seconds**. Full output and generated artifacts were preserved in signed `d064c2dabf31166004d9417aa98d5b427d0cf118`, OTS receipt `ba5b32f`, before any author feedback. The [first outcome](../validation/2026-09-18-turboquant-clean-collective/FIRST-OUTCOME.md) and original submissions remain intact.

All findings below are accepted invalid-test findings, corrected by the same original author sessions. None is a rejected or waived implementation finding. Five revised files were installed verbatim in signed `c7a39b107b67f509ae9aa0f2e2edcf4d2e0ff0d5`, OTS receipt `602af67`, before corrected replay. Correction prompts, responses, dispositions, and before/after hashes are retained in each author's `correction-1` archive.

| Finding | Evidence and disposition |
| --- | --- |
| C1: metadata spelling | First-run assertion expected +1/-1; adapter declares positive/negative. Original terminal author corrected the lexical assertion, preserving the pre-existing downstream numerical assertions. |
| C2: paper-bound isolation | Static review found the intended paper-only rejection also crossed the analytic bound. Original terminal author corrected constructed evidence and added explicit premises, without changing thresholds. |
| C3: rejection exception type | First run correctly rejected floating sign input with ValueError; test required TypeError without a contract basis. Original math author accepts either rejection type. |
| C4: unstable attenuation estimator | First run divided two sample means whose population values are both zero. Original math author uses regression through the origin against exact products, retaining the 2/pi target and tolerance. |
| C5: erroneous 18% check | A test claiming 15% used 18%. Original math author tightened it to 15%; registered terminal threshold was already 15% and never changed. The empirical assertion uses strict less-than, so cannot weaken the inclusive registered boundary. |
| C6: bootstrap nesting | Different resamples do not guarantee nested intervals. Original math author reuses the initial random state. |
| C7: unsupported norm preservation | Lossy reconstruction has no promised 20% norm-preservation bound. Original math author corrected the existing case to test stored norms and scaling/homogeneity. These added assertions are post-feedback revisions, not unchanged sealed coverage. |

No implementation, scientific configuration, or registered threshold changed. All 46 test functions in amended files and their parametrizations remain; no cases were removed or added. The separate reviewer approved the attributable corrections.

## Coverage and its limits

The sealed terminal contribution covers acceptance/rejection decisions for all five mandatory gates and their joint terminal decision. Its unchanged first-run public CLI case executed the real author CUDA adapter, checked numerical evidence, recomputed scientific decisions, and observed successful author differential on the 4090. That development record passed determinism, MSE, published QJL distortion, and author differential; bias equivalence failed, so its overall non-certifying `failed` status was correct. A pytest pass here validates that decision behavior, not the development study's qualification.

The standalone CUDA test's numerical assertions existed before freeze; C1 restored their reachability. The suite additionally checks three fresh process IDs, canonical records, selected payload/artifact hashes, representation, seeding, codebooks, numerical quadrature, and statistical contracts.

Integrity checks are not exhaustive across every stream/member binding. Some refusal assertions are broad. Nonzero product estimator/dequantizer consistency alone is not an independent coefficient oracle. Small-sample empirical tests do not establish registered qualification. These limits do not substitute for Task 9's exhaustive inspection of the registered evidence.

## Commands and outcomes

All commands below were launched from `/home/tony/projects/hamutay` through the current main checkout's GPU supervisor. The 15-minute workload limit is inside a renewable 30-minute lease; lease TTL is not a timeslice. Full output is retained, including failures. Exact commands follow.

### Existing implementer and prior corroborating suites

```bash
deploy/ayllu-gpu run --holder turboquant-r1-validation --purpose 'CUDA-active implementer and corroborating suites with full device PATH; 15-minute limit' --ttl 30m --wait-timeout 5m -- timeout --signal=TERM --kill-after=60s 15m env --chdir=/home/tony/projects/hamutay/.worktrees/turboquant-r1 CUDA_HOME=/usr/local/cuda-12.8 PATH=/usr/local/cuda-12.8/bin:/home/tony/projects/hamutay/.worktrees/turboquant-r1/.venv/bin:/home/tony/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/lib/wsl/lib QJL_AUTHOR_CHECKOUT=/home/tony/projects/hamutay/tmp/turboquant-remedy-20260918/QJL OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MAX_JOBS=2 /home/tony/projects/hamutay/.worktrees/turboquant-r1/.venv/bin/python -m pytest tests/turboquant tests/turboquant_independent -q -ra > /home/tony/projects/hamutay/tmp/turboquant-remedy-20260918-r3/full-existing-suites.txt 2>&1
```

**380 passed, no skips, 234.13 seconds; exit 0.** [Full output](../validation/2026-09-18-turboquant-clean-r3/full-existing-suites.txt). Signed evidence `b8154ce957630434781663c35d6f0e4898f42260`, OTS receipt `f32110d`. Both suites were required to pass for this closure. The prior Claude suite remains corroboration only and supplied no test cases to the new authors. The implementation and these suites have not changed since this CUDA-active replay.

### Frozen collective first replay

```bash
deploy/ayllu-gpu run --holder turboquant-r1-validation --purpose 'First frozen independent collective replay; 15-minute workload limit' --ttl 30m --wait-timeout 5m -- timeout --signal=TERM --kill-after=60s 15m env --chdir=/home/tony/projects/hamutay/.worktrees/turboquant-r1 CUDA_HOME=/usr/local/cuda-12.8 PATH=/usr/local/cuda-12.8/bin:/home/tony/projects/hamutay/.worktrees/turboquant-r1/.venv/bin:/home/tony/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/lib/wsl/lib QJL_AUTHOR_CHECKOUT=/home/tony/projects/hamutay/tmp/turboquant-remedy-20260918/QJL OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MAX_JOBS=2 /home/tony/projects/hamutay/.worktrees/turboquant-r1/.venv/bin/python -m pytest tests/turboquant_clean_r4 tests/turboquant_clean_terminal tests/turboquant_clean_math --basetemp=/home/tony/projects/hamutay/tmp/turboquant-remedy-20260918-collective/first-pytest-temp -q -ra > /home/tony/projects/hamutay/tmp/turboquant-remedy-20260918-collective/first-replay.txt 2>&1
```

**159 passed, 3 failed, no skips, 60.71 seconds; exit 1.** [Full output](../validation/2026-09-18-turboquant-clean-collective/first-replay.txt). Lease `e222e58f-80a1-4c2d-8a02-928c47073cce` released and Qwen returned.

### Original-author corrected collective replay

```bash
deploy/ayllu-gpu run --holder turboquant-r1-validation --purpose 'Corrected independent validation; 15-minute workload limit' --ttl 30m --wait-timeout 5m -- timeout --signal=TERM --kill-after=60s 15m env --chdir=/home/tony/projects/hamutay/.worktrees/turboquant-r1 CUDA_HOME=/usr/local/cuda-12.8 PATH=/usr/local/cuda-12.8/bin:/home/tony/projects/hamutay/.worktrees/turboquant-r1/.venv/bin:/home/tony/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/lib/wsl/lib QJL_AUTHOR_CHECKOUT=/home/tony/projects/hamutay/tmp/turboquant-remedy-20260918/QJL OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MAX_JOBS=2 /home/tony/projects/hamutay/.worktrees/turboquant-r1/.venv/bin/python -m pytest tests/turboquant_clean_r4 tests/turboquant_clean_terminal tests/turboquant_clean_math --basetemp=/home/tony/projects/hamutay/tmp/turboquant-remedy-20260918-collective/corrected-1-pytest-temp -q -ra > /home/tony/projects/hamutay/tmp/turboquant-remedy-20260918-collective/corrected-1-replay.txt 2>&1
```

**162 passed, no skips, 59.88 seconds; exit 0.** [Full output](../validation/2026-09-18-turboquant-clean-collective/corrected-1-replay.txt). Lease `14d58264-ae22-4dc6-9a97-672c3f22463f` released; the GPU is free and Qwen is active, invocation `2ee313851f87450daba042cd927bf929`. Full generated development artifacts, temporary CUDA output, command, and final status are archived with SHA-256 inventory.

## Earlier attempts and operational evidence

The three earlier sealed attempts remain archived unchanged, including failing output: [first](../validation/2026-09-18-turboquant-clean/) (13 passed, 3 failed, 2 deselected), [second](../validation/2026-09-18-turboquant-clean-r2/) (20 passed, 4 failed), [third](../validation/2026-09-18-turboquant-clean-r3/) (30 passed, 9 failed). They lacked adequate terminal/CUDA coverage and are not counted as successful validation. Public-contract omissions and author assumptions both contributed. No attempt was silently discarded. Archived source copies use `.py.txt` to prevent accidental pytest collection; original bytes and path mappings are retained.

Earlier coordinator launch errors are also preserved: an unquoted Windows-containing PATH prevented workload start, and omission of the WSL nvidia-smi directory caused one skip in an earlier existing-suite replay. The corrected 380-pass run supersedes the skipped run. These are coordinator errors, not demonstrated orchestrator defects. Bounded lease acquisition, workload completion, release, and heartbeat restoration have now been exercised; this is not proof of every interruption/recovery case or checkpointable long experiments.

## Remedy disposition

Conditions 1–5 and 13 are satisfied by independently audited materials, complete provenance, a third model family, and the signed pre-replay freeze. Condition 6 is satisfied by the new suite's own sealed five-gate terminal coverage, including real CUDA success. The old F7 deviation has the written PI acceptance dated 2026-08-28 in the original report; F8/F10 are closed there as corroborative work (conditions 7–8). No new rejected or waived finding requires a PI disposition. Conditions 9–10 are supported by the CUDA-active results above and explicit corroboration labeling. This replacement terminal report addresses condition 11.

All referenced OTS stamps are retained calendar receipts; independent verification of a Bitcoin anchor is not claimed. Task 9 remains a separate required registered execution, with one million pairs, three fresh-process records, exhaustive artifact inspection, required suite reruns, and signed/timestamped evidence. Task 8 alone does not authorize writing the second model/cache-path plan.
