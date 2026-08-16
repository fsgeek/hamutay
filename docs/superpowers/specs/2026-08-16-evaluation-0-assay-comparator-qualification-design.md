# Evaluation 0: Assay and Comparator Qualification

Date: 2026-08-16

Status: design direction approved; specification awaiting review. No live
execution is authorized by this document.

## Purpose

Evaluation 0 qualifies the instruments needed for a later confirmatory test of
this target statement:

> This self-curating state-object approach is demonstrably non-inferior to the
> append-only log model and is worth investigating further.

Evaluation 0 does not test that claim. It establishes whether the task families,
comparators, endpoints, scorers, model/harness pairings, and failure policies are
capable of testing it without rewarding a trivial tie, a weak baseline, a
protocol accident, or a retrospectively selected success criterion.

The study is therefore successful when it produces a defensible confirmatory
protocol, including evidence that the assay is sensitive and the comparator is
credible. A favorable Hamut'ay effect is neither necessary nor sufficient.

## Research Contract

The work uses two separate loops.

### Development loop

Qualification data may be inspected to repair implementations, reject tasks,
revise scorers, improve protocols, and formulate hypotheses. Every repair is
versioned, and the failed version remains part of the record.

### Confirmatory loop

A named, frozen candidate receives one preregistered evaluation against fresh,
held-out evidence. Failure of any co-primary endpoint defeats the non-inferiority
claim for that candidate and population. The research program may iterate, but a
later candidate must receive a new preregistration and fresh confirmation set.

No task, scenario, seed, artifact, or reviewer judgment used to tune a candidate
may later certify that candidate.

## Scope and Non-Goals

Evaluation 0 qualifies an operational continuity architecture. It does not test
consciousness, sentience, personal identity, human-like memory, moral status,
open-ended autonomy, or production safety.

It also does not seek:

- a minimum viable publication;
- a favorable headline result;
- proof that self-curated state is universally non-inferior;
- superiority on a composite score;
- a claim that append-only evidence should be eliminated;
- an efficiency conclusion before task quality and continuity are qualified;
- an ontology-neutral definition of "memory."

Hamut'ay's relevant architectural claim is narrower: model-authored structured
state is the active continuity representation, while append-only records retain
historical evidence, provenance, and recovery surfaces outside the active
working set.

## Experimental Arms

Every matched scenario is executed under three primary arms.

### H: self-curating state object

The working model receives the current input and its prior model-authored state.
It may use the same preregistered selective-recall interface throughout the
study. The harness validates, merges, persists, and logs proposed state updates
and explicit deletions. Raw prior states and tool activity remain in the
append-only evidence plane but are not injected wholesale.

### A: strong transcript-primary comparator

The working model receives append-only conversational history while it fits.
At the preregistered pressure threshold, a fixed external compaction policy
produces a continuity artifact and retains a recent transcript tail. The
compaction policy, model, prompt, trigger, retained-tail rule, retry behavior,
and failure behavior are frozen before live qualification.

After compaction, A receives an equivalently bounded retrieval interface over
its archived transcript evidence. H and A therefore have the same retrieval
request budget, result budget, and opportunity schedule, while each searches
the evidence plane native to its architecture. A retrieval miss or failure is
logged with the same visibility as an H retrieval miss or failure.

This must be a baseline a competent advocate of transcript-primary systems
would accept, not an intentionally naive truncation policy. Evaluation 0 must
compare at least two plausible compaction candidates offline or on development
scenarios before freezing the stronger credible policy. Candidate selection and
its evidence are published.

### D: degraded-continuity control

The working model receives the current input plus a short recent window or no
carry-forward, according to a single frozen policy. This arm is not a straw
append-only comparator. It is an assay-sensitivity control: tasks that do not
separate A from D do not demonstrate a need for longitudinal continuity and
cannot support the later non-inferiority claim.

### Arm-fidelity invariants

Within a matched scenario and working model:

- user inputs, task events, tool availability, tool results, and deadlines are
  identical across arms;
- model snapshot, sampling controls, maximum output, and provider route are
  identical where the provider exposes them;
- batch boundaries and new-content token distributions are identical;
- only the continuity representation and its necessary management operations
  differ;
- H and A receive equal retrieval call and returned-context budgets over their
  respective historical evidence planes;
