# Event-Loop Continuity Substrate Spec

Filed: 2026-06-05 after `continuity-research-synthesis-20260605.md`.

## Purpose

Define the minimal research substrate for bounded autonomy experiments.

The substrate is not a claim about AI identity. It is a control loop and
observability layer for testing what transformer instances can do across
discontinuous cycles when given:

- durable self-authored state;
- explicit-schema continuity artifacts;
- scheduled re-entry events;
- bounded deterministic context rendering;
- logged omissions, failures, and protocol repairs.

## Design Principles

1. Data first. Every loss, omission, repair, and failure is recorded.
2. Identity state is not the whole memory system.
3. Curator artifacts do not mutate identity state.
4. Context injected into a cycle is rendered deterministically from validated
   artifacts.
5. Protocol ambiguity is rejected or repaired only under logged rules.
6. Scheduler experiments require separate initialization and tool-path gates.
7. Metaphysical identity claims are out of scope.

## Core Loop

Each cycle has five phases:

1. **Assemble context**
   - prior identity state;
   - optional scheduled event envelope;
   - optional continuity rendering;
   - optional recall results;
   - explicit declared-loss/omission markers.

2. **Invoke main instance**
   - model produces visible `response`;
   - model updates open identity state through `think_and_respond`;
   - model may call allowed tools if enabled.

3. **Validate and merge**
   - reject delete-plus-update overlap unless a preregistered normalizer is
     active;
   - preserve raw output regardless of merge success;
   - classify protocol failures distinctly from task failures.

4. **Curate continuity**
   - curator receives prior state, raw output, visible response, merged state,
     cycle metadata, and optional event metadata;
   - curator returns explicit-schema claim rows;
   - renderer selects context for next cycle;
   - selected and omitted rows are logged.

5. **Schedule and persist**
   - committed scheduled events are appended only after successful cycle merge;
   - wake execution records event status, context resolution, and outcome;
   - failures are sidecar records, not silent drops.

## Artifact Contracts

### Cycle Record

Required fields:

- `record_type: "cycle"`
- `cycle`
- `record_id`
- `timestamp`
- `experiment_label`
- `model`
- `user_message`
- `system_prompt`
- `prior_state`
- `raw_output`
- `deleted_regions`
- `response_text`
- `state`
- `usage`
- `state_token_estimate`
- `system_prompt_tokens`

Optional fields:

- `scheduled_events`
- `continuity_curation`
- `curator_context_injection`
- `event_context`
- `protocol_recovery`
- `failure_classification`

### Identity State

The identity state remains open/extensible. Required framework behavior:

- top-level `cycle` is framework-authored;
- protocol fields (`response`, `deleted_regions`, legacy `updated_regions`)
  are not preserved as identity state;
- identity state is authored by the main model only;
- curator artifacts are never inserted automatically.

### Continuity Claim Row

Explicit-schema row:

```json
{
  "claim": "string",
  "status": "supported | invalidated | uncertain | open",
  "source_cycle": 3,
  "support": "string"
}
```

Validation rules:

- reject rows without `claim`;
- reject rows whose status is outside the allowed set;
- coerce integer-like `source_cycle`; otherwise store `null`;
- cap claim/support cell lengths;
- record rejected rows and reasons.

### Continuity Curation Record

Required fields:

- `record_type: "continuity_curation"`
- `record_id`
- `status`
- `created_at`
- `source_cycle`
- `source_record_id`
- `summary`
- `artifact`

Artifact fields:

- `curator_type`
- `model`
- `renderer`
- `summary_source`
- `summary_chars`
- `summary_truncated`
- `claim_rows`
- `rendered_claim_rows`
- `accepted_claim_rows`
- `rejected_claim_rows`
- `rejected_claim_row_examples`
- `selected_delta_rows`
- `omitted_delta_rows`
- `selected_delta_row_count`
- `omitted_delta_row_count`
- `usage`
- `raw_output`

### Event Record

Event records remain sidecar JSONL entries. Required lifecycle records:

- `event_pending`
- `event_running`
- `event_completed`
- `event_failed`

Required event fields:

