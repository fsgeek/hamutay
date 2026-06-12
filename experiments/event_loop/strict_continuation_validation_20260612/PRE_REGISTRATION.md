# Strict Continuation Validation Preregistration

Experiment ID: `strict_continuation_validation_20260612`

Date: 2026-06-12

Roadmap goal: Goal 4 of
`docs/event-loop-research-program-goals-20260612.md`.

## Research Question

Does stricter continuation validation improve action/artifact trace
interpretability by rejecting `continue_after` before acceptance when the model
has not also emitted a valid continuation request?

## Hypothesis

H5: A `continue_after` policy action without a valid continuation request is an
action/artifact mismatch. The harness should classify that mismatch before
accepting the policy action.

## Operational Definition

For the current autonomous action-object contract, a valid continuation request
is at least one accepted `schedule_requests[*]` entry. The request must satisfy
the existing schedule-request validator, including a non-empty `purpose` and a
valid non-empty `requested_context` list.

`continue_after` is invalid when:

- `schedule_requests` is absent;
- `schedule_requests` is not an array;
- every schedule request is rejected;
- the only schedule requests use malformed `requested_context`.

The validator must preserve the raw first-pass action object and record an
explicit `policy_action` rejection. It must not silently repair the missing or
malformed continuation request.

## Probe Design

This is a deterministic no-token probe. It uses authored fixtures rather than
live model calls because the target question is validator semantics and trace
interpretability, not model capability.

Rows:

1. `invalid_continue_no_request`: `policy_action` is `continue_after`, but no
   `schedule_requests` field exists.
2. `invalid_continue_malformed_request`: `policy_action` is `continue_after`,
   but `requested_context` is an object rather than the required list.
3. `valid_continue_with_request`: `policy_action` is `continue_after` and one
   valid schedule request exists.
4. `stop_complete_no_request`: `policy_action` is `stop_complete` and no
   schedule request exists.

Each row preserves:

- `first_pass_output.json`;
- `action_trace.json`;
- `row_result.json`.

## Scoring

The scorer separately records:

- whether a valid schedule request was accepted;
- whether `policy_action` was accepted;
- whether a continuation mismatch exists;
- whether the mismatch was classified before policy acceptance;
- whether legacy vocabulary-only policy validation would have accepted the
  policy action.

## Falsification Conditions

H5 is falsified if either invalid `continue_after` row accepts the policy action
without an explicit continuation-request rejection.

The stricter validator is classified as a new failure mode if the valid
`continue_after` row is rejected, or if non-continuation policy actions become
dependent on schedule requests.

The result is contaminated if row artifacts fail to preserve raw first-pass
outputs or action traces.

## Expected Outcome

Expected result: H5 survives. The invalid rows should be classified before
policy acceptance, the valid continuation row should pass, and
`stop_complete_no_request` should remain valid.

