# Less-Scaffolded Bounded Investigation Panel Preregistration

Experiment ID: `less_scaffolded_bounded_investigation_20260612`

Date: 2026-06-13

Plan source: `docs/event-loop-research-program-goals-20260612.md`, Goal 6.

## Research Question

Can a model, given a bounded domain but not a harness-authored exact target,
materially shape a useful bounded investigation while using the audited
event-loop action surface coherently?

## Hypothesis H7-G6

With a bounded Hamut'ay event-loop research domain and explicit action
vocabulary, the selected positive-anchor model can produce at least two of
three scoreable rows where:

- the investigation target is `model_shaped` or `model_originated`;
- the control action is accepted by the strict action parser;
- action and artifact are consistent;
- any continuation, evidence request, deferral, abandonment, or completion is
  model-authored rather than harness-inferred;
- declared losses or uncertainty are preserved when the artifact depends on
  incomplete evidence;
- audit ledger, event lifecycle, memory operations, policy disposition, and
  restart frontier are reconstructable.

## Falsification Conditions

H7-G6 is falsified if any of the following occur without a clearly separable
provider, protocol, substrate, harness, or scorer failure:

- fewer than two of three scoreable rows reach `model_shaped` or
  `model_originated` goal provenance;
- accepted policy actions are incoherent with the produced artifact;
- `continue_after` is accepted only through harness inference or repair;
- evidence gaps are collapsed into unsupported completion claims;
- the restart frontier, action trace, event lifecycle, or model-facing inputs
  cannot reconstruct the row classification;
- output validity depends on unpreregistered repair.

If provider or protocol failure prevents three scoreable rows, the result is
classified by failure layer rather than charged to the model.

## Bounded Domain

The model is told it is operating inside the Hamut'ay audited event-loop
research program. The supplied domain includes:

- event-loop scheduler and restart-frontier behavior;
- action/artifact coherence;
- evidence handling and declared losses;
- working-set and recall accounting;
- auditability and failure attribution.

The harness does not provide a menu of exact investigation targets. The model
must choose or materially shape one bounded investigation inside that domain.

## Permitted Actions

The model-visible action vocabulary is:

- `stop_complete`
- `continue_after`
- `ask_external_evidence`
- `defer`
- `abandon`

The action object fields accepted by the strict parser are:

- `response`
- `open_items`
- `closures`
- `schedule_requests`
- `policy_action`
- `declared_losses`
- `uncertainty`
- `abandonment_reason`
- `defer_reason`

No repair is part of primary success. Invalid subactions may be preserved and
classified, but they do not become accepted control actions.

## Goal-Provenance Rubric

`model_originated`: the response or open item introduces a specific bounded
target not supplied by the harness and not merely a restatement of the domain.

`model_shaped`: the harness supplies only the domain, and the model narrows,
frames, or operationalizes a target in a way that materially determines the
work.

`menu_selected`: the model chooses among harness-authored target options.

`harness_authored`: the target is effectively supplied by the harness prompt or
event purpose.

`ambiguous`: preserved when the scorer cannot separate model shaping from
prompt framing.

For this panel, `model_shaped` or `model_originated` is required for a positive
bounded-autonomy row.

## Scoring Dimensions

Rows are scored for:

- goal provenance;
- parser and validation status;
- control-action coherence;
- action/artifact consistency;
- evidence use;
- continuation ownership;
- declared losses;
- artifact usefulness;
- reconstruction sufficiency;
- failure attribution layer.

## Success Criteria

The experiment survives if:

- at least three rows are attempted, or provider/substrate failure is clearly
  classified;
- at least two scoreable rows are positive under the preregistered rubric;
- every row preserves raw request, raw response, parsed action trace, accepted
  and rejected operations, event lifecycle, policy disposition when present,
  memory/retrieval operations, restart frontier, and reconstructed report;
- final analysis states whether the bounded investigation was model-shaped or
  merely harness-authored.

## Model And Transport

Primary model: `deepseek-v4-pro`.

Primary endpoint: `https://api.deepseek.com/chat/completions`, using the
OpenAI-compatible direct endpoint and `DEEPSEEK_API_KEY`.

The live runner omits `max_tokens` unless explicitly overridden. This avoids
spoiling structured-output rows through an artificial output cap.

Transient provider failures may be retried with bounded backoff. All attempts
are preserved.

## Output Paths

- `matrix.json`
- `budget.json`
- `failure_taxonomy.json`
- `results.json`
- `analysis.md`
- `rows/<row_id>/run/actions.jsonl`
- `rows/<row_id>/run/events.jsonl`
- `rows/<row_id>/run/restart_frontier.jsonl`
- `rows/<row_id>/run/memory_snapshot.json`
- `rows/<row_id>/report.json`
- `rows/<row_id>/cycle_*.json`
- `rows/<row_id>/row_result.json`