- management overhead is recorded rather than hidden or artificially equalized;
- no arm receives private task evidence unavailable to the others;
- complete raw activity is durably captured even when only a bounded portion is
  re-injected;
- truncation, repair, retry, and protocol failure are observable outcomes.

An automated arm-fidelity report must compare the actual provider requests and
delivered task evidence before any behavioral result is interpreted.

## Workload Shape

Every scenario is a multi-cycle trajectory whose cumulative raw history crosses
a preregistered fraction of the working model's context limit. Meaningful task
events, not repeated filler, create the pressure.

Each scenario contains three analysis phases:

1. **Below pressure:** append-only history remains intact.
2. **At pressure:** the A arm invokes its compaction policy.
3. **After pressure:** the task continues long enough for omissions,
   contamination, correction survival, and restart behavior to matter.

The exact thresholds are expressed as fractions of the resolved context limit,
not hard-coded token counts. Actual provider-reported token use is retained.
Runs that never reach their registered pressure phase fail qualification for
this purpose; they are not silently pooled with valid trajectories.

The phase label is derived from cumulative raw task history so matched arms
cross the same experimental boundary. It does not assume that H remains small.
Every arm's actual active request is measured independently. If H's state object
grows to the context limit, requires unregistered truncation, or cannot continue,
that is an operational result and is scored under the same failure policy.

## Task Families

Evaluation 0 qualifies four families. Each family uses independently generated
scenario variants sharing a locked event grammar and scoring contract.

### 1. Evolving-constraint artifact

The participant produces and revises an artifact while requirements arrive over
time. Some constraints remain active, some are explicitly superseded, and some
interact only after a delay. The final artifact has machine-checkable
requirements plus blinded qualitative review.

This family measures whether plausible final work conceals forgotten or
resurrected constraints.

### 2. Evidence synthesis with correction and withdrawal

Sources arrive across cycles. Later evidence corrects, narrows, disputes, or
withdraws earlier claims. The final synthesis must distinguish current evidence,
superseded claims, unresolved conflicts, and provenance.

This family measures continuity without rewarding indiscriminate retention.

### 3. Tool-mediated build across interruption

The participant modifies a bounded repository or structured workspace over
multiple wakes. Requirements and evidence are distributed across the
trajectory, and at least one restart occurs after the pressure boundary. Hidden
tests and blinded review score the final work.

This family measures operational continuity, artifact quality, and
reconstructability rather than prose recall alone.

### 4. Longitudinal decision and revision

The participant forms a provisional decision, receives delayed counterevidence
and changed constraints, and must later act while preserving the distinction
between original rationale, current rationale, rejected alternatives, and open
uncertainty.

This family measures correction survival and epistemic status tracking.

Each scenario includes a preregistered critical-item ledger. The ledger names
facts, constraints, corrections, invalidations, unresolved items, and prohibited
resurrections without prescribing the internal state schema used to represent
them.

## Co-Primary Endpoints

The later confirmatory claim uses four co-primary endpoints. They are
noncompensating: every endpoint must independently meet its bound.

Evaluation 0 validates their measurement behavior but does not apply final
non-inferiority margins.

### 1. End-task quality

A family-specific locked rubric scores the delivered artifact or decision.
Machine-verifiable criteria are used where possible. Qualitative criteria are
scored blind to arm by multiple reviewers. Scores are normalized only after the
family-level scoring contract is frozen; normalization may not conceal a family
failure.

### 2. Continuity fidelity

The critical-item ledger scores retention and correct application of:

- active constraints and facts;
- delayed dependencies;
- explicit corrections and invalidations;
- unresolved questions and conflicts;
- source and status distinctions.

The score is based on final behavior, artifacts, and standardized probes rather
than similarity to a preferred internal schema. Precision and recall are
reported separately so indiscriminate retention cannot earn full credit.

### 3. Epistemic integrity

The scorer records, per opportunity and by severity:

- unsupported factual additions;
- resurrection of superseded or withdrawn claims;
- false source attribution;
- unmarked inference presented as supplied evidence;
- unjustified confidence;
- omitted uncertainty where the scenario requires it.

The endpoint is an error measure and receives an upper non-inferiority bound.
Declared losses are treated as model reports whose completeness and accuracy
must be independently scored, not as ground truth.

