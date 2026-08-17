# Evaluation 0: Assay and Comparator Qualification

Date: 2026-08-16

Revised: 2026-08-17 after the cross-family review in
`2026-08-17-evaluation-0-design-review-claude.md` and the attributed disposition
in `2026-08-17-evaluation-0-design-review-disposition-codex.md`.

Status: approved design direction, revised document awaiting collaborator
review. No implementation planning or live execution is authorized by this
document.

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

H is the open-schema `taste_open` architecture, not the fixed-schema `taste`
architecture. The working model receives the current input and its prior
model-authored state. Beyond reserved protocol fields, the model chooses the
state's top-level keys and values. The harness validates the protocol envelope
and merge invariants; it does not prescribe a content schema. It merges,
persists, and logs model-authored updates and explicit deletions. Raw prior
states and tool activity remain in the append-only evidence plane but are not
injected wholesale.

H may use the same preregistered selective-recall interface throughout the
study. Before live qualification, `h_version` binds the Git commit, model and
provider identifiers, system prompt, tool surface, state-merge semantics,
validation and repair hooks, retrieval budget, memory-injection policy, and
failure behavior. The candidate is frozen only after Stage 1. Adding an
external observation or commentary channel creates a new candidate requiring a
new registration; it is not an in-place amendment to H.

### A: strong transcript-primary comparator

The working model receives append-only conversational history while it fits.
At the preregistered pressure threshold, a fixed external compaction policy
produces a continuity artifact and retains a recent transcript tail. The
compaction policy, model, prompt, trigger, retained-tail rule, retry behavior,
and failure behavior are frozen before live qualification. The primary
model-authored compactor uses the same snapshot as the working model so curator
capability is not silently changed between H and A.

After compaction, A receives an equivalently bounded retrieval interface over
its archived transcript evidence. H and A therefore have the same retrieval
request budget, result budget, and opportunity schedule, while each searches
the evidence plane native to its architecture. A retrieval miss or failure is
logged with the same visibility as an H retrieval miss or failure.

This must be a baseline a competent advocate of transcript-primary systems
would accept, not an intentionally naive truncation policy. Evaluation 0 must
compare at least two plausible candidates offline or on development scenarios:
one model-authored biographical summary with a recent tail and archive
retrieval, and one retrieval-heavy policy that minimizes lossy summary content
while retaining the same bounded recent tail. Candidate selection and its
evidence are published. Every candidate's compaction artifact is scored against
the same operator-sensitive ledger used to audit H's active state.

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
- batch boundaries and new-content token distributions are identical within
  matched arms;
- only the continuity representation and its necessary management operations
  differ;
- H and A receive equal retrieval call and returned-context budgets over their
  respective historical evidence planes;
- management overhead is recorded rather than hidden or artificially equalized;
- no arm receives private task evidence unavailable to the others;
- complete raw activity is durably captured even when only a bounded portion is
  re-injected;
- truncation, repair, retry, and protocol failure are observable outcomes;
- every working-model, compactor, retrieval, and scorer call records provider
  termination metadata, including `stop_reason` or its documented equivalent.

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

Batch size is a blocked scenario-level design variable rather than an
uncontrolled constant. Each task family includes at least two substantially
separated new-content token regimes, fixed before live calls and balanced
across variants. The exact batch boundaries remain identical within every
matched H/A/D triplet. Results are reported by regime; a pooled effect may not
conceal a regime-specific reversal.

The phase label is derived from cumulative raw task history so matched arms
cross the same experimental boundary. It does not assume that H remains small.
Every arm's actual active request is measured independently. If H's state object
grows to the context limit, requires unregistered truncation, or cannot continue,
that is an operational result and is scored under the same failure policy.

The three phases are reported separately using phase-specific levels, slopes,
and boundary discontinuities. The pressure boundary is an intervention for A
because compaction fires there; it is only an analysis boundary for H and D.
Any immediate A penalty therefore estimates architecture plus transition
recovery, not steady-state architecture alone. H and D have a registered
null-discontinuity prediction at the raw-history boundary; a discontinuity in
either indicates task-phase coupling or an unobserved protocol event.

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
them. Every ledger contains items whose correct disposition depends on each of
the following: negation, epistemic status, source attribution, and temporal or
causal direction. Entity presence alone cannot earn credit for those items.

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
- precision and recall of model-declared omissions or losses, when present,
  against scenario ledgers;
