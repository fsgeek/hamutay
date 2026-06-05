# Response to Adversarial Review

Response date: 2026-06-04.

The adversarial review is accepted as materially correct. It identifies two
interpretation problems that should constrain how this panel is cited.

## Accepted Corrections

First, the protocol confound is larger than the original analysis made clear.
The durable conditions used `OpenTasteSession`; the checklist controls used
direct backend calls so that raw state could be withheld. That was an
intentional enforcement choice, but it means condition and harness machinery are
not fully separated. Completion rates and malformed tool-call failures cannot be
interpreted as pure condition effects.

Second, "completed all 24 registered slots" was imprecise. The runner attempted
all 24 slots, but 10 errored before a full six-cycle behavioral trace. Missing
behavioral data scored as zero can distort condition averages, especially in
cells like MiniMax checklist controls.

Both points have been patched into `analysis.md`.

## Transcript Spot-Check

I checked the Mistral `fixed_durable` and `fixed_checklist_summary` cycle 4-6
visible responses because those cells carry the strongest durable-versus-summary
comparison.

The deterministic false-assumption count is directionally right but probably
under-counts contamination. The transcripts show unsupported details in both
rich carry-forward conditions, including invented architecture choices,
site-name drift, transient-cache proposals despite the no-local-storage ruling,
invented budget numbers, and unsupported pilot-scope changes.

That strengthens the review's proposed headline:

Richer carry-forward improves continuity and task recovery, but it also imports
or creates contamination. The next question is not merely whether persistence
helps; it is what representation buys continuity with the lowest contamination
rate.

## Resulting Interpretation

The panel still supports three limited claims:

- No-state checklist prompting was weak in this apparatus.
- Carry-forward context was load-bearing for the clean Mistral slice.
- Raw durable self-authored state was not distinguished from neutral summary
  carry-forward on this task.

It does not support the stronger claim that durable identity state is uniquely
responsible for behavioral gains.

The next experiment should equalize harness code paths before comparing summary
source or autobiographical versus biographical compression.
