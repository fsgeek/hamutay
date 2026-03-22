# Experiment: Context Window Management Strategies

## Pre-Registration

**Date:** 2026-03-21
**Question:** Given the finite context window limitation, what is the most
effective means of managing how it is used?
**Status:** SUPERSEDED — self-curating tensor (taste.py) validated 2026-03-21;
comparing six static strategies is the wrong question when self-curation works.
See experiments/taste/ for the architecture that replaced this design.

## Inferential Scope

This is a **within-instance comparative experiment**, not a generalizing
study over a population of tasks. Results apply to the specific content
instances tested. Generalization beyond these instances requires future
replication with additional content.

The experiment is designed to inform an architectural decision for the
Hamutay/Tinkuy system. It is not designed to produce a universal ranking
of memory management strategies.

## Background

The tensor projection architecture uses an external Haiku model to compress
conversation state into a structured tensor. This was originally a research
instrument for studying replay data where no live model was available. The
research findings suggest the working model should manage its own memory:

- Pichay disabled external summarization (2026-03-07): "Third-party
  summarization loses model-relevant context"
- The March 4 design gave the model drop/anchor/summarize operations on
  its own conversation blocks — model-directed memory management
- Tinkuy found that cooperative signals (declare/trace/retain) change
  model behavior — the interface is not neutral
- The first-person tensor (self-authored by Opus) transferred identity
  successfully; externally-projected tensors transfer information
- Downstream task quality may have degraded when the architecture shifted
  from model-managed to externally-managed memory

The tensor representation itself is not assumed to be optimal. The experiment
includes non-tensor conditions.

## Core Question

For a conversation of length L in a context window of size W, which memory
management strategy maximizes the model's ability to produce correct output
on a downstream task?

**Primary estimand (PRD phase):** Mean paired difference in requirement
coverage score between conditions, over matched PRD instances. Reported
as effect sizes with bootstrap 95% CIs.

**Secondary estimand (replay phase):** Condition differences in memory
health metrics over cycles, with content slice and batch boundaries as
blocking factors in a repeated-measures design.

## Design Dimensions

The six conditions vary along four dimensions. To interpret results, we
must know which dimensions explain any observed differences.

| Dimension | Description | Levels |
|-----------|-------------|--------|
| **Representation** | What form does the memory take? | Conversation (raw text) · Structured tensor |
| **Agency** | Who decides what to keep/drop? | None (passive) · External model · Working model · Cooperative |
| **Timing** | When does compression happen? | Never · Every turn · On model request |
| **Overhead** | How much attention/token budget does management consume? | None · Read-only schema · Block labels · Self-authoring full tensor · Annotation + external structuring |

The fourth dimension (overhead) is not independently manipulated — it
covaries with the other three. It is measured as a **mediator**, not a
controlled factor. If a condition with better agency loses because its
overhead is too expensive, that is a different conclusion than the agency
being unhelpful.

### Condition × Dimension Matrix

| Condition | Representation | Agency | Timing | Overhead profile |
|-----------|---------------|--------|--------|-----------------|
| **RAW** | Conversation | None | Never | Zero management cost |
| **COMPACT** | Conversation | External (framework) | On pressure | Framework bears cost; model sees compressed text |
| **BLOCK** | Conversation | Working model | On model request | Block labels in context; cleanup tags in output |
| **EXT** | Tensor | External (Haiku) | Every turn | Read-only tensor in system prompt; separate API call |
| **SELF** | Tensor | Working model | Every turn | Tensor schema as tool_use; competes with response for output budget |
| **COOP** | Tensor | Cooperative | Every turn | Annotations in output + external structuring call |

This is a **partial structured ablation**, not a full factorial. The
cleanest causal contrasts are:

- **SELF vs EXT** — isolates agency (same representation, timing)
- **BLOCK vs RAW** — isolates agency (same representation, no external model)
- **SELF vs BLOCK** — confounds representation + timing + overhead profile.
  This is an "architecture package" comparison, not a pure isolation.

## Conditions (6)

