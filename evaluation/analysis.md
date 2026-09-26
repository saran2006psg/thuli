# Phase 7 — Baseline Evaluation Report

> Generated: 2026-09-26T09:20:37.059240+00:00
> Model: CLIP ViT-B/32 | Index: FAISS IndexFlatIP | Threshold: 0.75

## Summary

| Metric | Value |
|---|---|
| Total Images | 63 |
| Valid Images | 63 |
| **Top-1 Accuracy** | **66.7%** |
| **Top-5 Accuracy** | **77.8%** |
| MATCH decisions | 54 |
| UNKNOWN decisions | 9 |
| Mean Latency | 67.51 ms |
| Median Latency | 66.2 ms |
| P95 Latency | 86.36 ms |

## Per-Condition Accuracy

| Condition | N | Top-1 | Top-5 |
|---|---|---|---|
| `bad_lighting` | 7 | 57.1% | 71.4% |
| `bright_lighting` | 6 | 100.0% | 100.0% |
| `clutter` | 8 | 37.5% | 50.0% |
| `distance` | 6 | 33.3% | 50.0% |
| `hand` | 1 | 100.0% | 100.0% |
| `hand_wrist` | 5 | 100.0% | 100.0% |
| `motion_blur` | 6 | 83.3% | 100.0% |
| `motionblur` | 3 | 33.3% | 66.7% |
| `noise` | 1 | 0.0% | 0.0% |
| `normal` | 7 | 85.7% | 100.0% |
| `occlusion` | 6 | 50.0% | 50.0% |
| `odd_angle` | 6 | 83.3% | 100.0% |
| `reflection` | 1 | 100.0% | 100.0% |

## Worst Failures (Top-10)

| Image | Ground Truth | Predicted | Similarity | GT Rank | Condition |
|---|---|---|---|---|---|
| `id46` | `bracelet` | `bracelet` | 0.5646 | 1 | `distance` |
| `id04` | `ring` | `earring` | 0.6625 | -1 | `clutter` |
| `id65` | `ring` | `ring` | 0.7128 | 1 | `occlusion` |
| `id05` | `necklace` | `ring` | 0.7171 | 4 | `noise` |
| `id64` | `ring` | `earring` | 0.7237 | 2 | `distance` |
| `id58` | `ring` | `ring` | 0.7332 | 1 | `clutter` |
| `id18` | `ring` | `earring` | 0.7421 | 2 | `occlusion` |
| `id14` | `ring` | `ring` | 0.7432 | 1 | `distance` |
| `id09` | `ring` | `necklace` | 0.7466 | 3 | `bad_lighting` |
| `id23` | `bracelet` | `necklace` | 0.7554 | -1 | `clutter` |

## Dataset Progress

- Current: 63 / 100 images
- Progress: 63.0%
