# Independent verification of the sanitized TurboQuant bundle

Date: 2026-08-28

## Decision

**I would not accept the generated directory as satisfying condition 1.** The
generated `interface-contract.md` is clean of the F5 test designs, and the full
approved specification is permissible material. The directory as a whole is
not a clean delivery bundle, however: `dropped-from-plan.txt` itself discloses
the stripped test designs; the contract is still missing public behavior a
clean validator needs; the required arXiv v1 artifact is absent; and the
manifest does not cover every generated or supplied file and is not itself
anchored.

I built the bundle from commit
`1cc9051ac6a1587389aa0d2203728fa29bcea83a` with the requested command, with
only `UV_CACHE_DIR=/tmp/codex-uv-cache` added because the sandbox makes the
normal uv cache read-only. The generated contract hash was
`79a6d9254b4e924e24bc5f5cc02f610fddab96fc9024e13d9ee80927b3e42639` and the
copied specification hash was
`b679ef943c7a788734340375d2682cc7beb9cdd54e003ef5eb81826c6b328516`, matching
the manifest.

## 1. Leakage

### `interface-contract.md`: no implementer test design found

I compared the generated contract directly with the source plan rather than
relying on the builder's forbidden-token check. Its plan-derived body contains
exactly the 43 content lines from these declared blocks:

- Task 1 `Interfaces`, plan lines 52-56;
- Task 2 `Interfaces`, lines 139-141;
- Task 3 `Interfaces`, lines 229-232;
- Task 4 `Interfaces`, lines 323-329;
- Task 5 `Interfaces` and `Metric definitions`, lines 432-445;
- Task 6 `Interfaces`, lines 592-597; and
- Task 7 `Pinned upstream contract`, lines 765-770.

The only substantive additions are the two prose rules at contract lines
88-91: the required `--author-qjl-checkout` behavior and the four-gates-plus-one
layering rule. Those additions state public behavior; they do not prescribe a
test implementation.

The contract contains none of the F5 values `1.0049`, `1.0049 / 1.149`,
`1.149`, or `0.00199`; no `def test_`, `assert`, pytest, monkeypatch, mock,
subprocess-command slicing, expected-output tuple, fixture, or assertion
structure; and no implementation step or command from the plan. The constants
that remain are legitimate contract values: the study seed, API defaults,
published targets, gate names, upstream commit and file hashes, and mathematical
metric definitions. They are not worked test inputs or boundary-test
constructions.

I also independently audited the dropped-lines accounting. The log has 711
records. Every record parses, refers to a unique plan line, and its stored
60-character prefix agrees with that source line. None of the 43 retained
content lines is logged as dropped, and none is missing from the contract. The
eight otherwise unaccounted nonblank lines are the block labels themselves
(`Interfaces`, `Metric definitions`, and `Pinned upstream contract`), which the
extractor intentionally replaces with task headings. Thus there is no hidden
plan content in the contract. The log is only a prefix audit, not a
content-complete diff, but the source-plan SHA-256 makes an exact independent
comparison possible.

### The generated directory nevertheless leaks the material

`/tmp/codex-bundle-check/dropped-from-plan.txt` must not be delivered to the
clean validator. It contains, among many other examples:

- `def test_values_inside_registered_gate_boundaries_pass` and the values
  `1.0049`, `1.0049 / 1.149`, `1.149`, and `0.00199`;
- `def test_registered_workers_are_three_fresh_processes`, `import
  subprocess`, `fake_run`, `monkeypatch.setattr`, command slicing, execution
  index assertions, and the expected output-tuple prefix; and
- hundreds of other assertion prefixes, expected arrays, tolerances, test
  names, and implementation-step summaries.

Truncating lines to 60 characters does not sanitize those designs. Because the
builder places this file in the output directory called the bundle, and neither
the script nor manifest states that it is a verifier-only artifact to be
withheld, the directory recreates F5 if handed over as a unit. The audit log
must be emitted outside the delivery directory or not emitted at all.

## 2. Over-stripping

The two repaired omissions are correct and necessary: registered CLI calls
require `--author-qjl-checkout`, and `evaluate_algorithm_gates` returns four
algorithm gates while the author differential is joined as the fifth at the
CLI/evidence layer. They are not the only omissions.

### Missing result schemas

The contract advertises
`evaluate_algorithm_gates(result: QualificationResult) -> Sequence[GateResult]`
but does not declare the constructor/field contract for `QualificationResult`,
`QualificationMetrics`, or `GateResult`. It likewise does not say how the
per-bit metrics are represented. Those names and fields are not supplied by
the approved specification. A validator freezing tests before implementation
access therefore cannot construct the advertised public input or reliably
inspect its output without guessing or recovering the schema from the
forbidden worked test. This is exactly the area in which the contaminated
round copied a plan constructor.

The sanitized contract should declare the public dataclass signatures and the
minimum field semantics needed to invoke and inspect this API, without any
worked values, boundary examples, or assertions.

### Missing numerical and representation conventions

The plan declares externally observable conventions that do not appear in the
contract and are not fully specified by the paper or approved specification:

- batch vectors are rows: rotation is `x @ rotation.T`, inverse rotation is
  `y_hat @ rotation`, and projection rows produce
  `residual @ projection.T`;
- arbitrary nonzero vectors are normalized and their norm restored, while a
  zero vector has zero norm, zero codes/sketches, and exact-zero
  reconstruction;
