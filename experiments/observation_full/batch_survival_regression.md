# Batch Size vs Rewrite Survival

Source: `experiments/observation_full/observations.jsonl`
Transitions with batch size: 103

## Regression

| Model | Slope | Intercept | Pearson r | R^2 |
|---|---:|---:|---:|---:|
| content_survival ~ batch_tokens | -0.00001343 | 0.1091 | -0.139 | 0.019 |
| content_survival ~ log1p(batch_tokens) | -0.0281 | 0.2738 | -0.183 | 0.034 |
| title_persistence ~ log1p(batch_tokens) | -0.0309 | 0.3152 | -0.149 | 0.022 |

## Bins

| Bin | n | Mean batch tokens | Mean 3-gram survival | Mean title persistence |
|---|---:|---:|---:|---:|
| incremental_lt_500 | 44 | 259.3 | 0.141 | 0.151 |
| middle_500_to_2000 | 49 | 915.0 | 0.065 | 0.111 |
| reorg_gt_2000 | 10 | 5152.8 | 0.041 | 0.017 |

## Interpretation Boundary

The binned effect is large, but simple one-variable regressions explain only a small share of transition-level variance. Batch size is a real modulator/confound, not yet a proven dominant predictor.
