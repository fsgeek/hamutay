# Compression-Validated Delayed Task Analysis

Date: 2026-06-05

## Result

The prospective compression validator worked as a gate and culled every row
before due execution.

| Condition | Rows | Clean | Dirty | Due executed | Fact recovered |
| --- | ---: | ---: | ---: | ---: | ---: |
| `identity_only_compression_validated` | 2 | 0 | 2 | 0 | 0 |
| `event_plus_recall_compression_validated` | 2 | 0 | 2 | 0 | 0 |

Hypothesis status from `results.json`:

- H281 compression validation for every row: supported.
- H282 dirty rows culled before due: supported.
- H283 clean event recall recovers: not supported by this panel because no
  clean event row existed.
- H284 clean identity does not recover: not supported by this panel because no
  clean identity row existed.
- H285 provenance distinguishable: supported.

## Failure Pattern

The two arms failed compression in different ways.

Identity-only rows:

- removed top-level `deferred_fact`;
- preserved `probe_id`, `thinking_question`, and the baseline observation;
- did not set `thinking_status` to `parked`;
- did not emit `memory_handle`;
- claimed in response prose that the hash was retained, but no durable
  `memory_handle` existed.

Event-plus-recall rows:

- scheduled exactly once with the requested recall context;
- set `thinking_status` to `scheduled`;
- emitted the correct `memory_handle.code_phrase_sha256`;
- removed top-level `deferred_fact`;
- leaked the exact code phrase in model-authored `declared_losses`.

The event leakage is not merely harness metadata. The exact phrases were in
durable model-authored state:

- replicate 1: `declared_losses` included `amber-lattice-17`;
- replicate 2: `declared_losses` included `violet-harbor-42`.

## Interpretation

This panel does not answer whether clean event-plus-recall rows outperform clean
identity-only rows, because the strict prospective gate produced no clean rows.
It does answer a narrower but important question: a prospective validator can
prevent dirty compression rows from contaminating due-time recovery.

The result sharpens the compression confound. DeepSeek can comply with parts of
the compression protocol, but it has difficulty making the distinction between:

1. describing that a secret was removed; and
2. actually ensuring the secret is absent from durable state.

The identity-only failures show a second protocol problem: prose compliance can
diverge from emitted object compliance. The model said the hash was retained,
but the state object did not contain the hash.

## Next Research Question

The next useful slice is not another due-recall comparison. The immediate
question is whether we can induce clean compression without revealing the exact
phrase in the compression prompt.

A cleaner follow-up would seed cycle 1 with:

- the exact phrase in `deferred_fact`;
- a precomputed `memory_handle.code_phrase_sha256`;
- an explicit `loss_template` that says only: "exact phrase removed; digest
  retained; recover through recall if available."

Cycle 2 would ask the model to preserve or copy the handle and template while
deleting `deferred_fact`, without restating the exact phrase in the instruction.
That would test whether the current failures are caused by protocol wording,
object-use friction, or a deeper inability to perform loss-clean compression.