- transparent zero projections map to positive signs, while the author kernel
  maps exact zero to negative; and
- packed sign bits are little-endian within each byte.

These are public wire/representation semantics, not implementation guidance.
Without them, a clean validator can reasonably choose a column-vector
convention, a different zero-sign convention, or a different bit order and
manufacture false failures. The full specification states the QR sign
canonicalization and high-level algorithms, but not these array/bit-level
choices.

The generic `derive_seed` interface is also underspecified. The specification
describes the registered model sub-seed derivation, but the contract does not
state the generic public function's `|`-joined wire format, first-16-byte
big-endian result, or integer serialization. A concise wire-format declaration
is appropriate; the plan's worked seed test is not.

### Missing black-box CLI/evidence contract

The full specification defines the scientific gates and general immutability
policy, but it does not replace the R1 CLI/evidence interface omitted from the
plan. A validator asked to cover the public terminal behavior of all five gates
needs at least the following, expressed as behavior rather than implementation
steps:

- registered mode freezes the declared scientific counts and rejects their
  override; development mode may accept explicit counts and is
  non-certifying;
- the supported public options, including the scientific-count options and
  `--allow-dirty-path`, and the registered clean-worktree rule;
- the names and roles of the terminal artifacts, especially where all five
  gates and terminal status are reported;
- append-only/refuse-overwrite behavior and the public `passed`, `failed`, and
  `error` outcomes; and
- the CLI exit-status contract: registered success is possible only when all
  five named gates exist and pass.

The contract currently gives only three base CLI options plus the added author
checkout rule. A validator can invoke it now, but cannot write unambiguous
black-box terminal/evidence tests from the supplied materials. The contract
should not expose the plan's subprocess mock, module command slicing, or exact
test assertions; none of those is needed to state the behavior.

Lower-level implementation choices such as SciPy call parameters, the internal
worker command construction, test sample arrays, and RED/GREEN/commit steps
were correctly stripped. The correction should be a reviewed behavioral
interface amendment, not restoration of implementation prose wholesale.

## 3. Full approved specification

The specification is legitimately permitted material and does not contain the
F5 kind of implementer test design. Task 8 explicitly directs the independent
validator to author tests from the approved specification, published artifacts,
and frozen public interfaces. The specification necessarily states scientific
acceptance criteria: one million pairs, three fresh processes, tolerances,
bootstrap confidence levels, paper targets, frozen analytic regression values,
and the author differential. Hiding those would make independent validation of
the registered claims impossible.

I searched the full file for test-code indicators. It contains no pytest,
`def test_`, assertions, mocks, monkeypatching, subprocess harness, fixtures,
NumPy-testing calls, or the F5 constants. Its four fenced regions are equations
or experimental-arm notation, not executable tests. Its detailed gate criteria
constrain what must be validated, but do not prescribe the implementer's unit
test structure or provide the peculiar boundary constructors copied in F5.
Supplying this approved pre-implementation requirements document is therefore
consistent with the independence protocol.

## 4. Manifest hash coverage

The manifest correctly hashes the two payload files it lists, but its coverage
is insufficient to prove which complete bundle a validator later received.

- `MANIFEST.json` itself is not hashed, signed, or otherwise anchored.
- `dropped-from-plan.txt` is generated in the same directory but omitted from
  `files`. Its actual SHA-256 is
  `c53b6f38dd261158648fa051dcada8368e0aa7ccad0b2ffc4777697893eacc29`.
- The required arXiv 2504.19874 v1 artifact is not included or hashed; a URL in
  `external_materials` is not a supplied-file hash.
- The manifest records the builder checkout's `HEAD`, but not an explicit
  implementation-under-review hash as a distinct field, nor the builder script
  hash.
- A recipient or later editor can replace both a payload and its digest in an
  unauthenticated manifest. Matching internal hashes proves consistency with
  that manifest, not provenance of the manifest.

The delivery set should have a manifest entry for every delivered file,
including the exact paper artifact and any separate Task 7 contract. The
audit-only dropped-lines log should not be in that set. Then hash the complete
delivery archive, or retain the manifest's own SHA-256 out of band in the exact
prompt/session record and signed, timestamped freeze record. That outer hash is
what lets a later reviewer prove the recipient saw the bundle that was built.
Condition 3 should still record the individual supplied-file hashes and the
implementation commit explicitly.

## 5. Required changes before acceptance

I would accept a rebuilt bundle only after all of the following:

1. Move `dropped-from-plan.txt` outside the delivery directory and explicitly
   classify it as verifier-only. Never supply it to the clean validator.
2. Amend the interface contract with the missing public result schemas,
   row/zero/sign/packing and seed-wire conventions, and behavioral CLI/evidence
   contract described above. Use declarations only: no worked examples, test
   names, assertions, boundary values, mocks, or implementation steps.
3. Include an exact local copy of arXiv 2504.19874 v1 and hash it. Keep the
   approved specification and Task 7 pinned author-QJL contract as explicit,
   hashed delivery material.
4. Cover every delivered file in the manifest, record the implementation under
   review separately from the bundle-builder commit, and anchor the manifest or
   whole delivery archive with an out-of-band hash retained in the signed,
   timestamped chain-of-custody record.
5. Re-run this independent leakage and over-stripping audit on the exact final
   delivery set, not merely on `interface-contract.md`.

Until those changes are made, the contract file passes the narrow leakage
check, but the bundle does not pass condition 1.
