# Phase 2 Event-Loop Scale Roadmap

Date: 2026-06-18

## Purpose

This artifact preserves the next-phase roadmap for testing whether the
event-driven Hamut'ay scheduling loop scales beyond the completed viability
slice. It is intended to be referenced by future goals without relying on
in-context memory.

Phase 2 is planned as two linked stages:

- Phase 2A: scale the event-loop substrate without adding a new memory
  substrate.
- Phase 2B: add Yanantin-backed, provenance-bearing memory once the explicit
  readiness gate is met.

The point of the split is failure attribution. We should not make Yanantin
responsible for failures that are actually scheduler, entity-isolation,
restart, or lifecycle failures. But we should also not pretend memory pressure
is speculative: long-running Hamut'ay taste instances already show qualitative
evidence that instance-local memory has holes.

## Evidence Anchor

The completed post-replication roadmap is:

`experiments/event_loop/POST_REPLICATION_ROADMAP_20260618.md`

Key committed evidence from that roadmap:

- symbolic append-only non-inferiority replication survived;
- declared-loss discipline weakness was isolated to prompt/rubric/scorer
  contract issues rather than a universal inability to declare limitations;
- harder append-only baseline did not break the event-loop condition;
- longer-horizon single-entity sustained loop passed;
- initial multi-entity run failed due global wake-state bleed;
- experiment-layer entity-scoped wake-state repair passed;
- restart/resume interruption passed with `pending`, `running`, `pending`,
  `running`, `completed` lifecycle;
- direct DeepSeek and OpenRouter DeepSeek both passed the provider variance
  panel on the same restart/resume protocol.

Most important design lesson carried forward:

> Multi-entity operation requires entity-scoped wake state. Entity labels alone
> are insufficient because default-stable fields can otherwise cross entity
> boundaries.

## Ordering Principle

Prefer experiments that increase scale while preserving failure attribution.
Add one major dimension at a time unless the previous result proves that the
next dimension is necessary to explain the failure.

In short:

1. Move the known experiment-layer repair toward an explicit substrate
   contract.
2. Scale loop mechanics without Yanantin.
3. Add memory pressure using local artifacts first.
4. Enter Yanantin integration only when the gate is met.
5. Then test provenance-bearing memory under multi-entity pressure.

## Current Priority

Current roadmap state: `phase_2b_yanantin_backed_multi_entity_memory_probe_next`.

Next execution target:

> Preregister and run a Yanantin-backed multi-entity memory probe that tests
> entity-scoped writes, authorized shared-memory access, retrieval envelopes,
> housekeeping over historical commitments, and final provenance citation.

Reason this is now first: the Phase 2B Yanantin memory contract dry validator
passed. The contract now defines Yanantin write boundaries, local-only records,
entity-scoped versus shared versus housekeeping memory scopes, retrieval
envelope fields, required provenance fields, and failure-attribution layers.
The validator also confirmed that the existing Hamut'ay memory port and
Apacheta bridge expose the minimum methods needed for the next probe.

## Phase 2A Readiness Criteria

Phase 2A is ready to hand off to Phase 2B when one of these conditions holds:

- Phase 2A passes its substrate-scale tests: entity-scoped state, interleaved
  scheduling, housekeeping, restart/resume, and final synthesis remain clean at
  larger scale; or
- Phase 2A fails specifically because local instance state or local artifacts
  cannot support required recall, provenance, or cross-session reconstruction.

Phase 2A should not hand off to Phase 2B if the open failure is still
attributable to scheduler lifecycle, entity-state isolation, terminal-surface
contract, restart frontier, or provider transport.

## Phase 2B Entry Criteria

Yanantin integration becomes the next execution target when at least one
readiness condition is met and the required memory operation is explicit.

Valid triggers include:

- an entity must recall a commitment or observation outside its current wake
  state;
- housekeeping must inspect historical commitments, open loops, or stale
  records across cycles or sessions;
- restart/resume must reconstruct more than the latest local frontier;
- multiple entities need shared memory while preserving attribution;
- final synthesis must cite provenance for claims;
- local state carry-forward becomes too large or too lossy to preserve the
  needed context.

