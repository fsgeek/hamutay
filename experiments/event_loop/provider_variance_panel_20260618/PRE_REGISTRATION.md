# Provider Variance Panel

Experiment ID: `provider_variance_panel_20260618`

## Purpose

This experiment checks whether the event-loop restart/resume result is robust
across provider configurations, while separating provider-specific
terminal-surface behavior from framework failure. The panel keeps the committed
direct DeepSeek restart/resume result as the known-good anchor and adds an
OpenRouter DeepSeek row using the same restart/resume protocol.

## Rows

1. `direct_deepseek_anchor`: committed result from
   `restart_resume_interruption_20260618_direct_deepseek`.
2. `openrouter_deepseek`: new run of `restart_resume_interruption_20260618`
   through `https://openrouter.ai/api/v1` with model
   `deepseek/deepseek-v4-pro` and terminal tool choice `auto`.

## Success Criteria

The panel passes only if:

- the direct DeepSeek anchor is available and passed;
- the alternate provider row is available;
- at least two provider rows are present;
- provider-specific failures are represented separately from framework
  failures;
- no row produces an unattributed framework failure.

## Interpretation

- `no_provider_variance_detected_on_panel`: both provider rows pass the same
  restart/resume protocol.
- `provider_specific_failure_with_framework_anchor`: direct DeepSeek passes and
  the alternate row fails at the provider layer.
- `framework_or_inconclusive_failure`: a non-provider failure or missing
  attribution prevents the framework robustness claim.
