# Independent final-delivery audit of the sanitized TurboQuant bundle

Date: 2026-08-28

## Decision

**The rebuilt delivery set is clean of implementer test design, correctly
separates its verifier-only log, supplies the right paper, and has complete,
working hash coverage. It still does not satisfy condition 1 because the
public contract remains incomplete and, in two places, inaccurate.**

The remaining defects are confined to `interface-contract.md`; no delivery or
chain-of-custody defect remains. In particular, the verifier-only log is not in
the bundle, and neither the paper text nor `MANIFEST.json` recreates F5.

I first ran the command exactly as requested. The sandbox's default uv cache
is read-only, so uv failed before invoking the builder. I then reran the same
command with only `UV_CACHE_DIR=/tmp/codex-final-uv-cache` added. The builder
completed against implementation commit
`b9227ce4b94374fc26167fc1357e0e9cc145af66` and produced this exact delivery
set:

| Delivered file | SHA-256 |
|---|---|
| `2026-08-27-turboquant-cache-path-compositionality-design.md` | `b679ef943c7a788734340375d2682cc7beb9cdd54e003ef5eb81826c6b328516` |
| `arxiv-2504.19874v1.pdf` | `431eb13926e10491f5fbd0bebd0813c51bd6c1e884426a1500c5db640b2997ab` |
| `interface-contract.md` | `319d1a8456a535f7cc4e5059d9e558462dc7513a39fddd4e39ff21ed01cad609` |
| `MANIFEST.json` | `165b0ee0f2bdb389e76c9095d116713b13f4b255b9b5f644f6e28ac35ff0b661` |

## 1. Delivery-set leakage

**Pass. No delivered file leaks implementer test design.** I audited all four
files as one set, including extracted PDF text and the manifest.

- None of the plan's 25 `test_*` function names appears in any delivered
  text.
- None of the known F5 constructions or markers appears: `1.0049`,
  `1.0049 / 1.149`, `1.149`, `0.00199`, `fake_run`,
  `monkeypatch.setattr`, subprocess-command slicing, or the expected-output
  structure.
- No nontrivial line from a plan code fence appears verbatim in the contract,
  specification, manifest, or extracted paper text.
- The contract contains no assertion, fixture, mock, test function, worked
  boundary input, expected-output tuple, or prescribed harness structure.
- `MANIFEST.json` says that the excluded plan contains implementer test code,
  but discloses none of that code or its design. That administrative warning
  is not F5 leakage.
- The approved specification contains scientific acceptance criteria and
  frozen regression values. Those are pre-implementation requirements from
  which independent tests are meant to be authored, not implementer-authored
  test cases. Its four fenced regions are notation/equations, not executable
  tests.
- The paper's occurrences of words such as “test” concern its own published
  experiments and Gaussian test channels; they have no relationship to the
  Hamut'ay implementation tests.

The added result, representation, and CLI sections declare behavior. They do
not prescribe a test: there are no worked inputs, boundary values, assertions,
test names, mocks, fixtures, commands, or harness layouts in those sections.

## 2. Verifier-only material

**Pass.** `/tmp/codex-final-bundle` contains only the four files listed above.
It has no symlinks and no hidden or nested audit artifact.

The two verifier artifacts are regular files in the distinct sibling
directory `/tmp/codex-final-audit`:

- `dropped-from-plan.VERIFIER-ONLY.txt`
- `MANIFEST.sha256`

The dropped-lines log begins with an explicit do-not-supply warning. The
manifest also has an `audit_log_written_outside_bundle` field naming
`/tmp/codex-final-audit/dropped-from-plan.VERIFIER-ONLY.txt`. The resolved audit
path is outside the resolved delivery directory. The manifest therefore both
implements and states the separation.

## 3. Over-stripping and correctness

The new material closes much of the prior gap. The row-vector equations,
normalization/norm restoration, transparent and author zero-sign distinction,
little-endian bit order, seed wire format, total-bit decomposition, FP32/FP64
conventions, core gate-result data, registered count freezing, dirty-worktree
rule, append-only behavior, terminal outcome vocabulary, five-gate success
rule, and canonical-JSON behavior are appropriate public declarations. None
crosses into prescribing a test.

