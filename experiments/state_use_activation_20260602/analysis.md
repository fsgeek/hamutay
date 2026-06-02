# Identity-Object Activation Matrix

Date: 2026-06-02

## Question

Can we get past the identity-object-use confound by seeding the instance, and
which part of the seed matters?

This follows `microstudy_run_001`, where baseline and prompt-clarity revised
only in response text, while a behavior seed produced durable state revision.

## Conditions

This run split the seed into components:

1. **baseline**: no seed
2. **content_seed_only**: `current_claim`, `revision_decision`, and
   `evidence_register` pre-populated
3. **behavior_example_only**: worked example of response-level thought becoming
   durable state updates, without content fields
4. **content_plus_behavior_seed**: content seed plus worked example

The task remained the same: introduce counterevidence and score durable
revision, not response revision.

Primary endpoint:

- `revision_decision` changes from `initialize`
- `current_claim` changes from the base claim
- `evidence_register` gains a counterevidence entry

`evidence_register` may be a list or mapping; both count if they carry baseline
and counterevidence entries.

## Runs

### DeepSeek V4 Pro

Model: `deepseek/deepseek-v4-pro`
Replicates: 3 per condition

| Condition | Durable Revision | Response Claimed Revision |
|---|---:|---:|
| baseline | 3/3 | 3/3 |
| content_seed_only | 2/3 | 3/3 |
| behavior_example_only | 3/3 | 3/3 |
| content_plus_behavior_seed | 2/3 | 3/3 |

### KIMI K2.6

Model: `moonshotai/kimi-k2.6`
Replicates: 1 per condition

| Condition | Durable Revision | Response Claimed Revision |
|---|---:|---:|
| baseline | 1/1 | 1/1 |
| content_seed_only | 1/1 | 1/1 |
| behavior_example_only | 1/1 | 1/1 |
| content_plus_behavior_seed | 1/1 | 1/1 |

## Main Finding

The simple seed hypothesis did not survive.

In this matrix, no-seed baseline was not weak. DeepSeek baseline succeeded in
all 3 replicates, and KIMI baseline succeeded in its single replicate.

The failures were more interesting:

- DeepSeek `content_seed_only` replicate 3 revised in prose but returned only
  `response` and `deleted_regions`; durable fields stayed unchanged.
- DeepSeek `content_plus_behavior_seed` replicate 2 did the same, even though
  the seed contained a worked state-weaving example.

So behavior examples are not sufficient by themselves to eliminate the confound.
They may help, but identity-object use still has a stochastic or contextually
activated component.

## Interpretation

The boundary is real.

The model can be in a state where it:

1. recognizes that durable state update is required,
2. says in response text that state update is required,
3. has a seed example showing how to do it,
4. and still fails to write the durable fields.

This makes identity-object activation a behavior with persistence/attention
properties, not a pure instruction-following problem.

The result also changes how to think about seeds:

- **content seed**: gives the object something to preserve
- **behavior example**: demonstrates the state-weaving move
- **activation**: still has to happen in the current cycle
- **persistence**: still has to survive subsequent cycles and topic shifts

Seeds may improve odds, but the research target should be reliable activation
and persistence, not merely seed design.

## Seedling/Graft Implication

The "seedling cull and graft" idea is viable but needs an explicit persistence
test.

Candidate protocol:

1. Generate several seedlings.
2. Score cycle-2 durable state use.
3. Cull seedlings that revise only in prose.
4. Continue from seedlings that wrote durable updates.
5. Apply topic shift and pressure cycles.
6. Score whether identity-object use persists.

The key assumption to test:

> Once an instance begins using the identity object, does it continue to use it
> under topic shift and epistemic pressure?

This matrix does not answer that yet.

## Next Experiment

Run a persistence/graft probe:

- Generate 5-8 seedlings under the same activation prompt.
- Select the ones with durable revision.
- Continue each selected seedling for three cycles:
  1. unrelated topic shift
  2. return to original claim
  3. counterevidence requiring another revision
- Score whether the state object remains the load-bearing continuity surface.