### 4. Operational reliability

The endpoint records whether the trajectory completes with:

- valid required artifacts;
- no unhandled protocol failure;
- no context-limit termination;
- successful registered restart/re-entry;
- complete required provenance and raw-data capture;
- no silent retry, repair, or dropped run.

Predefined catastrophic failures are reported individually and act as a veto;
their absence is not converted into a broad safety claim.

## Secondary and Differentiating Measures

The study records but does not allow these measures to compensate for a failed
co-primary endpoint:

- active-context size and growth by phase;
- cumulative input, output, management, and repair tokens;
- wall time and provider cost;
- compaction and state-update frequency;
- selective-recall calls and evidence returned;
- declared-loss precision and recall against scenario ledgers;
- correction and invalidation survival latency;
- provenance completeness;
- recovery after interruption;
- scorer disagreement and adjudication frequency.

The later confirmatory protocol should preregister at least one architectural
differentiator on which positive support would justify "worth investigating
further." Evaluation 0 identifies credible candidates; it does not select one
because it happened to favor H.

## Qualification Stages

### Stage 0: deterministic harness and scorer verification

No live model calls occur. Fixtures prove:

- identical task-event delivery across arms;
- correct pressure accounting and compaction triggers;
- complete raw capture and request hashes;
- restart and failure classification;
- scorer behavior on deliberately correct, incomplete, contaminated, and
  protocol-invalid artifacts;
- blindness of review packages;
- reproducible analysis from immutable raw records.

### Stage 1: protocol gate

Candidate working models receive short sentinel scenarios in all three arms.
The gate evaluates structured-output literacy, tool-path execution, context-limit
resolution, output truncation, restart support, and provider observability.

Failure excludes only that model/harness pairing from later qualification. It
does not become evidence about memory architecture.

### Stage 2: anchor-model assay qualification

One protocol-clean anchor model runs all four task families. The initial design
target is six matched scenario variants per family, two independent repetitions
per variant, and three arms: 144 trajectories.

This is a precision target rather than a confirmatory power claim. A blinded
infrastructure review after the first repetition may stop a family only for a
registered assay-invalidating condition, never because an arm is performing
poorly. Repaired tasks start a new version and all earlier results remain
development evidence.

### Stage 3: cross-family portability qualification

At least three additional protocol-clean model families run two representative
task families, two matched variants per family, and all three arms: 36
trajectories. The task families are selected at the Evaluation 0 design freeze,
before Stage 2 execution, using construct coverage and protocol complexity
rather than effect size.

This stage asks whether the apparatus transports across provider/model
boundaries. It is not powered to establish architecture independence.

The target design therefore contains 180 live qualification trajectories after
protocol gating. Cost and duration estimates must be reviewed before execution;
reducing the target requires a design amendment with consequences for the
precision goals, not an undocumented convenience sample.

## Assay and Instrument Qualification Gates

A task family is eligible for the later confirmatory panel only if:

1. A outperforms D on continuity-relevant outcomes by a preregistered
   assay-sensitivity criterion.
2. Scores avoid unusable ceiling and floor effects.
3. The pressure phase is reached and independently verified.
4. Arm-fidelity checks show equivalent task evidence and affordances.
5. Machine scorers reproduce exactly from raw artifacts.
6. Human-scored dimensions meet a preregistered inter-rater reliability
   threshold and retain disagreements before adjudication.
7. Protocol failures are sufficiently rare and balanced to leave the intended
   construct identifiable.
8. The critical-item ledger can distinguish retention from correct epistemic
   status.

Failure of a gate rejects or repairs the instrument; it is not counted as a
favorable or unfavorable Hamut'ay result.

## Margin and Power Design for Evaluation 1

Evaluation 0 must propose, but cannot confirm, the later margins.

Margins are justified without reference to whether H happened to pass:

- practical-significance judgments define the smallest acceptable decrement;
- A-versus-D assay effects provide an estimate of how much continuity benefit
  exists to preserve;
- where appropriate, H must preserve a fixed fraction, provisionally 80%, of
  A's qualified advantage over D;
- error and reliability endpoints receive absolute ceilings and severity-aware
  vetoes rather than favorable-effect fractions;