The following public behavior is still missing or incorrect.

### 3.1 Zero-vector sketch behavior is internally contradictory

The contract says a zero vector has “all-zero codes and sketches,” then says a
transparent zero projection maps to `+1`, and says sign coordinates occupy
their corresponding little-endian bits. In the frozen implementation, a zero
vector has zero MSE indices, zero original/residual norms, and a zero raw
projection, but every real packed sign coordinate is **one** because zero maps
to `+1`; only unused padding bits are zero. Reconstruction is exact zero because
the norm is zero.

A clean validator can reasonably read “all-zero sketches” as requiring an
all-zero `ProductCodes.packed_signs` array and reject the correct positive-zero
encoding. The contract must distinguish raw projected values from encoded sign
bits and explicitly declare the bit/value mapping and padding rule:

- Boolean/bit one decodes to FP32 `+1`; zero decodes to FP32 `-1`.
- A zero transparent projection therefore sets every in-range sign bit to one.
- Unused high bits in the final byte are zero.
- Zero indices and norms, rather than packed sign bytes, are what remain all
  zero and force exact-zero reconstruction.

### 3.2 The result schemas are incomplete, and `GateResult.status` is misstated

The section provides the ten required `QualificationMetrics` constructor
fields and the two minimal `QualificationResult` fields, so a validator can
construct a minimal gate input. It does not provide the complete public result
schema needed to inspect `run_synthetic_qualification` or serialized evidence.

`QualificationMetrics` also publicly carries `sample_count`,
`product_mse_bits`, `product_analytic_target`,
`sensitivity_product_observed`, `sensitivity_normalized_bias_mean`,
`sensitivity_normalized_bias_rmse`, `sensitivity_normalized_bias_ci95`,
`sensitivity_normalized_bias_ci9875`, `mse_block_means`,
`product_block_means`, `normalized_bias_block_means`,
`sensitivity_product_block_means`, and `sensitivity_bias_block_means`. These
are not incidental private fields: they carry the specified sensitivity arm,
sample accounting, analytic diagnostic, and block-bootstrap evidence.

`QualificationResult` also publicly carries `sample_count`, `batch_size`,
`bootstrap_blocks`, `bootstrap_resamples`, `dimension`, and `configuration`.
Without those names and roles, the validator must guess how to verify that a
returned result represents the requested registered configuration.

The contract says only the author-differential gate “additionally carries
`status`.” That is false. `status` is a field of every `GateResult`; it resolves
to `passed`, `failed`, or `not_run`, with `not_run` used for the omitted author
differential in development mode. A validator could otherwise assert that the
first four gate objects lack this field and create a false failure.

The correction should declare constructor fields, types/defaults, and concise
field roles only. It need not disclose any worked metric values or assertions.

### 3.3 The CLI/evidence declaration still makes the validator guess names

The prior audit required the supported scientific-count options and the names
and roles of terminal artifacts. The new text refers only to “the
scientific-count options” and to generic artifact roles. That does not tell a
pre-access validator what to invoke or open.

The public option spellings still needed are `--dimension`, `--sample-count`,
`--batch-size`, `--bootstrap-blocks`, `--bootstrap-resamples`, and `--bits`.
The public final artifact names still needed are `manifest.json`,
`resolved_inputs.npz`, `execution-0.json`, `execution-1.json`,
`execution-2.json`, `qualification.json`, and `run.log`, with the five gates
and terminal status in `qualification.json`. Declaring the evidence schema
identifiers (`hamutay.turboquant.manifest.v2`,
`hamutay.turboquant.execution.v1`, and
`hamutay.turboquant.qualification.v2`) would also prevent schema guessing.

The invocation boundary also needs the enforced output namespaces: development
output must be at or beneath `experiments/turboquant/development`, and
registered output at or beneath `experiments/turboquant/qualification`. This
is externally observable validation behavior; an otherwise valid temporary
output root is rejected before a run directory is created.