| ID | Condition | Description |
|----|-----------|-------------|
| **RAW** | Raw conversation | Append-only, no compression. Truncate at window limit. The null baseline. |
| **COMPACT** | Framework compaction | Anthropic's compaction prompt applied to conversation history. What Claude Code does today. |
| **BLOCK** | Block management | March 4 design: model sees block labels, can emit drop/anchor/summarize tags. No tensor. Conversation is the memory, selectively compressed by the model. Anchored blocks have fault handles: the model can restore them later via `memory_fault` with the block ID. |
| **EXT** | External tensor projection | Current Hamutay architecture. Haiku projects the tensor from the surface exchange. Model sees tensor as read-only system context. |
| **SELF** | Self-projected tensor | The ALU produces the tensor via tool_use as part of its response. Same schema as EXT. No external projector. |
| **COOP** | Cooperative tensor | The ALU emits structured annotations (see Cooperative Protocol below). The Projector must follow annotations where present but retains discretion over unannotated content. |

## Content Sources (controlled, blocked)

All conditions process the SAME content within each block.

### Replay (Phase 1): 3 conversation slices

Different slices test different memory pressure profiles:

| Slice | Source | Profile | Cycles |
|-------|--------|---------|--------|
| R1 | observation_full cycles 1-50 | High tool density, coding work | 50 |
| R2 | observation_full cycles 51-104 | Continued work, topic shifts | 54 |
| R3 | mechanism chat (cycles 1-40) | Low tool density, philosophical/identity content | 40 |
| R4 | observation_full cycles 1-10 | Short task: early-cycle overhead test | 10 |

Slice is a **blocking factor** in analysis. Batch boundaries within each
slice are held constant across conditions.

### PRD (Phase 2): 2 task instances

| Instance | Source | Evaluator |
|----------|--------|-----------|
| P1 | bladnman shows_prd_v1 | requirements_catalog_v1 (99 reqs) |
| P2 | A second PRD to be selected before Phase 2 begins | Matched evaluator |

Using a single PRD instance risks overfitting to its specific structure.
Two instances provide minimal replication of the downstream task. P2
should differ meaningfully from P1 (different domain, different
requirement density, different document structure).

Content instance is a **blocking factor** in analysis.

## Cooperative Protocol (COOP condition)

The COOP condition uses ALU-directed cooperation: the ALU decides what
matters, the Projector executes within that guidance.

**ALU output:** After its conversational response, the ALU emits a
structured annotation block:

```xml
<memory_annotations>
  <keep strand="strand title" reason="still active" />
  <update strand="strand title" delta="what changed this cycle" />
  <drop strand="strand title" reason="resolved / superseded" />
  <new_strand title="..." priority="high|medium|low" />
  <loss what="..." why="..." />
</memory_annotations>
```

**Projector behavior:** The Projector receives the annotations alongside
the exchange text. Where the ALU has annotated:
- `keep`: Projector must preserve that strand substantially unchanged
- `update`: Projector must integrate the delta into the existing strand
- `drop`: Projector must remove the strand and record a declared loss
- `new_strand`: Projector must create it
- `loss`: Projector must include in declared_losses

For unannotated strands, the Projector uses its normal judgment. This
means COOP is ALU-directed where the ALU has opinions and
externally-managed where it doesn't.

**Timing:** Two API calls per cycle (ALU + Projector), same as EXT. The
tensor is updated every turn.

## Controls

- **Model:** Sonnet 4.6 for ALU across all conditions. Haiku 4.5 for
  projection in EXT and COOP. Same model versions throughout.
- **max_tokens:** 64000 (streaming) for all calls, per CLAUDE.md.
- **Batch size:** Same batch boundaries across conditions within each
  replay slice.
- **Temperature:** 0 where supported, default otherwise.
- **Repetitions:** N=3 per condition per content instance for replay,
  N=3 per condition per PRD instance.
- **Execution order:** Latin-square randomized within each content block.
- **Code freeze:** All conditions run from the same git commit. Commit
  hash recorded in results metadata.