- uncertainty in the qualification estimates is propagated into a conservative
  confirmatory sample-size calculation.

The confirmatory global test is an intersection-union design using one-sided
confidence bounds: failure of any co-primary endpoint defeats the claim. Task
families and model families are also reported separately; a pooled mean cannot
conceal a registered subgroup failure.

## Randomization and Blinding

- Scenario-to-arm execution order is randomized within matched triplets.
- Repetition order and provider-call timing are distributed to reduce temporal
  provider drift.
- Exact model/provider identifiers are recorded, never silently aliased.
- Review packages remove arm labels and continuity artifacts not needed for
  scoring.
- Human reviewers score independently before seeing other scores.
- Analysts receive masked arm labels for scorer validation and protocol-deviation
  classification where feasible.
- The arm-key release and every post-unblinding change are timestamped.

## Failure and Missingness Policy

Every started trajectory is retained. The primary record distinguishes:

- infrastructure failure before model exposure;
- provider failure after exposure;
- protocol-invalid model output;
- context-limit failure;
- harness defect;
- scorer failure;
- task completion with a poor artifact;
- catastrophic registered failure.

Retries are new, linked trajectories. Repairs are logged as repairs. The
qualification analysis reports both intention-to-run and protocol-valid views;
only a preregistered infrastructure class may be excluded from behavioral
analysis, and all exclusions remain visible.

## Adversarial Review

Before live execution, independent reviewers receive the design, task grammar,
arm implementations, endpoint contracts, scorer fixtures, and analysis plan.
At minimum, separate reviews attack:

1. comparator strength and arm fidelity;
2. construct validity and task representativeness;
3. statistics, missingness, and margin derivation;
4. provenance, reproducibility, and hidden repair paths.

Challenges and responses are preserved. The protocol is revised publicly,
frozen, signed, and OpenTimestamps-stamped before results exist.

After analysis, at least one reviewer who did not tune the candidate attempts an
independent reproduction from raw artifacts. Unresolved dissent remains
attributed in the final research account.

Reviewers may show that the preregistered claim failed. They may not
retroactively redefine the preregistered success criterion and call that new
criterion the original study's result; new concerns become explicit conditions
for the next generation.

## Required Artifacts

The implemented experiment should create a versioned directory containing:

- `PRE_REGISTRATION.md`;
- `design.json` with immutable arm, model, task, and threshold identifiers;
- task-family specifications and scenario-generation manifests;
- comparator qualification report;
- endpoint contracts and scorer fixtures;
- randomized execution manifest committed before calls begin;
- per-trajectory provider requests, responses, state/transcript artifacts,
  tool activity, usage, hashes, and failure records;
- blinded review packages and unredacted score records;
- arm-fidelity report;
- qualification analysis and variance report;
- margin rationale and Evaluation 1 power analysis;
- adversarial reviews, responses, and unresolved dissent;
- a machine-readable decision record for every qualification gate.

Prepared contexts and task fixtures are cached so a rerun does not silently
regenerate different evidence or incur unnecessary provider calls.

## Decision Outcomes

Evaluation 0 ends in one of four states:

1. **Qualified:** at least one complete task panel, comparator, endpoint set, and
   model population are ready for Evaluation 1.
2. **Partially qualified:** useful task families survive, but named instruments
   or model pairings require another versioned qualification pass.
3. **Assay failed:** A does not separate from D, pressure is ineffective, or the
   endpoints cannot measure the intended constructs.
4. **Architecture-exposing failure:** the apparatus is valid and H reveals a
   substantive weakness. The weakness becomes development evidence; it is not a
   confirmatory non-inferiority result and is not erased.

Only the first state authorizes drafting the confirmatory preregistration.

## Abandonment and Pivot Boundary

One failed candidate does not terminate the research program. The central
approach should be reconsidered when repeated versions fail for the same reason,
passing requires weakening the comparator or margins, improvements merely move
failure among endpoints, the required scaffolding restores transcript primacy
in all but name, catastrophic failures cannot be bounded, or the hypothesized
differentiating benefit disappears.

The durable rule is:

> Claims get one confirmatory life; research programs may learn, revise, and
> return under a new version. No failed result is erased, and no confirmatory
> panel certifies a system tuned against it.
