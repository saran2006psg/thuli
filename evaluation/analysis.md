# Phase 7 — Evaluation Report
## All Images in evaluation/images/

> Generated: 2026-09-27T09:10:25.821577+00:00
> Model: CLIP ViT-B/32 | Index: FAISS IndexFlatIP | Threshold: 0.75
> Source: All 115 images scanned from evaluation/images/

## Summary

| Metric | Value |
|---|---|
| Total Images Scanned | 115 |
| Valid (ran through matcher) | 111 |
| Scored (has ground truth) | 111 |
| Skipped (corrupt/tiny) | 4 |
| Errors | 0 |
| **Top-1 Accuracy** | **72.1%** |
| **Top-5 Accuracy** | **89.2%** |
| MATCH decisions | 103 |
| UNKNOWN decisions | 8 |
| Wrong Matches | 23 |
| **False Acceptance Rate (FAR)** | **20.72%** |
| **False Rejection Rate (FRR)** | **7.21%** |
| Mean Latency | 121.39 ms |
| Median Latency | 120.41 ms |
| P95 Latency | 138.68 ms |

## Per-Condition Accuracy

| Condition | N | Top-1 | Top-5 |
|---|---|---|---|
| `bad_lighting` | 7 | 100.0% | 100.0% |
| `bright_lighting` | 12 | 83.3% | 100.0% |
| `clutter` | 14 | 64.3% | 78.6% |
| `distance` | 12 | 58.3% | 75.0% |
| `hand` | 1 | 100.0% | 100.0% |
| `hand_wrist` | 11 | 72.7% | 100.0% |
| `motion_blur` | 12 | 75.0% | 100.0% |
| `motionblur` | 3 | 33.3% | 66.7% |
| `noise` | 1 | 0.0% | 0.0% |
| `normal` | 13 | 92.3% | 100.0% |
| `occlusion` | 12 | 58.3% | 75.0% |
| `odd_angle` | 12 | 66.7% | 91.7% |
| `reflection` | 1 | 100.0% | 100.0% |

## Worst Failures (Top-10)

| Image | Ground Truth | Predicted | Similarity | GT Rank | Condition |
|---|---|---|---|---|---|
| `id46` | `bracelet` | `bracelet` | 0.5594 | 1 | `distance` |
| `id04` | `ring` | `earring` | 0.6624 | -1 | `clutter` |
| `id18` | `ring` | `bracelet` | 0.6862 | 3 | `occlusion` |
| `id05` | `necklace` | `ring` | 0.7171 | -1 | `noise` |
| `id14` | `ring` | `ring` | 0.7270 | 1 | `distance` |
| `id58` | `ring` | `ring` | 0.7403 | 1 | `clutter` |
| `id113` | `bracelet` | `bracelet` | 0.7410 | 1 | `distance` |
| `id76` | `bracelet` | `bracelet` | 0.7411 | 1 | `odd_angle` |
| `id08` | `ring` | `bracelet` | 0.7578 | 3 | `motionblur` |
| `id03` | `bracelet` | `necklace` | 0.7668 | -1 | `motionblur` |

## Dataset Progress

- Current: 115 / 115 images
- Progress: 100.0%