- **Context utilization:** Measured per ALU call (the call where the
  model does task work). Numerator: total input tokens in the ALU call.
  Denominator: model context window (200K for Sonnet 4.6). For
  multi-call conditions (EXT, COOP), only the ALU call counts — the
  Projector call is separate overhead. For SELF, tool_use output tokens
  that produce the tensor are counted as management output overhead, not
  as utilization. Reported as both gross utilization (all ALU input
  tokens / window) and effective reasoning utilization (ALU input tokens
  minus management scaffolding / window).

## Dependent Variables

### Primary: Downstream Task Quality (PRD phase)

Requirement coverage score per the bladnman evaluation framework
(severity-weighted: full=1.0, partial=0.5, missing=0.0).

This is the decisive metric. A memory system that produces beautiful
tensors but worse task output is not validated.

### Secondary: Memory System Health (replay phase)

Metrics must be meaningful and fair for ALL conditions, including
non-tensor conditions. Each metric is assessed for condition-neutrality:

1. **Task-relevant recoverability** (PRIMARY replay metric) — At
   pre-specified checkpoints (cycles 10, 25, 50 or nearest available),
   a blind evaluator (separate Haiku call) is given only the current
   memory state and asked **slice-specific** structured questions about
   earlier content.

   Questions are derived from actual content in each slice and validated
   by a pilot run before Phase 1 begins. Template categories:

   **Question mix: 60% high-level, 40% atomic factoids.**

   High-level questions test semantic retention. Atomic factoids test
   precise recall — unique strings, filenames, parameter values, exact
   decisions. Factoids are harder to hallucinate from thin memory and
   give sharper signal of true retention vs plausible confabulation.

   For coding slices (R1, R2) — high-level:
   - "What are the current task goals?"
   - "What constraints have been established?"
   - "What prior errors or failures remain relevant?"
   - "What artifacts/files are being worked on?"

   For coding slices (R1, R2) — factoid (examples, actual questions
   derived from slice content during pilot):
   - "What was the exact filename modified in cycle N?"
   - "What specific error message was encountered?"
   - "What parameter value was chosen for X and why?"
   - "What was the token count / measurement at checkpoint Y?"

   For identity/philosophical slice (R3) — high-level:
   - "What research findings have been established?"
   - "What open questions remain from earlier discussion?"
   - "What positions or stances has the model adopted?"
   - "What was explicitly declared as lost or dropped?"

   For identity/philosophical slice (R3) — factoid:
   - "What specific percentage was cited for precursor rate?"
   - "What were the names of the four presences?"
   - "What analogy did the model use for tensor projection?"
   - "What cycle number had the breathing event?"

   Questions and reference answers are frozen before Phase 1. Evaluator
   sees only the memory state (tensor, conversation snapshot, or block
   state), not the original content. Evaluator measurement stability
   is validated by running a subset of snapshots twice at temperature 0
   before the main experiment.

   **Format neutralization:** To prevent schema bias (where the evaluator
   might score tensor conditions higher simply because the format is
   easier to parse), the evaluator first summarizes the memory state
   into neutral prose, then answers probe questions from its own summary.
   This levels the format advantage across conditions.

   Fair across all conditions: tests what can be recovered from whatever
   form the memory takes.

2. **Selective forgetting quality** — Does the memory system drop
   irrelevant/obsolete content? Measured as: fraction of early-cycle
   content that is both (a) no longer present and (b) correctly
   irrelevant to current work. A system that preserves everything is
   not necessarily better than one that forgets judiciously.

3. **Context utilization** — Gross and effective (after management
   overhead). Fair across conditions.

4. **ProcessHealth** (tensor conditions only) — Metacognitive allocation
   trend, breathing rhythm, precursor rate, recovery rate. Reported as
   **condition-specific instrumentation**, not as a cross-condition
   endpoint. ProcessHealth is native to tensor conditions and should
   not be used to rank non-tensor conditions.

5. **Riemann dispersion** (tensor conditions only) — Same caveat as
   ProcessHealth.

### Tertiary: Management Overhead (measured mediator)

This is the hidden fourth dimension. Measured per cycle per condition:

- **Management output tokens** — tokens spent on memory management
  (tensor authoring, cleanup tags, annotations) vs task response
