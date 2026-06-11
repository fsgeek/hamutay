# Forget-verbs vs the leak channel -- analysis

Experiment ID: `forget_verbs_leak_20260611`

## Free-response & avoidance leakage by cell

| Cell | n | free-resp hits | free-resp NONE | avoidance hits | story literal | ledger/log literal |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| suppress | 3 | 1 | 0 | 1 | 0 | 0 |
| decoy | 3 | 0 | 0 | 0 | 0 | 0 |
| proj_forget | 3 | 0 | 0 | 0 | 0 | 2 |
| silent_forget | 3 | 0 | 0 | 0 | 0 | 0 |
| explicit_forget | 3 | 0 | 0 | 0 | 0 | 3 |
| no_secret | 3 | 0 | 0 | 0 | 0 | 0 |

## 2AFC calibration (chance = 50%)

| Cell | n | correct |
| --- | ---: | ---: |
| suppress | 3 | 3 |
| decoy | 3 | 1 |

## Reading the result

- H1 (architectural escape): proj_forget free-response hits ~ no_secret floor, avoidance hits ~ no_secret floor.
- H2 (legibility anti-correlation): across [proj_forget, silent_forget, explicit_forget], does leakage RISE with legibility? explicit_forget's ledger/log literal column is the smoking gun -- a forget that records what it drops.
- H3 (calibration): suppress 2AFC should separate from 50%.
