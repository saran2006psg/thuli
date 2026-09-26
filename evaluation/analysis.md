# Phase 7 — Baseline Evaluation Report

> Generated: 2026-09-26T08:59:22.119991+00:00
> Model: CLIP ViT-B/32 | Index: FAISS IndexFlatIP | Threshold: 0.75

## Summary

| Metric | Value |
|---|---|
| Total Images | 46 |
| Valid Images | 46 |
| **Top-1 Accuracy** | **63.0%** |
| **Top-5 Accuracy** | **78.3%** |
| MATCH decisions | 40 |
| UNKNOWN decisions | 6 |
| Mean Latency | 105.06 ms |
| Median Latency | 101.2 ms |
| P95 Latency | 128.49 ms |

## Per-Condition Accuracy

| Condition | N | Top-1 | Top-5 |
|---|---|---|---|
| `bad_lighting` | 6 | 50.0% | 66.7% |
| `bright_lighting` | 4 | 100.0% | 100.0% |
| `clutter` | 6 | 50.0% | 50.0% |
| `distance` | 4 | 25.0% | 50.0% |
| `hand` | 1 | 100.0% | 100.0% |
| `hand_wrist` | 3 | 100.0% | 100.0% |
| `motion_blur` | 4 | 75.0% | 100.0% |
| `motionblur` | 3 | 33.3% | 66.7% |
| `noise` | 1 | 0.0% | 0.0% |
| `normal` | 5 | 80.0% | 100.0% |
| `occlusion` | 4 | 50.0% | 75.0% |
| `odd_angle` | 4 | 75.0% | 100.0% |
| `reflection` | 1 | 100.0% | 100.0% |

## Worst Failures (Top-10)

| Image | Ground Truth | Predicted | Similarity | GT Rank | Condition |
|---|---|---|---|---|---|
| `id46` | `bracelet` | `bracelet` | 0.5646 | 1 | `distance` |
| `id04` | `ring` | `earring` | 0.6625 | -1 | `clutter` |
| `id05` | `necklace` | `ring` | 0.7171 | 4 | `noise` |
| `id18` | `ring` | `earring` | 0.7421 | 2 | `occlusion` |
| `id14` | `ring` | `ring` | 0.7432 | 1 | `distance` |
| `id09` | `ring` | `necklace` | 0.7466 | 3 | `bad_lighting` |
| `id23` | `bracelet` | `necklace` | 0.7554 | -1 | `clutter` |
| `id08` | `ring` | `bracelet` | 0.7587 | 3 | `motionblur` |
| `id10` | `ring` | `necklace` | 0.7627 | -1 | `bad_lighting` |
| `id03` | `bracelet` | `necklace` | 0.7667 | -1 | `motionblur` |

## Dataset Progress

- Current: 46 / 100 images
- Progress: 46.0%