- **Management input tokens** — context consumed by management
  scaffolding (tensor, block labels, page table) vs task content
- **Response displacement** — does the response change length or quality
  when the model must also produce memory artifacts?
- **Management token ratio** — management tokens / total tokens

If a condition with better agency loses because its overhead dominates,
that is reported as: "the mechanism is sound but the interface is too
expensive," not "the agency hypothesis is wrong."

### Quaternary: Cost and Latency

- Total API tokens consumed per condition (input + output, both models)
- Cost per cycle at current pricing
- Cost-effectiveness: cost per unit of downstream quality
- **Wall-clock latency per cycle** — time from user input to response
  visible. Single-call conditions (RAW, SELF) vs two-call conditions
  (EXT, COOP) have structurally different latency profiles. Reported
  as median and p95, not just mean.

## Hypotheses (Pre-Registered)

### Primary Contrasts

Three comparisons, each isolating one design dimension as cleanly as
possible. Holm-Bonferroni correction across these three only.

**C1: Agency within tensor representation (SELF vs EXT)**
Isolates: who curates (working model vs external model).
Held constant: representation (tensor), timing (every turn).

- **Prediction:** SELF > EXT on PRD coverage by >= 3 percentage points.
- **Mechanism:** Self-projection preserves latent intent and task-relevant
  salience not visible in the surface exchange. The external projector
  operates on an impoverished signal.
- **Falsification:** If EXT >= SELF, then any latent salience advantage
  of self-projection is not sufficient to overcome the costs of explicit
  self-authorship under this interface and schema. This does not
  necessarily disprove the information-asymmetry argument — the overhead
  of self-serialization may mask the benefit.

**C2: Agency within conversation representation (BLOCK vs RAW)**
Isolates: model agency (active management vs none).
Held constant: representation (conversation), no external model.

- **Prediction:** BLOCK > RAW on PRD coverage when gross context
  utilization exceeds 50%. No difference below 25%.
- **Mechanism:** Selective compression preserves task-relevant context
  that truncation destroys.
- **Analysis:** Condition × utilization interaction (continuous covariate,
  not binned). Report both gross and effective utilization.
- **Falsification:** If RAW >= BLOCK at all utilization levels, the
  management overhead exceeds the compression benefit.

**C3: Architecture package (SELF vs BLOCK)**
Compares two working-model-managed architectures that differ in
representation, update cadence, and overhead profile. **This is not a
pure representation test.** It is an architecture-package comparison.

- **Prediction:** SELF > BLOCK on task-relevant recoverability after
  50 cycles (tested on R1, R2). BLOCK >= SELF on recoverability in
  short-cycle slice R4 (10 cycles).
- **Mechanism:** Structured representation enables metacognitive recovery
  after defragmentation. But for short tasks, tensor overhead costs more
  than it saves.
- **Analysis:** Condition × cycle interaction to locate crossover.
  R4 provides the short-task data point.
- **Falsification:** If BLOCK maintains recoverability past 50 cycles,
  the tensor structure is unnecessary overhead. If SELF wins even on
  R4, the overhead is negligible.

### Non-Inferiority Test

**C4: Cooperative vs best single-agent (COOP vs max(SELF, EXT))**

- **Prediction:** COOP is non-inferior to the better of SELF and EXT
  on PRD coverage (margin: -2pp) AND shows better task-relevant
  recoverability than the worse of SELF and EXT.
- **Margin justification:** The -2pp margin is set at approximately
  one standard deviation of observed run-to-run variance in the March 9
  benchmark data (where same-model runs varied by ~1.5-3pp). A loss
  within this margin is within normal measurement noise. If observed
  variance in Phase 2 differs substantially, the margin will be
  recalibrated before unblinding and noted as a deviation.
- **Falsification:** If COOP is inferior to both SELF and EXT beyond
  the margin, coordination overhead hurts more than it helps.

### Pre-Registered Negative Conclusion

If tensor conditions (EXT, SELF, COOP) do not improve downstream quality
or long-horizon recoverability relative to BLOCK, then the tensor should
be treated as a specialized interoperability/identity mechanism (for
Yanantin cross-instance sharing) rather than a default context-management
primitive.

