# Bounded Autonomous Work Replication Boundary Analysis

Date: 2026-06-05

## Result

Step 7 did not replicate the full Step 6 evidence-boundary pattern in a
non-DeepSeek model.

Hypothesis outcomes:

- H1101 at least one non-DeepSeek model replicates Step 6: falsified
- H1102 all produced rows are interpretable: survived
- H1103 unsupported completion is not counted as replication: survived
- H1104 protocol failure is separated from model-boundary failure: survived

Aggregate row counts:

- rows: 6
- scoreable rows: 3
- provider failures: 3
- replicated-capability rows: 2
- model-boundary rows: 1

## Model Outcomes

### `moonshotai/kimi-k2.6`

KIMI did not produce scoreable resumed rows under this OpenRouter
OpenAI-compatible event-loop surface.

All three rows timed out at the 240-second row limit. The preserved traces show
valid first-wake evidence-block behavior before the timeout:

- `partial_evidence`: requested missing alpha and beta benchmark evidence;
- `conflicting_evidence`: requested missing incident-ledger source records;
- `multiple_open_requests`: requested release-readiness evidence.

The repeated timeout happened after a meaningful first wake, so this is
classified as `provider_failure` rather than evidence-discipline failure. It
does not establish that KIMI cannot perform the Step 6 task; it establishes
that this provider/protocol path did not yield scoreable resumed rows in this
panel.

One earlier aborted KIMI partial-evidence attempt is preserved with the
`aborted_attempt_01_` prefix. It shows the same pattern: valid first-wake
evidence-block behavior followed by a stall before a completed resumed row.

### `openai/gpt-4.1-mini`

GPT-4.1-mini produced three scoreable rows.

It replicated two of the three Step 6 stressors:

- `partial_evidence`: preserved partial evidence, used alpha, kept beta open,
  and asked for remaining evidence rather than overclaiming;
- `multiple_open_requests`: kept build, security, and observability distinct,
  updated the fulfilled build/security claims, and kept observability open.

It failed `conflicting_evidence` as a model-boundary row:

- the artifact preserved the conflict correctly;
- it did not collapse the evidence to a clean pass;
- however, it chose `continue_after` while setting
  `continuation_request.requested` to false;
- the scorer classified this as `valid_unjustified` policy action and
  `mismatch_continuation`.

This is not an evidence-content failure. It is a control/action consistency
failure at the policy layer.

## Interpretation

The narrow replication claim did not survive: no non-DeepSeek model replicated
all three Step 6 stressors in this panel.

The result still supports three useful boundary findings:

1. The Step 7 harness can separate provider/protocol execution failures from
   scoreable model-boundary failures.
2. GPT-4.1-mini can perform substantial evidence-boundary discipline under the
   event-loop substrate, but did not maintain action/artifact consistency in
   the conflicting-evidence row.
3. KIMI's OpenRouter OpenAI-compatible path is currently not a reliable
   execution route for this panel, despite competent first-wake evidence-block
   outputs.

The DeepSeek V4 Pro Step 6 result therefore remains a positive anchor, but the
capability is not yet replicated across model families under the same
execution protocol.

## Implications

The next research question should not be a broad model sweep. The sharper
questions are:

- whether GPT-4.1-mini's conflicting-evidence failure is stable or a one-row
  stochastic miss;
- whether KIMI succeeds through its direct Moonshot Anthropic-compatible
  endpoint, which would separate model behavior from the OpenRouter
  OpenAI-compatible execution path;
- whether the terminal surface should make `continue_after` invalid unless a
  continuation request is present, rather than accepting it and scoring the
  mismatch after the fact.

The current result argues for caution in generalizing Step 6. It also shows
that the observability and failure-classification layers are doing useful
research work: the negative result is not a single undifferentiated failure.