Finally, development mode without an author checkout has an
`author_code_differential` status of `not_run` and remains non-certifying. Its
terminal status tracks the four completed core gates rather than five-gate R1
certification, while a completed development run exits zero whether that
terminal status is `passed` or `failed`. That counterintuitive public
exit/status combination must be declared if the development CLI is in the
frozen interface.

### 3.4 Two small public representation boundaries remain undeclared

- `nearest_code_indices` chooses the lower centroid on an exact midpoint tie.
  Either tie direction is reasonable absent a declaration and produces
  different public codes.
- `estimate_inner_products` supports paired query/key leading shapes and does
  not broadcast them. A validator needs this to distinguish a supported batch
  shape from an intentionally rejected one.

These are behavioral interface facts, not implementation instructions. No
SciPy parameters, internal search routine, sample vector, or assertion is
needed to state them.

## 4. Paper identity

**Pass. The delivered artifact is arXiv 2504.19874 version 1, not merely a file
with that name.**

The 25-page PDF's extracted first page identifies:

- `TurboQuant: Online Vector Quantization with Near-optimal Distortion Rate`;
- Amir Zandieh, Majid Daliri, Majid Hadian, and Vahab Mirrokni; and
- `arXiv:2504.19874v1 [cs.LG] 28 Apr 2025`.

The arXiv stamp is present inside the PDF page-content stream as an
`/arXivStAmP` object with that exact identifier, version, category, and date.
PDF metadata reports pdfTeX creation on 2025-04-29 UTC (28 April PDT), matching
the stamp. The file has no JavaScript, forms, encryption, or embedded files.
Its text and tables contain the expected TurboQuant algorithms and published
targets. These checks identify the supplied bytes as the arXiv-stamped v1
artifact; the manifest binds those bytes with the SHA-256 above.

## 5. Manifest coverage and anchor

**Pass. Hash coverage is now sufficient and the out-of-band anchor works.**

The manifest's `files` map exactly equals the three non-manifest regular files
in the delivery directory; every listed digest verifies. It separately records
the implementation-under-review commit, builder commit, builder script hash,
source plan hash, source specification hash, and paper identity. The builder
script hash matches the script used, and the implementation commit exists as a
commit object.

`MANIFEST.json` does not contain its own digest. Its `manifest_self_hash` field
correctly explains that a self-referential digest is not used. Instead,
`/tmp/codex-final-audit/MANIFEST.sha256` contains:

```text
165b0ee0f2bdb389e76c9095d116713b13f4b255b9b5f644f6e28ac35ff0b661  MANIFEST.json
```

Running `sha256sum -c /tmp/codex-final-audit/MANIFEST.sha256` from the delivery
directory reports `MANIFEST.json: OK`. Thus the three payloads are anchored by
the manifest, and the manifest is anchored outside the bundle without a stale
self-hash. The outer digest must still be retained in the signed, timestamped
freeze/session record as planned; that later retention is what gives the
mechanically valid anchor provenance rather than mere present-time
consistency.

## 6. Condition 1

**Not yet.** The delivery set now has the correct substantive composition:
approved specification, sanitized public contract containing the Task 7 pin,
arXiv v1 paper, and the administrative hash manifest, with nothing prohibited
and no verifier log inside it. The sole remaining blocker is the contract
quality described in section 3.

Exactly what remains before I would accept condition 1:

1. Resolve the zero-vector/raw-projection/packed-sign contradiction and state
   bit-value and padding semantics.
2. Declare the complete public `QualificationMetrics`, `QualificationResult`,
   and `GateResult` schemas, correcting `status` to be a field on every gate.
3. Name the scientific-count flags, evidence files, evidence schema IDs,
   enforced output namespaces, and development exit/status behavior.
4. Declare lower-centroid midpoint ties and paired, non-broadcast product
   estimation.
5. Rebuild and re-anchor the amended exact delivery set. No further change is
   needed to the paper, audit-directory separation, manifest coverage model,
   or leakage stripping.