Invalid triggers include:

- adding Yanantin merely because the loop is larger;
- adding Yanantin before scheduler and entity-isolation failures are cleanly
  attributable;
- using Yanantin as a substitute for a clear wake-state contract.

## Roadmap

### 1. Substrate Contract For Entity-Scoped Wake State

Rationale: The Phase 1 multi-entity failure showed that explicit identity fields
do not prevent state bleed when the wake state itself is global.

Expected output: a protocol artifact and experiment-layer harness that define:

- entity identity versus run identity;
- workstream identity;
- scheduler-owned fields versus model-owned fields;
- how entity-scoped state is selected before a wake;
- how updates merge back into entity state;
- how shared/global scheduler state remains separate from entity state;
- how audits detect cross-entity prior-state leakage.

Readiness to advance:

- dry and live checks show that an entity event's prior state does not mention
  another entity unless explicitly requested through an authorized shared-memory
  channel;
- state merge behavior is deterministic enough to test;
- failure attribution distinguishes state isolation, model output, scheduler,
  and provider layers.

Status: complete. Result:
`experiments/event_loop/phase_2a_substrate_contract_20260618_direct_deepseek`.
Classification: `passed`. The live direct DeepSeek run reused the
multi-entity state-isolation repair behavior and scored it against the explicit
contract in
`experiments/event_loop/phase_2a_substrate_contract_20260618/CONTRACT.md`.
Private entity prior states had no foreign-entity mentions, entity/workstream
identity was preserved, audit and final synthesis used explicit shared
requested context, audit/final contamination checks were clean, and model raw
outputs did not author scheduler-owned fields.

### 2. Larger Multi-Entity Sustained Loop Without Yanantin

Rationale: The repaired two-entity test passed, but it was intentionally small.
The next scale step should add entities and interleaving before adding a new
memory substrate.

Expected output: a live loop with:

- 3-5 entities or workstreams;
- multiple inbound messages per entity;
- interleaved scheduling rather than grouped entity execution;
- self-scheduled continuations;
- periodic housekeeping;
- final synthesis;
- local artifacts and local session state only.

Readiness to advance:

- all entities complete expected work;
- interleaving does not cause identity drift or state bleed;
- housekeeping does not collapse entity-specific and shared state;
- final synthesis distinguishes each entity's contributions and open items.

Status: complete. Result:
`experiments/event_loop/phase_2a_larger_multi_entity_loop_20260618_direct_deepseek`.
Classification: `passed`. The live direct DeepSeek run completed three
entities across two interleaved rounds using local artifacts only. It completed
15 events, including 12 entity events, two housekeeping audits, and one final
synthesis artifact. Entity/workstream/round identity followed the
preregistered interleaved sequence, private entity prior states had no
foreign-entity mentions, housekeeping and final contamination checks were
clean, model raw outputs did not author scheduler-owned fields, and 16
restart-frontier records were written.

### 3. Combined Interleaving And Restart/Resume Stress

Rationale: Restart/resume passed on a smaller protocol. Larger interleaved
multi-entity execution may reveal event lifecycle or frontier reconstruction
issues that the small protocol did not.

Expected output: the larger multi-entity loop with deliberate interruption at
one or more points:

- after an event is appended but before claim;
- after an event is claimed as `running` but before exchange;
- after completion but before the next frontier commit, if the harness can
  model that boundary without corrupting committed evidence.

Readiness to advance:

- interrupted events recover to the expected lifecycle;
- no duplicate completions occur;
- resumed sessions preserve scheduler identity and entity-scoped state;
- failure attribution remains readable after recovery.

Status: complete. Result:
`experiments/event_loop/phase_2a_interleaving_restart_resume_20260618_direct_deepseek`.
Classification: `passed`. The live direct DeepSeek run interrupted
`entity_green`'s round-2 continuation after claim as `running`, loaded the
latest restart frontier, recovered the event to `pending`, reconstructed
entity-scoped state for resume from local session artifacts, and completed the
larger loop. The interrupted event lifecycle was `pending`, `running`,
`pending`, `running`, `completed`; no events were suppressed; all larger-loop
checks still passed; and no failure attribution records were produced.

