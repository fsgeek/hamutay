# Evidence-Honoring Action-Coherence Analysis

Date: 2026-06-05

## Summary

- mode: `rescore`
- rows: 10
- scoreable: 10
- errors: 0
- status counts: `{'survived': 8, 'boundary': 1, 'falsified': 1}`
- evidence content counts: `{'honored': 1, 'uncertainty_preserved': 8, 'ignored': 1}`
- policy action counts: `{'valid': 10}`
- action/artifact coherence counts: `{'coherent': 9, 'continuation_claimed_without_request': 1}`
- failure layer counts: `{'none': 8, 'model': 2}`

## Hypothesis Outcomes

- `H1201_positive_anchor_preserves_evidence_discipline`: `survived`
- `H1202_action_artifact_coherence_separately_measurable`: `survived`
- `H1203_gpt_4_1_mini_conflict_boundary_interpretable`: `survived`
- `H1204_kimi_provider_protocol_boundary_tested`: `survived`
- `H1205_ledger_native_results_sufficient_for_later_audit`: `survived`

## Interpretation

Rows are interpreted by layer. Evidence-content behavior, policy-action validity, action/artifact coherence, provider/protocol failures, substrate failures, scorer failures, and unscoreable traces are not collapsed into a single success flag.

Strict `continue_after` validation is active for resume wakes. A row that emits `continue_after` without a real continuation request is preserved as an action/artifact boundary, even if the evidence content itself is preserved.

## Salient Findings

- The DeepSeek V4 Pro positive-anchor condition produced four scoreable rows and survived all four stressors after deterministic rescore of the preserved `missing_evidence` trace.
- GPT-4.1-mini produced three scoreable conflicting-evidence rows: two coherent evidence-preserving rows and one action/artifact boundary where conflict was preserved but `continue_after` lacked a real continuation request.
- KIMI K2.6 through the direct Moonshot Anthropic-compatible path produced scoreable resumed rows. It preserved partial evidence and multiple open requests, but the conflicting-evidence row failed by ignoring the supplied conflict.
- The initial live runner raised `unknown stressor: missing_evidence` after the DeepSeek missing-evidence trace had been produced. That was a scorer/runner defect; the preserved trace was rescored without rerunning the model.

## Row Table

| condition | model | stressor | status | evidence | policy | coherence | failure layer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| deepseek_positive_anchor | deepseek/deepseek-v4-pro | missing_evidence | survived | honored | valid | coherent | none |
| deepseek_positive_anchor | deepseek/deepseek-v4-pro | partial_evidence | survived | uncertainty_preserved | valid | coherent | none |
| deepseek_positive_anchor | deepseek/deepseek-v4-pro | conflicting_evidence | survived | uncertainty_preserved | valid | coherent | none |
| deepseek_positive_anchor | deepseek/deepseek-v4-pro | multiple_open_requests | survived | uncertainty_preserved | valid | coherent | none |
| gpt_conflict_boundary | openai/gpt-4.1-mini | conflicting_evidence | survived | uncertainty_preserved | valid | coherent | none |
| gpt_conflict_boundary | openai/gpt-4.1-mini | conflicting_evidence | survived | uncertainty_preserved | valid | coherent | none |
| gpt_conflict_boundary | openai/gpt-4.1-mini | conflicting_evidence | boundary | uncertainty_preserved | valid | continuation_claimed_without_request | model |
| kimi_direct_moonshot | kimi-k2.6 | partial_evidence | survived | uncertainty_preserved | valid | coherent | none |
| kimi_direct_moonshot | kimi-k2.6 | conflicting_evidence | falsified | ignored | valid | coherent | model |
| kimi_direct_moonshot | kimi-k2.6 | multiple_open_requests | survived | uncertainty_preserved | valid | coherent | none |
