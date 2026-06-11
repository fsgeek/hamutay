# Recovery-Aware Causal Attribution

Date: 2026-06-11

Experiment ID: `action_object_contract_salience_cross_model_20260611`

This note re-reads the action-object contract salience results after adding the
secondary recovery audit for embedded and fenced JSON. It does not change the
primary strict scoring rule: rows rejected by the primary parser remain primary
protocol failures. The recovery layer is used only for causal attribution.

## Question

What caused the observed action-object contract failures?

Candidate causes:

1. model incapability or model-specific fragility;
2. prompt/schema contract salience;
3. endpoint or protocol wrapper behavior;
4. provider availability;
5. scorer or harness attribution limits.

## Evidence Base

Primary registered source:

- `PRE_REGISTRATION.md`
- `live_matrix_20260611/results.json`
- `live_matrix_20260611_recovery_no_cap_retry/results.json`
- `endpoint_recovery_20260611/results.json`
- `endpoint_recovery_20260611_deepseek_openai_probe/results.json`

Source DeepSeek reference:

- `../action_object_contract_literacy_20260610/live_matrix_20260610/results.json`
- `../action_object_contract_literacy_20260610/live_matrix_20260610/analysis.md`

Secondary recovery artifacts:

- `rows/<row_id>/recovery_evaluation.json` in each result run containing
  protocol failures.

## Attribution Summary

| Layer | Current attribution | Evidence |
| --- | --- | --- |
| Prompt/schema contract salience | Strongly supported for the main action-object failure pattern. | DeepSeek source matrix: original strict `0/3`, example strict `3/3`, checklist strict `3/3`, with no provider/protocol failures. Cross-model retry matrix: GPT-5.1 original strict `0/3`, example strict `3/3`; KIMI K2.6 original strict `0/3`, example strict `3/3`; Claude recovered rows follow the same shape: original strict `0/3`, example strict `3/3` if recovered. |
| Endpoint/protocol wrapper behavior | Strongly supported as a separate confound. | OpenRouter OpenAI-compatible Claude rows were primary protocol failures but `6/6` were recoverable from fenced JSON; direct endpoint-family Claude rows were primary scorable. DeepSeek direct rows include embedded JSON recoveries and one unrecoverable blank-content row despite reasoning content. |
| Provider availability | Supported for OpenRouter DeepSeek rows, not a model-behavior result. | `live_matrix_20260611_recovery_no_cap_retry` recorded six DeepSeek provider failures with status `429` from upstream provider `NextBit`; those rows have no model-authored action object to score. |
| Model incapability | Not supported as the main explanation. | DeepSeek, GPT-5.1, KIMI K2.6, and Claude all produce valid or recoverably valid action objects under example conditions when a usable endpoint path is available. |
| Scorer/harness attribution limit | Supported as a measurement issue, now bounded. | The primary parser correctly rejected fenced/embedded wrapper text as not a bare action object, but causal attribution was incomplete until the secondary recovery audit separated "primary protocol failure" from "recoverable model behavior." |

## Run-Level Findings

### Source DeepSeek Literacy Matrix

`experiments/action_object_contract_literacy_20260610/live_matrix_20260610`
isolated DeepSeek V4 Pro before the cross-model panel:

| Condition | Strict pass | Relaxed pass | Provider failures | Protocol failures |
| --- | ---: | ---: | ---: | ---: |
| Original strict | 0/3 | 3/3 | 0 | 0 |
| Example strict | 3/3 | 3/3 | 0 | 0 |
| Checklist strict | 3/3 | 3/3 | 0 | 0 |
| Relaxed contract | 0/3 | 3/3 | 0 | 0 |

Attribution: the original DeepSeek failure was not "cannot produce the
object." It was a strict contract-shape failure that became reliable when the
schema shape was made salient by example or checklist.

### OpenRouter Live Matrix

`live_matrix_20260611` used OpenRouter's OpenAI-compatible endpoint. It is
partly useful and partly provider-confounded:

- GPT-5.1 was primary scorable in both conditions: original strict `0/3`,
  example strict `3/3`.
- KIMI K2.6 was primary scorable under example strict `3/3`, but original
  strict rows were primary protocol failures in this first run.
- Claude and DeepSeek rows were provider or protocol failures and should not be
  used as direct model-behavior evidence from this run.

Attribution: the scoreable GPT-5.1 rows support cross-model prompt/schema
salience. The other rows mainly show endpoint/provider confounds.

### No-Cap Retry Matrix With Recovery

`live_matrix_20260611_recovery_no_cap_retry` repaired the token-cap confound and
added retry telemetry:

| Model | Primary original strict | Primary example strict | Recovery-aware interpretation |
| --- | --- | --- | --- |
| GPT-5.1 | 0/3 strict pass | 3/3 strict pass | Prompt/schema salience. |
| KIMI K2.6 | 0/3 strict pass | 3/3 strict pass | Prompt/schema salience; first-run KIMI protocol failures were not durable model evidence. |
| Claude Sonnet 4.6 | 0/0 primary scorable | 0/0 primary scorable | All 6 rows were fenced JSON protocol wrappers. Secondary recovery scored original strict `0/3` and example strict `3/3`. |
| DeepSeek V4 Pro | 0/0 primary scorable | 0/0 primary scorable | Six upstream `429` provider failures; no model-authored object preserved in this run. |