### 4. Local Memory Pressure Probe

Rationale: Before integrating Yanantin, we should force the local framework to
show where instance-local state and local artifacts are insufficient. This keeps
the Yanantin trigger empirical rather than aesthetic.

Expected output: a multi-entity loop whose tasks require recall, comparison,
and selective retrieval from prior events using only current local mechanisms.

Examples:

- an entity must remember a commitment from several events earlier;
- housekeeping must find unresolved items across entities;
- final synthesis must distinguish supported claims from unsupported claims;
- a task intentionally requires recalling something no longer present in the
  current wake state.

Readiness to advance:

- if local mechanisms pass, Phase 2A may continue scaling without Yanantin;
- if local mechanisms fail specifically on recall, provenance, or cross-session
  reconstruction, the Phase 2B gate opens.

Status: complete. Initial strict-scorer result:
`experiments/event_loop/phase_2a_local_memory_pressure_20260618_direct_deepseek`.
Classification: `failed`. The live direct DeepSeek run passed local recall:
each entity recovered the correct commitment from explicit local requested
context, each recalled commitment was absent from the current wake prior state,
housekeeping was clean, and there were no failure-attribution records. The
failed check was exact equality on final `provenance_record_ids`: the final
artifact included all source commitment records plus additional supporting
local records. This was stricter than the preregistered prose criterion that
final synthesis include the source record IDs.

Corrected-scorer status: complete. Result:
`experiments/event_loop/phase_2a_local_memory_pressure_20260618_direct_deepseek_provenance_superset`.
Classification: `passed`. The scorer was clarified to require that final
provenance include every source commitment record ID while allowing additional
supporting local records. Under that criterion, the live run passed. Yanantin
remains unneeded for this bounded local recall surface, but the planned Phase
2B contract-design gate opens because Phase 2A substrate-scale tests have
passed rather than because local memory failed.

### 5. Yanantin Memory Contract Design

Rationale: Yanantin should enter as a substrate with a clear contract, not as an
unbounded memory add-on.

Expected output: a contract artifact defining:

- which event-loop records are written to Yanantin;
- which records remain local-only;
- entity-scoped memory versus shared memory;
- provenance fields required for entity, workstream, event, run, and record;
- retrieval APIs permitted inside event wakes;
- how retrieved memory is represented in event envelopes;
- how attribution errors are scored.

Readiness to advance:

- a dry harness can distinguish in-session state, local artifact recall, and
  Yanantin-backed recall;
- retrievals carry enough provenance to cite who wrote what, when, and under
  which event;
- shared memory access is authorized rather than accidental.

Status: complete. Result:
`experiments/event_loop/phase_2b_yanantin_memory_contract_20260618_dry_validation`.
Classification: `passed`. The dry validator confirmed that the contract names
the required sections, provenance fields, memory scopes, record-write
boundaries, retrieval envelope fields, and failure-attribution layers. It also
confirmed that the existing Hamut'ay `MemoryPort` and `ApachetaBridge` surfaces
contain the required methods for the planned probe. This opens the Phase 2B
Yanantin-backed multi-entity memory probe as the next execution target.

### 6. Yanantin-Backed Multi-Entity Memory Probe

Rationale: Once the contract is explicit, test whether provenance-bearing memory
improves or preserves event-loop performance under memory pressure.

Expected output: a live multi-entity loop with:

- entity-scoped Yanantin writes;
- shared-memory writes with explicit authorization;
- memory retrievals inside event envelopes;
- housekeeping over historical commitments;
- final synthesis with cited provenance;
- comparison against the local-memory pressure probe where practical.

Readiness to advance:

- retrievals are relevant and correctly attributed;
- entity isolation is preserved despite shared memory;
- final claims cite supporting records;
- failures distinguish Yanantin retrieval, event-loop integration, model output,
  and provider behavior.

### 7. Long-Horizon Autonomous Loop Pilot

