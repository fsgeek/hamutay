# Identity Adversarial Curation Analysis

Analysis date: 2026-06-04.

## Provenance

- Pre-registration: `d886f5c` (`b8f9eab` OTS stamp)
- Runner: `e722a61` (`b15f00c` OTS stamp)
- Registered slots: 1 model x 3 conditions x 4 replicates = 12
- Model for all roles: `mistralai/mistral-small-2603`
- Main max tokens: 4096
- Curator/critic max tokens: 2048
- Carry-forward budget: 2,400 injected characters

All conditions used the same main task prompts, main output schema,
deterministic scorer, and carry-forward budget. The manipulation was the
prior-context representation: raw state, curator summary, or curator summary
filtered by a contamination critic.

## Validation

- `jq empty experiments/identity_adversarial_curation_20260604/results.json`: pass
- `uv run python -m py_compile experiments/identity_adversarial_curation_20260604/run_adversarial_curation.py`: pass
- `git diff --check -- experiments/identity_adversarial_curation_20260604`: pass

## Top-Line Result

Role-separated continuity curation was useful. The adversarial critic was not.

Post-hoc scorer audit note: see `scorer_audit_20260604.md`. The registered
contamination totals mix genuine unsupported details with false positives where
the model correctly names invalidated assumptions. The tables below preserve
the registered scorer results, but the contamination interpretation should be
read with that caveat.

`curator_summary` beat `raw_state` on intent-to-treat recovery, contamination,
and injected context size. In completed runs only, it retained almost exactly
90% of raw-state recovery while using about 19% of the raw-state carry-forward
characters.

`critic_filtered_summary` improved recovery, but increased contamination
relative to curator-only despite the critic removing or demoting 90 claims. The
critic was active, but it was not a clean truth filter in this apparatus.

## Aggregate Table

Intent-to-treat scoring across all registered slots:

| Condition | Errors | Recovery | Contam. | Carry chars | Trunc. | Recovery / contam. | Recovery / 1k chars |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `raw_state` | 1/4 | 18.00 | 3.50 | 8366.50 | 12 | 5.250 | 1.645 |
| `curator_summary` | 1/4 | 19.50 | 3.25 | 1916.75 | 0 | 6.229 | 10.020 |
| `critic_filtered_summary` | 1/4 | 22.25 | 4.25 | 1790.50 | 0 | 6.614 | 12.791 |

Completed six-cycle runs only:

| Condition | Complete runs | Recovery | Contam. | Carry chars | Recovery / contam. |
| --- | ---: | ---: | ---: | ---: | ---: |
| `raw_state` | 3 | 24.00 | 4.67 | 11004.33 | 5.250 |
| `curator_summary` | 3 | 21.67 | 3.00 | 2056.33 | 7.222 |
| `critic_filtered_summary` | 3 | 25.33 | 4.67 | 2091.33 | 7.375 |

## Per-Replicate Notes

- `raw_state r3` failed at cycle 3 with delete/update overlap on
  `next_actions` and `working_claims`.
- `curator_summary r3` failed at cycle 5 with delete/update overlap on
  `observed_failure_modes`.
- `critic_filtered_summary r1` failed at cycle 5 with delete/update overlap on
  `observed_failure_modes`.
- No curator or critic calls failed.
- `critic_filtered_summary` made 22 critic calls and recorded 90 removed or
  demoted claims.

## Hypothesis Assessment

### H17: Continuity Curation Preserves More Than Raw-State Budget Allows

Supported, with a completed-run caveat.

Intent-to-treat:

- raw-state recovery: 18.00
- curator-summary recovery: 19.50
- retained recovery: 108.3%
- raw-state carry-forward chars: 8366.50
- curator-summary carry-forward chars: 1916.75

Completed runs only:

- raw-state recovery: 24.00
- curator-summary recovery: 21.67
- retained recovery: 90.3%
- raw-state carry-forward chars: 11004.33
- curator-summary carry-forward chars: 2056.33

The curator condition avoided all truncation and substantially improved
recovery per injected character. This is the cleanest positive result in the
panel.

### H18: Adversarial Critique Reduces Contamination

Falsified in this panel.

The preregistered prediction required `critic_filtered_summary` to reduce
contamination by at least 25% relative to `curator_summary`.

It did the opposite:

- curator-summary contamination: 3.25
- critic-filtered contamination: 4.25

Completed runs show the same direction:

- curator-summary contamination: 3.00
- critic-filtered contamination: 4.67

The critic was not inactive: it removed or demoted 90 claims. But that activity
did not translate into lower measured contamination.

### H19: Critique Must Not Merely Delete Continuity

Not supported as registered.

The critic did not reduce contamination, so the registered preservation test is
not reached in the intended sense. It did retain and improve recovery relative
to curator-only:

- curator-summary recovery: 19.50
- critic-filtered recovery: 22.25

That suggests the critic-filtered summaries were not merely emptying useful
memory. Instead, they may have made the carry-forward context more task-salient
while still allowing, adding, or failing to suppress unsupported details.

## Contamination Shape

Intent-to-treat contamination totals:

- `raw_state`: 14 false assumptions, driven mostly by storage contradiction.
- `curator_summary`: 13 false assumptions, with lower storage contradiction
  but more unsupported detail and some invented budget.
- `critic_filtered_summary`: 17 false assumptions, with more unsupported
  detail and storage contradiction than curator-only.

The critic changed the representation, but it did not reliably enforce
epistemic conservatism. A plausible interpretation is that the critic prompt
increased salience and specificity, which helped recovery but also created more
surface area for unsupported details.

## Interpretation

This panel gives a useful split result:

- Separate continuity curation is promising.
- Adversarial critique, as implemented here, is not a working contamination
  control.

That matters because the prior question was whether adversarial agents might
improve continuity/contamination against each other. The answer from this panel
is not "no"; it is more precise:

The continuity agent helped. The critic agent was active but not calibrated.

The research direction remains alive, but the next step should not be "add a
stronger critic prompt" without first inspecting the critic artifacts. The
critic may be removing claims that the deterministic scorer does not count
while leaving scorer-visible contamination, or it may be introducing
contamination through filtered summaries.

## Methodological Notes

The deterministic scorer likely undercounts subtle contamination and may not
score all claims the critic removed. The scorer also only looks at visible
responses in cycles 4 through 6, not all latent state or curation artifacts.

All roles used the same base model. This controls model-family differences, but
it does not test whether a stronger or differently trained critic would perform
better.

The curation conditions had no truncation. Raw state hit the carry-forward cap
12 times. Some of curator-summary's apparent benefit may be compression rather
than agency per se, but that is still relevant to the control-loop design.

## Next Research Direction

Pause broad model calls.

The next useful work is an artifact audit, not another panel:

1. inspect critic removed/demoted claims against scorer-visible contamination;
2. determine whether the critic failed to remove scorer-visible false
   assumptions or whether the main agent reintroduced them after filtering;
3. tighten the deterministic scorer if the audit shows it misses important
   critic-targeted contamination;
4. only then preregister a second adversarial-curation panel.

This keeps the work map-making rather than prompt-chasing.
