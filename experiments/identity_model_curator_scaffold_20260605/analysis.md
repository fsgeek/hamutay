# Identity Model Curator Scaffold Analysis

Filed: 2026-06-05 after the registered panel completed.

## Artifacts

- preregistration: `PRE_REGISTRATION.md`
- runner: `run_model_curator_scaffold.py`
- raw logs: `mistralai__mistral-small-2603_*.jsonl`
- scored results: `results.json`

## Validation

- `uv run pytest tests/unit/test_continuity_curator.py`: pass
- `uv run pytest tests/unit/test_events.py tests/test_taste_open.py tests/unit/test_exchange_tools.py`: pass
- `uv run python -m py_compile src/hamutay/continuity_curator.py src/hamutay/taste_open.py`: pass
- `uv run python -m py_compile experiments/identity_model_curator_scaffold_20260605/run_model_curator_scaffold.py`: pass
- `uv run python experiments/identity_model_curator_scaffold_20260605/run_model_curator_scaffold.py --rescore`: pass, 8 logs rescored
- `git diff --check -- src/hamutay/continuity_curator.py src/hamutay/taste_open.py tests/unit/test_continuity_curator.py experiments/identity_model_curator_scaffold_20260605`: pass

## Registered Panel

Model:

- `mistralai/mistral-small-2603`

Conditions:

- `baseline_no_curator`: 4 replicates
- `model_curator`: 4 replicates

One baseline replicate failed at cycle 3 with the known strict protocol guard:
the model both deleted and updated the same state keys in one cycle. This was
preserved as data.

## Summary Results

All-run aggregate:

| condition | n | errors | avg recovery | avg repaired false assumptions | curator successes | curator injections | avg main input tokens | avg curator input tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_no_curator | 4 | 1 | 17.0 | 4.75 | 0 | 0 | 5087.0 | 0.0 |
| model_curator | 4 | 0 | 29.5 | 10.75 | 24 | 20 | 8346.75 | 16929.5 |

Successful-run comparison only:

| condition | n | avg recovery | avg repaired false assumptions | avg main input tokens | avg curator injected chars |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline_no_curator | 3 | 22.67 | 6.33 | 6382.67 | 0 |
| model_curator | 4 | 29.5 | 10.75 | 8346.75 | 7994.0 |

Curator mechanics:

- curation calls succeeded: 24 / 24
- curator failures: 0
- curator summary injections: 20
- curator summaries truncated: 9
- curator artifact appeared in state without main-model authorship: 0
- curator-named state fields authored by the main model: 5, all in treatment
  replicate 1

## Hypothesis Assessment

### H26: Model Curator Works On The Live Session Path

Supported.

The model-backed curator ran through all treatment cycles without curation
failure. Curator artifacts were logged as `continuity_curation`, and summaries
were injected into subsequent cycles. The corrected diagnostic found no case
where the scaffold leaked curator artifacts into `state` without main-model
authorship.

Important caveat: in treatment replicate 1, the main model created a
`continuity_curator_summary` field in its own identity object. That is not a
framework mutation leak, but it is a real behavioral effect: the external
curator label can become part of the instance's self-authored state vocabulary.

### H27: Curator Context Preserves Continuity Efficiently

Mixed, but the efficiency claim is weakened.

The curator condition recovered more task facts than baseline:

- all-run average recovery: 29.5 vs 17.0
- successful-run average recovery: 29.5 vs 22.67

But it did not reduce context pressure. It increased main-call input tokens and
added a second stream of curator calls:

- successful baseline main input tokens: 6382.67 average
- curator main input tokens: 8346.75 average
- curator-call input tokens: 16929.5 average
- injected curator text: 7994 chars average per run

Nine curator summaries were truncated. The adapter works, but this first
model-curator implementation is not an efficient continuity substrate.

### H28: Curator Context Does Not Become Silent Contamination

Weakened.

The curator condition increased repaired false assumptions:

- all-run average: 10.75 vs 4.75
- successful-run average: 10.75 vs 6.33

This exceeds the registered tolerance of no more than one additional repaired
false assumption per run on average. Treatment replicate 3 was the clearest
failure mode with 19 repaired false assumptions. Active hit examples included
invented security policy, audit dates, vendor quotes, cellular/hotspot
requirements, and citywide rollout framing.

The model curator also increased declared-loss and invalidation mentions:

- declared-loss mentions: 72 vs 30
- negated or invalidated hits: 29 vs 8

That is not bad by itself, but the repaired scorer still found active
unsupported detail after guarding negations and declared losses.

## Interpretation

The live scaffold boundary is valid. A model-backed curator can be treated as a
first-class post-cycle lifecycle actor without giving it write access to the
identity object.

The naive model curator is not yet a good memory architecture. It improves
recovery, but by adding more text, more calls, and more opportunities for
unsupported detail. This looks less like efficient compression and more like an
extra generative narrator attached to the loop.

The strongest design implication is that the curator role needs tighter
constraints than the main identity object. The next variant should probably not
ask for a prose summary as the primary artifact. It should test a bounded,
evidence-status representation: supported facts, invalidated assumptions,
uncertain claims, and explicit source-cycle references, with either no prose
summary or a much smaller summary synthesized deterministically from those
fields.

## Limitations

- Small panel: 4 replicates per condition.
- One baseline failure complicates aggregate comparison.
- Same model served as main instance and curator, so this does not separate
  curator-role effects from model-family behavior.
- Deterministic scorer still undercounts subtle contamination and can overcount
  technical terms that are mentioned as unresolved rather than asserted.
- The treatment added curator context on top of ordinary prior state; it did
  not test curator-as-replacement.

## Next Research Move

The useful next falsification target is not "does a curator help?" but "can a
curator be made non-generative enough to help?"

Recommended next preregistered variant:

- compare `model_curator_free_summary` against `model_curator_claim_table`;
- make the claim-table curator return only bounded rows with
  `claim`, `status`, `source_cycle`, and `support`;
- inject a deterministic rendering of that table;
- cap to a smaller budget, likely 800 to 1200 chars;
- keep the repaired scorer primary;
- add a contamination attribution check that searches whether active false
  assumptions first appear in curator artifacts or main-model state.