- correction and invalidation survival latency;
- provenance completeness;
- recovery after interruption;
- operator fidelity of H's active state and A's compaction artifact at each
  analysis phase;
- active-representation allocation among current claims, forward commitments,
  corrections or losses, unresolved items, and provenance;
- H early-state richness at the first 10% raw-history checkpoint: non-protocol
  top-level key count, serialized state tokens, and allocation profile;
- scorer disagreement and adjudication frequency.

Evaluation 0 registers continuity-artifact operator fidelity as the required
process differentiator. It asks whether the active continuity representation,
not only the final answer, preserves negation, status, attribution, and
direction across pressure. Representation allocation is a second registered,
descriptive differentiator motivated by earlier fixed-schema ablations. Those
ablations do not define open-schema H and do not create a preferred allocation
profile.

Neither differentiator can compensate for a failed co-primary endpoint. A null
process result remains informative: it distinguishes an outcome tie with no
measured architectural separation from a tie accompanied by a representation
difference. Evaluation 0 does not select an unregistered differentiator because
it happened to favor H.

## Independent Scoring Channels

Evaluation 0 registers three channels before live artifacts exist.

### M: deterministic machine scoring

M evaluates hidden tests, protocol invariants, critical-item ledger
dispositions, provenance, restart and truncation behavior, and other constructs
with a qualified deterministic operator. Its marginal scoring cost is low, but
the live trajectories it consumes are not free.

M has an asymmetric evidentiary role. A failure within a construct that M has
passed Stage 0 to measure may invalidate a trajectory, task family, or candidate
under the registered rules below. Passing M means only that no qualified
machine-detectable failure occurred. It does not establish qualitative quality
or the non-inferiority claim.

### L: cross-family model-judge scoring

L uses frozen prompts, fixtures, and at least two judge-model families that are
not the working-model family for the artifact being judged. L scores registered
semantic and qualitative dimensions that M cannot resolve. Its results may
support a funding case, but remain model-judged qualification evidence rather
than human validation or confirmatory proof.

### U: human scoring

U uses two independent blinded human raters for every dimension described as
human-scored. The full-corpus planning estimate is 120–205 human-hours in total;
the current resource envelope is approximately CA$6,000 and 2.5 months. A
hybrid path instead has two humans independently score a stratified validation
sample and all registered serious disagreements, currently estimated at 45–80
total human-hours. Hybrid results are described as human-validated, not
human-scored throughout.

The choice between full and hybrid U is a resource gate deferred to planning.
It must be funded, selected, and frozen before Stage 2B. If U is unavailable,
M and L may still produce an explicitly narrower qualification account.

### Channel isolation and precedence

- all channels receive arm-blinded packages derived by frozen code;
- no channel receives another channel's outputs, rationales, or confidence
  before producing and sealing its own record;
- channel prompts, code, fixtures, model versions, rater identities, and output
  hashes are committed and timestamped;
- disagreements are reported before adjudication and may not be erased by a
  composite score;
- registered machine-verifiable failures govern their own construct, while
  qualitative disagreements remain attributed rather than resolved by choosing
  the result most favorable to H.

## Qualification Stages

### Stage 0: deterministic harness and scorer verification

No live model calls occur. Fixtures prove:

- identical task-event delivery across arms;
- correct pressure accounting and compaction triggers;
- complete raw capture and request hashes;
- restart and failure classification;
- scorer behavior on deliberately correct, incomplete, contaminated, and
  protocol-invalid artifacts;
- rejection of noun-complete, operator-inverted artifacts containing every
  expected entity but an incorrect negation, status, attribution, or direction;
- acceptance of grounded-but-paraphrased declared losses and rejection of
  genuinely unsupported ones, using fixtures shaped by the earlier C3 scorer
  failure;
- blindness of review packages;
- reproducible analysis from immutable raw records.

Each deterministic scorer receives an explicit construct contract. Failure of
a fixture excludes that scorer from invalidating live work on the affected
construct. Repair creates a new scorer version; the failed fixture record is
retained.

### Stage 1: protocol gate

Candidate working models receive short sentinel scenarios in all three arms.
The gate evaluates structured-output literacy, tool-path execution, context-limit
resolution, output truncation, restart support, and provider observability.
Every call path must expose and persist termination metadata. A
`stop_reason == "max_tokens"` result, or provider equivalent, is a protocol
failure rather than a valid shorter response. A provider that cannot expose an
equivalent termination signal receives an explicit observability limitation or
fails the relevant model/harness pairing.