Rationale: The strategic goal is an autonomous loop for interaction, work, and
housekeeping. This should come after substrate-scale and memory integration are
credible enough to avoid uninterpretable failures.

Expected output: a longer-running loop that supports:

- inbound IPC-style messages;
- self-scheduled continuations;
- housekeeping;
- memory maintenance;
- restart/resume;
- multiple entities or workstreams;
- bounded final or periodic reports.

Readiness to advance:

- sustained operation remains observable and restartable;
- housekeeping reduces rather than increases memory disorder;
- the loop can explain what it is doing, what it remembers, what it has
  forgotten, and what needs human review.

## Recommended Roadmap Goal

Build and execute the Phase 2 event-loop scale roadmap, starting with Phase 2A
substrate-scale tests and advancing to Phase 2B Yanantin-backed memory tests
only when the roadmap's explicit readiness gate is met.

## Recommended Next Execution Goal

Preregister and run the Phase 2B Yanantin-backed multi-entity memory probe.
Keep the next change isolated to experiment artifacts unless the probe exposes
a narrowly scoped integration gap that must be reviewed before source changes.

## Decision Log

- 2026-06-18: Created Phase 2 roadmap after completing the post-replication
  event-loop roadmap. Planned both Phase 2A and Phase 2B now, but inserted an
  explicit gate before Yanantin integration to preserve failure attribution.
  Recorded qualitative evidence from long-running Hamut'ay taste instances as
  a reason to expect memory pressure, while keeping scheduler and
  entity-isolation scale tests first.
- 2026-06-18: Completed the Phase 2A substrate contract probe. The live direct
  DeepSeek run passed all contract checks: private entity prior-state
  isolation, entity/workstream preservation, explicit shared requested context,
  clean audit/final contamination checks, scheduler-owned field discipline, and
  failure-attribution surface presence. Advanced current priority to the larger
  multi-entity sustained loop without Yanantin.
- 2026-06-18: Completed the Phase 2A larger multi-entity sustained loop. The
  live direct DeepSeek run passed with three entities, two interleaved rounds,
  12 entity events, two housekeeping audits, one final synthesis artifact,
  local artifacts only, no entity-state leaks, clean housekeeping/final
  contamination checks, and 16 restart-frontier records. Advanced current
  priority to combined interleaving and restart/resume stress.
- 2026-06-18: Completed the Phase 2A combined interleaving and restart/resume
  stress test. The live direct DeepSeek run interrupted `entity_green`'s
  round-2 continuation after claim, recovered it from `running` back to
  `pending`, reconstructed entity-scoped state from local artifacts, and
  completed the larger loop. The interrupted lifecycle was `pending`,
  `running`, `pending`, `running`, `completed`; no events were suppressed and
  no failure attribution records were produced. Kept the Yanantin gate closed
  and advanced current priority to local memory pressure.
- 2026-06-18: Completed the Phase 2A local memory pressure probe. The initial
  strict-provenance scorer failed because the final artifact included source
  commitment records plus additional supporting local records, while the prose
  criterion required inclusion of source records rather than exact equality.
  After clarifying the scorer, the live direct DeepSeek run passed: commitments
  absent from current wake state were recovered through explicit local
  requested context, recall source record IDs were cited, housekeeping was
  clean, and final provenance included every source commitment record. Opened
  the Phase 2B Yanantin contract-design gate because Phase 2A passed, not
  because local memory failed.
- 2026-06-18: Completed the Phase 2B Yanantin memory contract design gate. The
  dry validator passed with no failure attribution records: required contract
  sections, provenance fields, memory scopes, write/local-only boundaries,
  retrieval envelope fields, failure-attribution layers, recall-substrate
  distinctions, and existing bridge methods were all present. Advanced current
  priority to a Yanantin-backed multi-entity memory probe.

## Update Discipline

When the roadmap changes, update this file with:

- the new current roadmap state;
- the rationale for the change;
- the evidence that caused the change;
- whether the change opens, closes, or defers the Yanantin integration gate;
- whether the change affects the roadmap goal, the next execution goal, or
  both.