- `event_id`
- `created_at`
- `scheduled_by_cycle`
- `scheduled_by_record_id`
- `purpose`
- `requested_context`
- `not_before`
- `status`

Wake records must include:

- context resolution results;
- context errors;
- source event ID;
- wake cycle record ID when available.

### Omission Record

Any renderer or context-boundary omission must preserve:

- `source_artifact_id`
- `selected_count`
- `omitted_count`
- `selected_rows`
- `omitted_rows`
- `selection_policy`
- `budget_chars`
- `truncated`

Omission is not absence. It is a recorded substrate decision.

### Protocol Recovery Record

Protocol recovery records are required when any parser or merge path accepts a
non-canonical shape:

- `recovery_type`
- `source_field`
- `accepted_shape`
- `recovered_count`
- `raw_excerpt`
- `reason`

Strict mode should be the default in experiments. Repair modes must be
preregistered.

## Renderer Policies

### Full Claim Table

Render validated claim rows in deterministic priority order until budget.

Use when:

- contamination minimization is primary;
- context budget is less constrained;
- first-pass substrate validation is more important than efficiency.

### Delta Claim Table

Render new or changed rows plus stable high-priority rows.

Current priority:

1. new/changed `invalidated`
2. new/changed `supported`
3. stable `invalidated`
4. stable `supported`
5. new/changed `uncertain`
6. new/changed `open`

Log selected and omitted rows.

### Guardrail Delta

Proposed next renderer. Reserve slots for:

- no-local-document-storage constraint when present;
- site substitution status when present;
- invalidated assumptions up to cap;
- top new/changed supported claims;
- one uncertainty/open-question row when present.

This should be the next preregistered renderer experiment.

## Scheduler Gates

Scheduler experiments must classify failures before interpreting wake results.

### Initialization Gate

Before scheduler intervention:

- required top-level fields are present;
- durable state matches visible response claims;
- baseline evidence/claim fields are not merely prose.

Invalid initialization ends the replicate as `initialization_failed`.

### Scheduler Tool Gate

Before epistemic or autonomy claims:

- schedule_event is actually called;
- event is persisted;
- terminal `think_and_respond` follows tool results;
- event sidecar records completion or failure.

Failure here is `scheduler_tool_failure`, not task failure.

### Wake Gate

On wake:

- requested context resolves or records explicit context errors;
- wake cycle records source event;
- durable state records wake status when required by the experiment.

Failure here is `wake_execution_failure`.

## Evaluation Contract

Primary evaluation should include:

- recovery total;
- repaired false assumption count;
- declared loss mentions;
- negated/invalidated hits;
- active contamination attribution;
- protocol failure classes;
- selected/omitted continuity rows;
- token usage;
- rebriefing needed;
- scheduled event completion;
- semantic revision when relevant.

Evaluation must keep scorer versions visible. Repaired contamination scoring is
current primary, but it remains heuristic.

## Minimal Vertical Slice

The first substrate slice should implement or consolidate:

1. Explicit-schema claim-table curator.
2. Guardrail delta renderer.
3. Event queue wake envelope.
4. Cycle log + event sidecar + curation artifact linkage.
5. Failure taxonomy for initialization, scheduler tool path, wake path,
   protocol merge, and curator failure.
6. Shared evaluator for recovery/contamination/attribution.

## First Substrate Experiment

Recommended first question:

> Can a guardrail-preserving delta renderer reduce continuity context while
> matching full claim-table recovery and contamination in a scheduled re-entry
> task?

Candidate conditions:

- `claim_table_full_1200`
- `claim_table_delta_800`
- `claim_table_guardrail_delta_900`

Model:

- `mistralai/mistral-small-2603` for direct comparability with recent panels.

Why not scheduler autonomy immediately:

- renderer guardrails are still an active confound;
- scheduled wake experiments need clean continuity artifacts;
- prior scheduler panels showed initialization/tool-path gates must be
  explicit.

## Build Boundary

Do not build a broad platform yet.

Build only enough to test the next falsification question and to make the data
cleaner than the current experiment-specific runners. The first substrate
implementation should be allowed to remain research infrastructure.
