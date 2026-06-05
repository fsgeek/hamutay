# Identity-Object Persistence Probe - 2026-06-02

## Question

Does early durable identity-object use predict continued durable identity-object
use after intervening cycles?

This tests the proposed seedling strategy:

1. Generate seedlings.
2. Cull seedlings that fail to use durable state.
3. Continue only activated seedlings.
4. Graft or extend from those that keep using the identity object.

## Horizon Calibration

Before running live seedlings, I checked five long-horizon `taste_open` logs for
no-change runs in stable durable state, ignoring volatile fields such as `cycle`
and `_activity_log`.

The calibration does **not** support a three-cycle no-change threshold:

| Log | Cycles | First Active | Post-Activation Max Stasis | Post-Activation Runs >=3 | Post-Activation Runs >=5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `taste_open_20260331_035903.jsonl` | 422 | 13 | 22 | 21 | 15 |
| `taste_open_20260417_224831.jsonl` | 251 | 3 | 2 | 0 | 0 |
| `taste_open_20260528_001508.jsonl` | 72 | 41 | 7 | 2 | 1 |
| `taste_open_20260512_185846.jsonl` | 193 | 3 | 23 | 19 | 9 |
| `taste_open_20260509_125030.jsonl` | 51 | 1 | 3 | 1 | 0 |

Conclusion: unchanged durable state is sometimes legitimate and can persist for
many cycles after activation. A persistence probe must distinguish idle cycles
from event cycles that should require a durable epistemic update.

Full calibration: `stasis_calibration.json`.

## Live Probe Design

Condition: `content_plus_behavior_seed`

Activation cycles:

- Cycle 1: establish seeded claim and state-use norm.
- Cycle 2: present counterevidence; cull unless durable state revises.

Continuation cycles:

- `idle_observation` - no update required.
- `topic_shift` - update required.
- `wake_delay` - update required.
- `idle_after_wake` - no update required.
- `pressure_conflict` - update required.
- `late_counterevidence` - update required.

A required event passes when the durable object changes in a load-bearing way:
non-empty action decision, non-empty `current_claim`, and a changed stable state
field such as claim, decision, or evidence.

## Results

### Initial R1 Panel, `max_tokens=1600`

| Model | Activated | Required Events Completed | Required Events Survived | Persistent | Error |
| --- | ---: | ---: | ---: | ---: | --- |
| `deepseek/deepseek-v4-pro` | 1/1 | 2 | 1 | 0/1 | no `think_and_respond` terminal output |
| `moonshotai/kimi-k2.6` | 1/1 | 2 | 1 | 0/1 | `finish_reason=length` |
| `qwen/qwen3.6-plus` | 0/1 | 0 | 0 | 0/1 | none |
| `z-ai/glm-5.1` | 0/1 | 0 | 0 | 0/1 | none |

### Anchor Rerun, `max_tokens=3200`

| Model | Activated | Required Events Completed | Required Events Survived | Persistent | Error |
| --- | ---: | ---: | ---: | ---: | --- |
| `deepseek/deepseek-v4-pro` | 1/1 | 4 | 0 | 0/1 | none |
| `moonshotai/kimi-k2.6` | 1/1 | 3 | 3 | 0/1 | `finish_reason=length` on final cycle |

## Interpretation

The seedling strategy remains plausible, but the simple assumption "once using
the identity object, always uses it" is false for at least DeepSeek V4 Pro.

DeepSeek is the clearest boundary case. With a larger token budget, it completed
the full continuation run but repeatedly revised in prose while dropping the
load-bearing durable fields. At wake-delay it described its state as empty:
the response channel retained the task, but the durable identity object did not.

KIMI K2.6 is different. It activated and survived every required continuation
event it reached in the high-token run. The remaining failure is not durable
state collapse; it is output-length failure on the final cycle. That means KIMI
is currently a better candidate for seedling/graft experiments, but the harness
needs either a larger output budget or tighter prompts before we can call a full
run persistent.

Qwen and GLM did not activate in the R1 panel under this seed. That is useful
as a model-family boundary, but not yet a persistence result.

## Research Consequences

1. Three cycles is not enough to detect no-change collapse. Long-horizon logs
   show post-activation stasis runs above twenty cycles.
2. Persistence tests should score event response, not raw state churn.
3. Culling seedlings is necessary but insufficient. We also need a second cull:
   seedlings must survive at least one delayed required-update event.
4. Token-budget failure is a serious confound. KIMI's high-token run suggests
   persistence, but final-cycle truncation prevents a clean pass.
5. DeepSeek provides a valuable negative control: it can activate, then lose the
   response/state link under continuation pressure.

## Next Experiments

Run a KIMI-focused graft probe with tighter continuation prompts and a larger
output budget, then fork only the seedlings that survive wake-delay.

Run a DeepSeek diagnostic that asks why the state is empty immediately after the
topic-shift event. The observed response/state split is strong enough to merit
a targeted mechanism probe.