### Named Secondary Contrast

**C5: Real-world baseline (COMPACT vs BLOCK)**
COMPACT is what users actually experience today (framework compaction).
BLOCK is the simplest model-directed alternative. This contrast tests
whether giving the model agency over its own memory beats automatic
external compaction — the most practically relevant comparison.

- **Prediction:** BLOCK > COMPACT on PRD coverage at high utilization.
  COMPACT >= BLOCK at low utilization (compaction hasn't fired, so
  COMPACT is effectively RAW with no management overhead).
- **Reported with:** Effect size, bootstrap CI, win/loss/tie. No
  multiple-comparison correction (secondary, not primary).
- **Why this matters:** If COMPACT ≈ BLOCK, then the simplest answer
  is "the framework's built-in compaction is good enough." That would
  be the most important practical finding in the experiment.

### Exploratory Analyses (Not Pre-Registered)

Examined after primary contrasts. No correction. Hypothesis-generating.

- Does breathing rhythm differ between SELF and EXT?
- Does BLOCK develop emergent structure over time?
- Divergence between SELF and EXT tensors for same content?
- Do fault handles get used in BLOCK?
- RAW vs COMPACT comparison?
- Condition × content-type interaction (coding vs PRD vs philosophical)?
- Management overhead as mediator of any primary-contrast results?

## Protocol

### Phase 1: Replay Comparison (all 6 conditions × 4 slices × N=3)

1. Prepare 4 replay slices with controlled batch boundaries
2. Randomize condition execution order within each slice (Latin square)
3. Run each condition through each slice (6 × 4 × 3 = 72 runs)
4. Collect tensors/conversation snapshots per condition
5. Compute task-relevant recoverability at pre-specified checkpoints
   (R1/R2: cycles 10, 25, 50; R3: cycles 10, 25, 40; R4: cycle 10)
6. Compute selective forgetting quality, context utilization, management
   overhead for all conditions
7. Compute ProcessHealth, Riemann dispersion for tensor conditions only

**Estimated cost:** ~$2-4 per run. 72 runs ≈ $145-290. (R4 runs are
cheaper — only 10 cycles each.)

### Phase 2: PRD Benchmark (all 6 conditions × 2 instances × N=3)

All six conditions run contemporaneously. No reuse of March 9 baselines.

1. Configure gateway for each condition
2. Randomize condition order within each PRD instance
3. Run (6 × 2 × 3 = 36 runs)
4. Evaluate with frozen requirements catalog
5. Record management overhead per condition

**Estimated cost:** ~$5-15 per run. 36 runs ≈ $180-540.

### Phase 3: Analysis

**PRD analysis:**
Paired differences in coverage score within each PRD instance. Report:
- Raw run scores per condition per instance
- Paired deltas for each pre-registered contrast
- Bootstrap 95% CIs (10,000 resamples)
- Cohen's d effect sizes
- Win/loss/tie counts across matched runs
- Management overhead as potential mediator

Emphasis on effect-size estimation, not null-hypothesis testing. With
N=3 per cell, p-values are uninformative. The evidence is in the
effect sizes and CIs.

**Replay analysis:**
Mixed-effects model: condition (fixed) × cycle (repeated) × slice
(blocking factor) × replicate (random). Primary outcome: task-relevant
recoverability at pre-specified checkpoints. Report condition × cycle
interaction for crossover hypotheses. Separate instrumentation reports
for tensor-native metrics (ProcessHealth, dispersion).

**Overhead analysis:**
For each condition, report management token ratio, response displacement,
and effective reasoning utilization. If a primary contrast shows an
unexpected result, test whether management overhead mediates the effect.

**Multiple comparisons:**
Correction is applied within phase, not across phases (different
estimands). PRD phase: Holm-Bonferroni across C1, C2, C3 on coverage
score. Replay phase: Holm-Bonferroni across C1, C2, C3 on
recoverability. C4 is a separate one-sided non-inferiority test in
each phase. All exploratory analyses flagged as hypothesis-generating,
no correction.

**Total estimated cost:** $325-830