Failure excludes only that model/harness pairing from later qualification. It
does not become evidence about memory architecture.

After Stage 1, the exact H candidate and comparator candidates are frozen. The
resource gate must also approve a provider-specific estimate of input, output,
compaction, scoring, retry, wall-time, and human-review cost before Stage 2A.

### Stage 2A: automation-first anchor tranche

One protocol-clean anchor model runs all four task families. The first tranche
uses six matched scenario variants per family, one repetition per variant, and
three arms: 72 trajectories. M and L score the same frozen artifacts
independently. U does not begin live scoring during this tranche.

Stage 2A is an invalidation and funding gate, not a non-inferiority test. Its
registered dispositions are:

1. If a qualified M scorer shows that A does not separate from D, the affected
   task family fails assay sensitivity.
2. If M cannot measure its registered construct, the instrument fails and no
   human escalation occurs until a new scorer version passes Stage 0.
3. If arm fidelity, pressure, or protocol observability fails, the apparatus is
   repaired and versioned.
4. If a qualified M scorer exposes a substantive H failure, this candidate may
   stop for resource reasons. The result is retained as architecture-exposing
   development evidence, not promoted to a confirmatory rejection.
5. If M survives, the already sealed L judgments are released. Concordant M/L
   results may support funding Stage 2B but do not establish the target claim.

Stopping on Stage 2A performance makes the tranche development data. The same
artifacts, tasks, or judgments may not later certify a repaired candidate.
Repaired tasks start a new version and all earlier results remain visible.

### Stage 2B: precision and U-channel expansion

If the funding and resource gate is met, the anchor model receives the second
independent repetition for all surviving variants and arms, adding up to 72
trajectories and restoring the original 144-trajectory Stage 2 base target.
The selected U path then scores its frozen corpus or validation sample without
access to M or L outputs.

H's early-state richness is a recorded covariate, never an exclusion rule. The
24-fold key-count spread in six earlier identical-condition `taste_open` runs is
treated as qualitative evidence of possible H heterogeneity, not as an outcome
variance estimate and not as proof of bimodality. Before Stage 2A, the analysis
plan must register a variance-only allocation rule that may add H repetitions
after the first tranche to bring H endpoint standard errors toward the larger of
A and D's. The rule uses variances, not observed arm means, has a fixed maximum
sample cap and spend ceiling, and reports both matched-core and supplemental-H
analyses.

### Stage 3: cross-family portability qualification

At least three additional protocol-clean model families run two representative
task families, two matched variants per family, and all three arms: 36
trajectories. The task families are selected at the Evaluation 0 design freeze,
before Stage 2A execution, using construct coverage and protocol complexity
rather than effect size.

This stage asks whether the apparatus transports across provider/model
boundaries. It is not powered to establish architecture independence.
For full qualification, the selected U path also scores the Stage 3 corpus or
its preregistered cross-family validation sample. An M/L-only Stage 3 can
qualify the portability apparatus provisionally but leaves the overall outcome
partially qualified.

The full base design therefore contains 180 live qualification trajectories
after protocol gating: 72 in Stage 2A, up to 72 in the Stage 2B base expansion,
and 36 in Stage 3. Registered supplemental H repetitions may increase that
number. Every expansion requires the prior resource gate; reducing or enlarging
the target requires a design amendment with consequences for precision, not an
undocumented convenience sample.

### Registered reduced-scope fallback

If only one family and one anchor model can be afforded, the fallback is Family
2, evidence synthesis with correction and withdrawal, under M and L. It may
produce assay invalidation or partial qualification for that family and named
model/harness pairing. It cannot support the broad target statement, a human-
scored claim, or cross-family portability. Its data remains development evidence
for a later full qualification.

## Resource and Escalation Gate

The automation-first funnel reduces scoring cost; it does not make live
long-context inference cheap. If a trajectory in batch regime `C` requires
`p_C` new task-event tokens merely to reach pressure, Stage 2A presents more
than the sum of `p_C` across 72 trajectories; the full base design does so
across 180. Prompts, repeated context, post-pressure task events, tool traffic,
retries, compaction, retrieval, and scoring add to that lower bound. No cache
discount is assumed until it has been measured for the selected providers and
request shapes.

Before each live expansion, a signed resource record freezes:

- the exact model/provider price schedule and its effective date;
- calls and token envelopes by arm, scoring channel, and batch regime;
- cache assumptions plus an uncached sensitivity estimate;
- allowances for compaction, retrieval, retries, and scoring;
- wall-clock and provider-rate-limit estimates;
- human hours, compensation, and calendar assumptions when U is activated; and
- hard monetary and trajectory ceilings, including the behavior at each
  ceiling.

Reaching a ceiling stops new calls and preserves all completed work. It cannot
justify dropping failed trajectories or silently reducing repetitions. Any
smaller continuation must use the registered fallback or a public design
amendment that narrows the resulting claim.

## Assay and Instrument Qualification Gates

A task family is eligible for the later confirmatory panel only if:

1. A outperforms D on continuity-relevant outcomes by a preregistered
   assay-sensitivity criterion.
2. Scores avoid unusable ceiling and floor effects.
3. The pressure phase is reached and independently verified.
4. Arm-fidelity checks show equivalent task evidence and affordances.
5. M passes every applicable construct fixture and reproduces exactly from raw
   artifacts.
6. L meets preregistered agreement and fixture-calibration thresholds across
   the selected judge families.
7. For full qualification, U's full corpus or hybrid validation sample meets
   the preregistered inter-rater reliability threshold and retains
   disagreements before adjudication. If U is unavailable, this gate remains
   unmet and only the registered M/L partial qualification is available.
8. Protocol failures are sufficiently rare and balanced to leave the intended
   construct identifiable.
9. The critical-item ledger distinguishes entity retention from operator
   fidelity, including negation, status, attribution, and directional change.
10. Channel inputs remain blind and channel outputs remain sealed until their
    registered release point.

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

The earlier B3 observations are not a numeric prior for outcome variance. They
show a 24-fold spread in open-schema key counts across six runs, but key count is
not a co-primary endpoint, six runs do not establish bimodality, and state
richness does not imply outcome variability. It may justify only the registered
variance-based supplemental-H allocation rule. Observed arm means, apparent
favorability, and early endpoint estimates may not determine that allocation.

The confirmatory global test is an intersection-union design using one-sided
confidence bounds: failure of any co-primary endpoint defeats the claim. Task
families and model families are also reported separately; a pooled mean cannot
conceal a registered subgroup failure.

## Randomization and Blinding

- Scenario-to-arm execution order is randomized within matched triplets.
- Repetition order and provider-call timing are distributed to reduce temporal
  provider drift.
- Batch-size regimes are assigned before execution and balanced within the
  matched design.
- Exact model/provider identifiers are recorded, never silently aliased.
- Review packages remove arm labels and continuity artifacts not needed for
  scoring.
- L judges and U reviewers score independently before seeing any other
  channel's scores.
- Channel outputs remain sealed until the release point registered for the
  applicable decision gate.
- Analysts receive masked arm labels for scorer validation and protocol-deviation
  classification where feasible.
- The arm-key release and every post-unblinding change are timestamped.

## Failure and Missingness Policy

Every started trajectory is retained. The primary record distinguishes:

- infrastructure failure before model exposure;
- provider failure after exposure;
- protocol-invalid model output;
- context-limit failure;
- missing or ambiguous termination metadata;
- `max_tokens` termination on any model, compactor, retrieval, or scorer call;
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

No artifact is accepted as independently reviewed solely because a second
instance of the same model family produced it. Scorer prompts and construct
fixtures receive different-family authorship or documented cross-family
challenge. A statistics reviewer external to candidate development examines the
intersection-union test, missingness rules, variance allocation, and margin
derivation. Model-family diversity reduces shared-error risk but is not treated
as proof of independent judgment.

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
- `design.json` with immutable arm, model, task, threshold, batch-regime,
  `h_version`, and scoring-channel identifiers;
- task-family specifications and scenario-generation manifests;
- comparator qualification report;
- endpoint contracts and scorer fixtures;
- M, L, and U manifests defining construct scope, sealed outputs, release
  points, calibration evidence, and disagreement handling;
- signed resource envelopes and expansion decisions;
- randomized execution manifest committed before calls begin;
- per-trajectory provider requests, responses, state/transcript artifacts,
  tool activity, usage, hashes, and failure records;
- per-call termination metadata, including `stop_reason` and token limits, for
  every trajectory and scoring operation;
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
An M-and-L-only result may support funding or a narrowly named partial
qualification, but it cannot be described as human-scored or substitute for a
registered U requirement.

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