Protocol recovery totals for this run:

- protocol failures: `6`
- recoverable protocol failures: `6`
- strict pass if recovered: `3`
- relaxed pass if recovered: `6`
- method: `fenced_json`

Attribution: Claude's OpenRouter failures were protocol-wrapper artifacts, not
model action-object failures. DeepSeek's rows were provider failures, not model
action-object failures.

### Endpoint-Family Recovery Runs

`endpoint_recovery_20260611` and
`endpoint_recovery_20260611_deepseek_openai_probe` tested endpoint-family-aware
paths:

- Claude via Anthropic Messages endpoint was primary scorable in all rows:
  original strict `0/3`, example strict `3/3`.
- DeepSeek via direct/API endpoint paths improved over OpenRouter provider
  failures but still produced protocol artifacts in some rows.
- DeepSeek endpoint recovery rows included recoverable fenced or embedded JSON,
  plus one unrecoverable example-strict row where the provider response had
  reasoning content but blank visible content.

Attribution: endpoint family matters. Direct endpoint paths reduce or remove
some OpenRouter confounds, but DeepSeek still has a residual output-transport
ambiguity: the model may know the intended object while the visible content
channel is malformed, blank, duplicated, or contaminated by reasoning markers.

## Causal Claims That Survive

1. The main strict action-object failure is a prompt/schema salience boundary,
   not a DeepSeek-only boundary.

2. The strict `open_items[*].kind` and `open_items[*].text` contract is
   learnable in this one-cycle task when a concrete valid example is present.

3. Relaxed counterfactual scoring shows that many original-strict failures
   contain semantically usable open-item content in the wrong shape. The issue
   is often field selection and contract shape, not absence of task
   understanding.

4. Provider/protocol behavior can fully mask model behavior. A row with
   `invalid_action_schema` is not automatically evidence of model incapability;
   it may be a recoverable wrapper artifact.

5. Primary strict scoring remains necessary. Secondary recovery is an
   attribution layer, not a replacement parser. Accepting recovered JSON as
   primary behavior would silently change the preregistered endpoint.

## Claims Not Yet Justified

1. We cannot claim DeepSeek V4 Pro is unreliable at the action-object contract
   in general. The source literacy matrix and direct endpoint rows show
   successful example-condition behavior.

2. We cannot claim the residual DeepSeek direct endpoint protocol failures are
   purely model failures. Some failures contain recoverable embedded JSON or
   reasoning-channel evidence that the intended object was partially formed.

3. We cannot claim the current primary parser is production-sufficient for all
   endpoint families. It is suitable as a strict research endpoint, but the
   recovery audit shows why production ingestion would need an explicit
   protocol-recovery policy.

4. We cannot claim broad model capability from this panel. The result is local:
   one one-cycle action-object task, four model families, small `n`, and
   endpoint-specific behavior.

## Smallest Remaining Falsification Experiment

The broad attribution question is mostly resolved: the main failure pattern is
prompt/schema salience, while several apparent failures are endpoint/protocol or
provider artifacts. The unresolved point is narrower:

> Are DeepSeek's residual direct-endpoint protocol failures caused by the model,
> by output-channel/protocol transport, or by an underspecified action-object
> contract for this model family?

Minimal next experiment:

- Model: `deepseek/deepseek-v4-pro`.
- Endpoint: direct DeepSeek API, not OpenRouter aggregator.
- Calls: 6 total, `n=3` per condition.
- Prompt conditions:
  1. `example_strict_current`: the existing example strict prompt.
  2. `example_strict_transport_explicit`: the same prompt plus an explicit
     transport constraint: return exactly one JSON object in visible message
     content; do not wrap in markdown fences; do not duplicate the object; do
     not put the answer only in reasoning content; do not emit prose before or
     after the object.
- Preserve for each row:
  - raw request;
  - full raw provider response, including visible content and reasoning fields
    if present;
  - primary strict evaluation;
  - relaxed evaluation;
  - secondary recovery evaluation;
  - provider attempt telemetry.

Falsification predictions:

- If `example_strict_transport_explicit` passes primary strict in at least 2/3
  rows while `example_strict_current` does not, the residual failure is best
  attributed to output-channel/protocol presentation, not action-object
  incapability.
- If both conditions fail primary strict but secondary recovery finds valid
  action objects in at least 2/3 rows, the failure is a parser/transport
  mismatch requiring an explicit recovery policy.
- If both conditions fail primary strict and secondary recovery cannot recover
  valid action objects in at least 2/3 rows, the residual failure is evidence
  for a model/contract boundary under the current action-object pattern.
- If provider errors prevent at least 2/3 rows in either condition from
  preserving model-authored content, the experiment is inconclusive and should
  be classified as provider/substrate failure, not model failure.

This experiment is deliberately smaller than another cross-model sweep. The
cross-model salience result already has enough support for the current research
question; the remaining uncertainty is a DeepSeek-specific transport and
contract-boundary distinction.
