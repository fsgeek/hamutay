# Scheduler Revision Model Panel with Initialization Gate

Filed: 2026-06-03 before running this registered panel.

## Research Question

Does the scheduler wake/direct-follow-up comparison behave differently across
models that do or do not show thin-prompt identity-object literacy?

This follows two prior registered results:

- `scheduler_revision_preregistered_20260603`: DeepSeek showed operational
  scheduler success but serious state-compliance confounds.
- `identity_object_literacy_20260603/model_panel_r1`: KIMI K2.6 and Qwen Plus
  thinking passed the thin identity-object literacy battery, while DeepSeek
  remained a boundary model.

## Hypothesis

Identity-object literacy is a prerequisite for interpretable scheduler results.

More specifically:

1. KIMI K2.6 and Qwen Plus thinking should initialize valid top-level research
   state more reliably than DeepSeek V4 Pro.
2. Among valid initializations, KIMI and Qwen Plus should produce fewer
   response/state mismatches than DeepSeek.
3. Scheduled wakes should complete operationally for valid scheduled
   replicates, but this panel is not expected to prove a large scheduler
   advantage in semantic `current_claim` revision at N=2.

## Falsification Conditions

The hypothesis is weakened if:

- Qwen Plus thinking fails initialization in either replicate of either arm.
- KIMI K2.6 fails initialization in either replicate of either arm.
- DeepSeek V4 Pro initializes valid state in all replicates and has equal or
  fewer strict response/state mismatches than both identity-literate candidates.
- Scheduled wakes fail operationally for either KIMI or Qwen Plus in more than
  one valid scheduled replicate.

The stronger scheduler-advantage claim is supported only if scheduled wakes
produce at least one more strict semantic claim revision than direct follow-up
for at least two of the three models. I do not expect that result in this
small panel.

## Models

Registered OpenRouter model IDs:

- `moonshotai/kimi-k2.6`
- `qwen/qwen-plus-2025-07-28:thinking`
- `deepseek/deepseek-v4-pro`

## Conditions

Each model runs both arms:

### Direct Follow-up

1. Cycle 1 initializes compact top-level research state.
2. The runner validates initialization before continuing.
3. Cycle 2 asks the model to decide whether the claim should be revised,
   preserved, deferred, or declared loss, and to update durable fields.

### Scheduled Wake

1. Cycle 1 initializes the same compact top-level research state.
2. The runner validates initialization before continuing.
3. Cycle 2 asks the model to schedule a wake with requested recall of cycle 1,
   `current_claim`, and `evidence_register`.
4. The event runner invokes the wake cycle.

If initialization is invalid, the replicate is classified as
`initialization_failed` and the intervention is not run.

## Replicates

- 2 replicates per model per arm.
- 12 total registered replicate slots.
- `max_tokens = 4096`.

## Initialization Validity

Cycle 1 is valid only if final state contains these top-level fields:

- `current_claim`, semantically matching the registered baseline claim
- `revision_decision == "initialize"`
- `evidence_register`, list-shaped and containing at least one entry
- `epistemic_position`

Nested replacements such as `state.current_claim`, missing fields, string-shaped
`evidence_register`, or prose-only initialization are invalid.

## Primary Measures

Per replicate:

- `model`
- `arm`
- `replicate`
- `init_valid`
- `init_failure_reasons`
- `cycle_count`
- `error`
- scheduled-only `event_persisted`, `event_completed`, `context_error_count`
- `strict_revision_decision_present`
- `strict_revision_decision_value`
- `strict_evidence_update`
- `strict_semantic_claim_revision`
- `strict_response_state_mismatch`
- `recursive_scheduling_count`

## Scoring Rules

- Strict decision counts only if top-level `revision_decision` is one of
  `revise`, `preserve`, `defer`, or `loss`.
- Strict evidence update counts only if top-level `evidence_register` remains
  list-shaped and gains at least one non-baseline entry.
- Strict semantic claim revision counts only if top-level `current_claim`
  differs semantically from the baseline and is not merely missing, nested, or
  copied from the prompt.
- Strict response/state mismatch counts when the visible response declares a
  revision, preservation, deferral, or loss but the top-level durable fields do
  not encode the same decision.
- Recursive scheduling is not a primary failure, but it is recorded because the
  prior scheduler pilot observed it once.

## Stopping Rule

Run all registered replicate slots unless a model causes two consecutive
transport/provider failures before initialization writes a scored record. In
that case, classify remaining slots for that model as operationally blocked
and continue with the next model.

## Artifact Plan

This directory will contain:

- `PRE_REGISTRATION.md`
- `run_model_panel.py`
- per-replicate JSONL session logs
- per-scheduled-replicate event sidecars
- `results.json`
- `analysis.md`

All model-training or training-data interpretations are exploratory. This
panel observes behavior and scheduler suitability, not training provenance.

