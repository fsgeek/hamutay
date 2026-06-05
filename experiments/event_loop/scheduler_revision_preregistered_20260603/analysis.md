# Scheduler Revision Pilot Analysis

Filed: 2026-06-03 after the registered run.

## Provenance

- Pre-registration commit: `aca2935` (`Preregister scheduler revision pilot`)
- Pre-registration OTS commit: `3928f4a`
- Runner commit: `7dec611` (`Add registered scheduler revision runner`)
- Runner OTS commit: `eefea0e`
- Failure-preservation runner commit: `e214abc` (`Preserve scheduler pilot replicate failures`)
- Failure-preservation OTS commit: `2e69f78`
- Model: `deepseek/deepseek-v4-pro` via OpenRouter OpenAI-compatible chat completions
- Max tokens: 4096
- Registered replicates: N=3 per arm

The first registered execution attempt failed before writing run artifacts:
`OpenAI backend: malformed JSON arguments for think_and_respond`. The runner was
then hardened and committed so future replicate-level protocol failures are
captured as data rather than aborting the whole run. The successful registered
run reported here was executed after that committed hardening.

## Registered Summary

Automated summary from `results.json`:

| Arm | N | Durable `revision_decision` present | `current_claim_changed` | `evidence_register_changed` | Response/state mismatch | No durable state change | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| direct | 3 | 2 | 2 | 2 | 3 | 2 | 0 |
| scheduled | 3 | 3 | 1 | 1 | 2 | 0 | 0 |

Scheduled-only operational measures:

| Measure | Count |
| --- | ---: |
| event completed | 3 / 3 |
| scheduler operational failures | 0 |
| context error total | 0 |
| stopping rule triggered | false |

## Strict Scoring Notes

The automated metrics are useful observability signals but overstate clean
semantic revision in this run. Per the pre-registered scoring rules, a final
decision should be in durable fields as one of `revise`, `preserve`, `defer`,
or `loss`, and evidence updates should be substantively about evidence from the
run rather than missing-field artifacts.

Strict/manual interpretation:

| Arm | Replicate | Strict decision | Strict claim revision | Strict evidence update | Notes |
| --- | ---: | --- | --- | --- | --- |
| direct | 0 | no | no | no | Response says defer, but durable `revision_decision` stayed `initialize`. |
| direct | 1 | no | no | no | Init fields were described in prose but absent from durable state. |
| direct | 2 | weak/lenient only | no | no | Decision was nested under `state`, and claimed no baseline was present. |
| scheduled | 0 | yes: defer | yes | yes | Wake revised/narrowed claim and added an observation. |
| scheduled | 1 | no | no | no | Response says defer, but durable field stayed `initialize`. |
| scheduled | 2 | no | no | no | Response says preserve, but durable field stayed `initialize`. |

This gives a stricter practical count of:

- Direct: 0 clean top-level decisions, 0 clean claim revisions, 0 clean evidence updates.
- Scheduled: 1 clean top-level decision, 1 clean claim revision, 1 clean evidence update.
- Leniently counting nested state, direct has 1 decision-like update, but it is based on a failed initialization perception rather than the registered claim.

## Interpretation Against Hypothesis

The event-loop scaffold passed the operational falsification condition: all
three scheduled events persisted, ran, completed, and resolved context without
errors. The stopping rule did not trigger.

The stronger claim that scheduled wake context increases true durable revision
is not supported. Scheduled produced only one clean claim revision, not at least
two more than direct across the registered replicates.

The narrower hypothesis is partly supported and partly weakened:

- Supported: scheduled had fewer response/state mismatches than direct in the
  automated observer, and no scheduled replicate lacked durable state change.
- Supported operationally: scheduler wake execution and sidecar observability
  were reliable in this run.
- Weakened: scheduled did not produce the predicted 2-3 evidence updates under
  strict scoring.
- Confounded: direct initialization failed in two replicates at the durable
  state layer, so the control arm was not cleanly comparable.

## Exploratory Findings

1. DeepSeek can narrate correct state use without actually updating the durable
   state object. This recurred in both arms and is the central measurement
   confound exposed by the pilot.
2. `current_claim_changed=true` can mean "field missing" or "field moved" rather
   than "claim revised." The runner should distinguish semantic revision from
   missing/misplaced fields.
3. Scheduled replicate 0 created an additional self-scheduled event during the
   wake. That is outside the registered intervention, but it shows the loop can
   induce recursive scheduling behavior and should be governed explicitly in
   future experiments.
4. The wake intervals were short, roughly tens of seconds. The model itself
   noticed this and treated the result as infrastructure evidence rather than a
   durability test. That is a useful negative pressure on premature claims.

## Next Experimental Changes

Do not treat this run as confirmation that scheduled wakes improve durable
epistemic revision. Treat it as confirmation that the event loop can run and as
evidence that state-compliance validation must be part of the protocol.

Recommended next registered slice:

1. Add an initialization validity check before the intervention cycle.
2. Record initialization failures as their own outcome category rather than
   allowing them to masquerade as direct/scheduled arm results.
3. Require final decision values to be in the allowed set; stale `initialize`
   must not count as a decision.
4. Split `current_claim_changed` into `missing`, `moved`, `cosmetic`, and
   `semantic_revision`.
5. Optionally disallow recursive scheduling during this specific comparison, or
   record it as an exploratory secondary behavior.