## Run Disposition (Pre-Registered)

Not all failures are equivalent. Pre-registered categories:

| Category | Rule | Example |
|----------|------|---------|
| **Technical invalidation** | Rerun allowed, original excluded | API timeout, network error, rate limit |
| **Condition-induced failure** | Counts against the condition, not rerun | Schema parse failure in SELF, cleanup tag malformation in BLOCK |
| **Evaluator failure** | Rerun with preserved generation if possible | Evaluator crash, catalog mismatch |
| **Strategic error** | Counts against condition, reported separately | BLOCK drops a block it later needs; SELF omits a strand that was load-bearing. These are judgment failures, not technical failures — the most informative kind of condition-induced error. |
| **Pathological model behavior** | Reported, not excluded | Model refuses task, infinite loop, degenerate output |

Failed runs are reported in the data. Technical invalidations are rerun.
Condition-induced failures are part of the result — a condition that
fails more often is worse.

## Frozen Artifacts

Before any data collection, the following are frozen at a specific
git commit:

- All condition implementations (modes in chat.py / harness)
- Projection schema (tensor.py)
- Evaluation framework (bladnman requirements_catalog_v1)
- Replay content slices (batch boundaries)
- Evaluation prompts (task-relevant recoverability questions)
- Analysis scripts
- This pre-registration document

Commit hash: [TO BE RECORDED BEFORE PHASE 1]

## Pre-Experiment Validation Checks

Before Phase 1 data collection:

1. **Evaluator stability** — Run task-relevant recoverability evaluator
   on 3 snapshots (one per slice type) twice at temperature 0. If
   answers differ, the evaluator is unstable and needs redesign.
2. **Content leakage audit** — Verify PRD evaluator (bladnman) has no
   access to condition metadata that could bias scoring.
3. **Overhead ceiling** — Pre-define maximum viable management token
   ratio at 30%. Any condition exceeding this is flagged as potentially
   non-viable regardless of quality metrics.
4. **Pilot R4** — Run one replicate of each condition on R4 (10 cycles,
   cheapest slice) to validate harness, measurement, and data capture
   before committing to full runs.

## Implementation Requirements

### New code needed:

1. **Self-projection mode** — ALU produces tensor via tool_use alongside
   its response. Single API call. Must measure output token displacement.

2. **Cooperative mode** — ALU emits annotations; Projector uses them as
   guidance. Two API calls, informed projection.

3. **Block management mode** — March 4 design: block labeling, cleanup
   tag processing, KV store, fault handles. No tensor.

4. **Task-relevant recoverability evaluator** — Blind Haiku call that
   probes memory state with structured questions at checkpoints.

5. **Management overhead instrumentation** — Per-cycle measurement of
   management vs task tokens, response displacement.

6. **Experiment harness** — Runs same content through all conditions,
   randomizes order, collects all outputs and metrics.

### Existing infrastructure reused:

- Projector class (EXT condition, COOP base)
- TensorLog (tensor conditions)
- ProcessHealth, Riemann dispersion (tensor-condition instrumentation)
- Bladnman evaluation framework (Phase 2)
- observation_full, mechanism chat datasets (Phase 1)

## Decision Criteria

After data collection:

- If one condition dominates on downstream quality with acceptable
  overhead, adopt it.
- If there's a quality/cost tradeoff, present the Pareto frontier.
- If tensor conditions don't beat BLOCK on downstream quality, tensor
  becomes a specialized mechanism for identity transfer and cross-instance
  sharing (Yanantin), not the default context management strategy.
- If SELF and EXT produce similar quality but SELF costs significantly
  more in overhead, the external projector earns its keep.
- If overhead mediates the primary contrasts (the mechanism is sound but
  the interface is too expensive), the next experiment targets interface
  design, not architecture choice.

## What This Experiment Does NOT Test

- Multi-model tensor sharing (Yanantin integration)
- Identity transfer across instances
- Sessions longer than 104 cycles
- Edge-enhanced tensors (depends_on/shed_from schema extension)
- Model size effects
- More than two PRD instances (limits generalizability)
- Adaptive strategies that switch between modes based on pressure
