# Embedding Similarity Analysis

Source: `experiments/observation_full/observations.jsonl`
Embedding model: `BAAI/bge-large-en-v1.5`
Transitions: 103

## Summary

| Measure | Mean | Std | Min | P25 | Median | P75 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| Content embedding cosine | 0.870 | 0.080 | 0.616 | 0.812 | 0.876 | 0.934 | 1.000 |
| Meta embedding cosine | 0.757 | 0.163 | 0.412 | 0.753 | 0.819 | 0.862 | 1.000 |
| Full tensor embedding cosine | 0.871 | 0.080 | 0.616 | 0.812 | 0.876 | 0.934 | 1.000 |
| Content 3-gram survival | 0.095 | 0.158 | 0.006 | 0.026 | 0.048 | 0.076 | 0.954 |

Batch-token/content-embedding Pearson r: `-0.171`

## Lowest Content Similarity Transitions

| Prior -> Cycle | Batch tokens | Content cosine | 3-gram survival |
|---|---:|---:|---:|
| 90 -> 91 | 555 | 0.616 | 0.048 |
| 21 -> 22 | 2312 | 0.624 | 0.020 |
| 100 -> 101 | 1021 | 0.682 | 0.035 |
| 51 -> 52 | 854 | 0.697 | 0.012 |
| 68 -> 69 | 6570 | 0.729 | 0.032 |

## Highest Content Similarity Transitions

| Prior -> Cycle | Batch tokens | Content cosine | 3-gram survival |
|---|---:|---:|---:|
| 43 -> 44 | 959 | 1.000 | 0.341 |
| 87 -> 88 | 257 | 1.000 | 0.769 |
| 15 -> 16 | 624 | 1.000 | 0.067 |
| 30 -> 31 | 406 | 0.999 | 0.358 |
| 29 -> 30 | 1087 | 0.998 | 0.243 |

## Interpretation Boundary

This measures consecutive-cycle tensor-to-tensor embedding similarity. It does not measure cross-condition similarity and does not prove that every important fact survived; it tests the narrower A2 companion claim that semantic content remains close while surface structure rewrites.
