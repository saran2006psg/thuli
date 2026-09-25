# Phase 7 — Baseline Evaluation Report

> Generated: 2026-09-25T17:26:29.536191+00:00
> Model: CLIP ViT-B/32 | Index: FAISS IndexFlatIP | Threshold: 0.75

## Summary

| Metric | Value |
|---|---|
| Total Images | 39 |
| Valid Images | 39 |
| **Top-1 Accuracy** | **64.1%** |
| **Top-5 Accuracy** | **76.9%** |
| MATCH decisions | 34 |
| UNKNOWN decisions | 5 |
| Mean Latency | 103.17 ms |
| Median Latency | 94.43 ms |
| P95 Latency | 131.69 ms |

## Per-Condition Accuracy

| Condition | N | Top-1 | Top-5 |
|---|---|---|---|
| `bad_lighting` | 5 | 40.0% | 60.0% |
| `bright_lighting` | 3 | 100.0% | 100.0% |
| `clutter` | 6 | 50.0% | 50.0% |
| `distance` | 3 | 33.3% | 66.7% |
| `hand` | 1 | 100.0% | 100.0% |
| `hand_wrist` | 3 | 100.0% | 100.0% |
| `motion_blur` | 3 | 66.7% | 100.0% |
| `motionblur` | 3 | 33.3% | 66.7% |
| `noise` | 1 | 0.0% | 0.0% |
| `normal` | 4 | 100.0% | 100.0% |
| `occlusion` | 3 | 33.3% | 66.7% |
| `odd_angle` | 3 | 100.0% | 100.0% |
| `reflection` | 1 | 100.0% | 100.0% |

## Worst Failures (Top-10)

| Image | Ground Truth | Predicted | Similarity | GT Rank | Condition |
|---|---|---|---|---|---|
| `id04` | `ring` | `earring` | 0.6625 | -1 | `clutter` |
| `id18` | `ring` | `ring` | 0.6877 | 1 | `occlusion` |
| `id05` | `necklace` | `necklace` | 0.7166 | 1 | `noise` |
| `id14` | `ring` | `ring` | 0.7432 | 1 | `distance` |
| `id09` | `ring` | `necklace` | 0.7466 | 3 | `bad_lighting` |
| `id08` | `ring` | `necklace` | 0.7522 | 2 | `motionblur` |
| `id23` | `bracelet` | `necklace` | 0.7554 | -1 | `clutter` |
| `id10` | `ring` | `necklace` | 0.7627 | -1 | `bad_lighting` |
| `id03` | `bracelet` | `necklace` | 0.7667 | -1 | `motionblur` |
| `id38` | `necklace` | `bracelet` | 0.7921 | 4 | `occlusion` |

## Dataset Progress

- Current: 39 / 100 images
- Progress: 39.0%
